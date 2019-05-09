"""PytSite ODM Plugin Finder
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from typing import List as _List, Tuple as _Tuple, Union as _Union, Callable as _Callable, Optional as _Optional
from abc import ABC as _ABC, abstractmethod as _abstractmethod
from copy import deepcopy as _deepcopy
from bson import DBRef as _DBRef
from pymongo.cursor import Cursor as _Cursor, CursorType as _CursorType
from pytsite import util as _util, reg as _reg, cache as _cache
from plugins import query as _query
from . import _model, _api, _odm_query, _error

_CACHE_TTL = _reg.get('odm.cache_ttl', 86400)  # 24 hours

_ResultProcessor = _Callable[[_model.Entity], _model.Entity]


class Result(_ABC):
    @_abstractmethod
    def count(self) -> int:
        raise NotImplementedError()

    def __len__(self) -> int:
        return self.count()

    def __iter__(self):
        """Get iterator
        """
        return self


class SingleModelResult(Result):
    """Finder Result
    """

    def __init__(self, model: str, count: int, cursor: _Cursor = None, cached_ids: _List[str] = None,
                 process: _ResultProcessor = None, cache_ttl: int = None, cache_pool: _cache.Pool = None,
                 finder_id: str = None):
        """Init
        """
        self._model = model
        self._count = count
        self._dispensed_cnt = 0
        self._cursor = cursor
        self._cached_ids = cached_ids
        self._process = process
        self._cache_ttl = cache_ttl
        self._cache_pool = cache_pool
        self._finder_id = finder_id

    @property
    def model(self) -> str:
        return self._model

    def __next__(self) -> _model.Entity:
        """Get next item
        """
        if self._dispensed_cnt == self._count:
            raise StopIteration()

        # Get next document ID from cache or from database
        doc_id = self._cached_ids[self._dispensed_cnt] if self._cached_ids else next(self._cursor)['_id']

        # Dispense entity
        entity = _api.dispense(self._model, doc_id)

        # Add document's ID to the cache
        if not self._cached_ids and self._cache_ttl:
            self._cache_pool.list_r_push(self._finder_id, doc_id)

        # Call response processor
        if self._process:
            entity = self._process(entity)

        self._dispensed_cnt += 1

        return entity

    def count(self) -> int:
        return self._count

    def explain(self) -> dict:
        """Explain the cursor
        """
        if not self._cursor:
            raise RuntimeError('Cannot explain cached results')

        return self._cursor.explain()

    def explain_winning_plan(self) -> dict:
        """Explain winning plan of the the cursor.
        """
        return self.explain()['queryPlanner']['winningPlan']

    def explain_parsed_query(self) -> dict:
        """Explain parsed query of the the cursor.
        """
        return self.explain()['queryPlanner']['parsedQuery']

    def explain_execution_stats(self) -> dict:
        """Explain execution stats of the the cursor.
        """
        return self.explain()['executionStats']


class MultiModelResult(Result):
    def __init__(self, results: _List[SingleModelResult], limit: int = 0):
        self._results = results
        self._results_count = len(results)
        self._current_result_index = 0
        self._exhausted_results_indexes = []
        self._dispensed_count = 0
        self._limit = limit

    def __next__(self) -> _model.Entity:
        """Get next item
        """
        if self._limit and self._dispensed_count >= self._limit:
            raise StopIteration()

        if len(self._exhausted_results_indexes) == self._results_count:
            raise StopIteration()

        if self._current_result_index >= self._results_count:
            self._current_result_index = 0

        try:
            e = next(self._results[self._current_result_index])
            self._dispensed_count += 1
        except StopIteration:
            # Mark current result as exhausted and move forward
            self._exhausted_results_indexes.append(self._current_result_index)
            self._current_result_index += 1
            e = next(self)

        return e

    def count(self) -> int:
        return sum([len(r) for r in self._results])


class Finder(_ABC):
    def __init__(self, query: _query.Query = None):
        """Init
        """
        self._query = query if query is not None else _query.Query()
        self._skip = 0
        self._limit = 0
        self._sort = None
        self._result_processor = None
        self._cache_ttl = _CACHE_TTL
        self._no_cache_fields = []

    @property
    def query(self) -> _query.Query():
        return self._query

    @property
    def id(self) -> str:
        """Get unique finder's ID to use as a cache key, etc
        """
        q = _deepcopy(self._query)
        for f in self._no_cache_fields:
            q.rm_field(f)

        return _util.md5_hex_digest('{}{}{}{}'.format(q, self._skip, self._limit, self._sort))

    @property
    def result_processor(self) -> _Optional[_Callable[[_model.Entity], _model.Entity]]:
        return self._result_processor

    @result_processor.setter
    def result_processor(self, value: _ResultProcessor):
        self._result_processor = value

    def process_result(self, value: _ResultProcessor):
        self._result_processor = value

        return self

    @property
    def cache_ttl(self) -> int:
        """Get query's cache TTL
        """
        return self._cache_ttl

    @cache_ttl.setter
    def cache_ttl(self, value: int):
        """Set query's cache TTL
        """
        self._cache_ttl = value

    def cache(self, ttl: int):
        """Set query's cache TTL
        """
        self._cache_ttl = ttl

        return self

    def no_cache(self, field: str = None):
        """Disable caching of the field or entire query
        """
        if field:
            self._no_cache_fields.append(field)
        else:
            self.cache(0)

        return self

    def add(self, op: _query.Operator):
        """Add a query operator
        """
        self._query.add(op)

        return self

    def rm(self, field: str):
        """Remove all operator that use specified field
        """
        self.query.rm_field(field)

        return self

    def eq(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.And(_query.Eq(field, arg)))

    def gt(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.And(_query.Gt(field, arg)))

    def gte(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.And(_query.Gte(field, arg)))

    def lt(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.And(_query.Lt(field, arg)))

    def lte(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.And(_query.Lte(field, arg)))

    def ne(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.And(_query.Ne(field, arg)))

    def inc(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.And(_query.In(field, arg)))

    def ninc(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.And(_query.Nin(field, arg)))

    def regex(self, field: str, pattern: str, case_insensitive: bool = False, multiline: bool = False,
              dot_all: bool = False, verbose: bool = False):
        """Shortcut
        """
        return self.add(_query.And(_query.Regex(field, pattern, case_insensitive, multiline, dot_all, verbose)))

    def or_eq(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.Or(_query.Eq(field, arg)))

    def or_gt(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.Or(_query.Gt(field, arg)))

    def or_gte(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.Or(_query.Gte(field, arg)))

    def or_lt(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.Or(_query.Lt(field, arg)))

    def or_lte(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.Or(_query.Lte(field, arg)))

    def or_ne(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.Or(_query.Ne(field, arg)))

    def or_inc(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.Or(_query.In(field, arg)))

    def or_ninc(self, field: str, arg):
        """Shortcut
        """
        return self.add(_query.Or(_query.Nin(field, arg)))

    def text(self, search: str, language: str = None):
        """Shortcut
        """
        return self.add(_query.And(_query.Text(search, language)))

    def or_text(self, search: str, language: str = None):
        """Shortcut
        """
        return self.add(_query.Or(_query.Text(search, language)))

    def or_regex(self, field: str, pattern: str, case_insensitive: bool = False, multiline: bool = False,
                 dot_all: bool = False, verbose: bool = False):
        """Shortcut
        """
        return self.add(_query.Or(_query.Regex(field, pattern, case_insensitive, multiline, dot_all, verbose)))

    def skip(self, num: int):
        """Set number of records to skip in result cursor.
        """
        self._skip = num

        return self

    def sort(self, fields: _List[_Tuple[str, int]] = None):
        """Set sort criteria
        """
        self._sort = fields

        return self

    def add_sort(self, field: str, direction: int = _model.I_ASC, pos: int = None):
        """Add a sort criteria
        """
        if self._sort is None:
            self._sort = []

        if pos is None:
            pos = len(self._sort)

        self._sort.insert(pos, (field, direction))

        return self

    @_abstractmethod
    def count(self) -> int:
        """Count entities
        """
        raise NotImplementedError()

    @_abstractmethod
    def get(self, limit: int = 0) -> Result:
        """Get result
        """
        raise NotImplementedError()

    def first(self) -> _Union[_model.Entity, None]:
        """Get first result
        """
        result = list(self.get(1))

        if not result:
            return None

        return result[0]

    def delete(self, force: bool = False):
        """Delete all the entities matching search criteria
        """
        for entity in self.get():
            entity.delete(force=force)

        return self

    def __len__(self) -> int:
        return self.count()

    def __iter__(self):
        """Get iterator
        """
        return self.get()

    def __str__(self) -> str:
        return str(self._query.compile())


class SingleModelFinder(Finder):
    """ODM finder for querying single collection
    """

    def __init__(self, model: str, query: _query.Query = None):
        """Init
        """
        if not _api.is_model_registered(model):
            raise _error.ModelNotRegistered(model)

        self._model = model
        self._mock = _api.dispense(model)
        self._cache_pool = _cache.get_pool('odm.finder.' + model)

        super().__init__(_odm_query.ODMQuery(self._mock, query))

    @property
    def model(self) -> str:
        """Get finder model
        """
        return self._model

    @property
    def mock(self) -> _model.Entity:
        """Get finder mock entity
        """
        return self._mock

    def rm(self, field: str):
        """Remove all operator that use specified field
        """
        if not self._mock.has_field(field):
            raise _error.FieldNotDefined(self._model, field)

        return super().rm(field)

    def distinct(self, field: str) -> list:
        """Get a list of distinct values for field among all documents in the collection
        """
        from ._api import get_by_ref
        values = self._mock.collection.distinct(field, self._query.compile())

        r = []
        for v in values:
            # Transform references to entities
            if isinstance(v, _DBRef):
                v = get_by_ref(v)
            r.append(v)

        return r

    def sort(self, fields: _List[_Tuple[str, int]] = None):
        """Set sort criteria
        """
        if fields:
            for f in fields:
                if not self._mock.has_field(f[0]):
                    raise _error.FieldNotDefined(self._model, f[0])
            self._sort = fields

        return super().sort(fields)

    def add_sort(self, field: str, direction: int = _model.I_ASC, pos: int = None):
        """Add a sort criteria
        """
        if not self._mock.has_field(field):
            raise _error.FieldNotDefined(self._model, field)

        return super().add_sort(field, direction, pos)

    def count(self) -> int:
        """Count documents in collection
        """
        ckey = self.id + '_count'

        if self._cache_ttl and self._cache_pool.has(ckey):
            return self._cache_pool.get(ckey)

        cnt = self._mock.collection.count_documents(self._query.compile(), skip=self._skip)

        if self._cache_ttl:
            self._cache_pool.put(ckey, cnt, self._cache_ttl)

        return cnt

    def get(self, limit: int = 0) -> SingleModelResult:
        """Execute the query
        """
        self._limit = limit

        query = self._query.compile()

        # Try to load result from cache
        if self._cache_ttl and self._cache_pool.has(self.id):
            cached_ids = self._cache_pool.get_list(self.id)
            count = len(cached_ids) if cached_ids else 0
            return SingleModelResult(self._model, count, None, cached_ids, self._result_processor)

        cursor = self._mock.collection.find(
            filter=query,
            skip=self._skip,
            limit=self._limit,
            cursor_type=_CursorType.NON_TAILABLE,
            sort=self._sort,
        )

        # Result
        count = self._mock.collection.count_documents(query, skip=self._skip)
        return SingleModelResult(self._model, count, cursor, None, self._result_processor, self._cache_ttl,
                                 self._cache_pool, self.id)


class MultiModelFinder(Finder):
    """ODM finder for querying multiple collections
    """

    def __init__(self, models: _List[str], query: _query.Query = None):
        """Init
        """
        super().__init__(query)

        self._finders = [SingleModelFinder(model, query) for model in models]

    def add(self, op: _query.Operator):
        """Add a query criteria
        """
        # Add operator to every finder
        for f in self._finders:
            try:
                f.add(op)
            except _error.FieldNotDefined:
                pass

        return self

    def rm(self, field: str):
        """Remove all operator that use specified field
        """
        for f in self._finders:
            f.rm(field)

        return self

    def count(self):
        """Count entities
        """
        return sum([f.count() for f in self._finders])

    def get(self, limit: int = 0) -> MultiModelResult:
        """Get result
        """
        return MultiModelResult([f.skip(self._skip).get(limit) for f in self._finders], limit)
