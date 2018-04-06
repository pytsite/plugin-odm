"""PytSite ODM Plugin Finder
"""
__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from typing import List as _List, Tuple as _Tuple, Union as _Union
from bson import DBRef as _DBRef
from pymongo.cursor import Cursor as _Cursor, CursorType as _CursorType
from pytsite import util as _util, reg as _reg, cache as _cache, logger as _logger
from plugins import query as _query
from . import _model, _api, _odm_query

_DBG = _reg.get('odm.debug_finder')
_DEFAULT_CACHE_TTL = _reg.get('odm.cache_ttl', 86400)  # 24 hours


class Result:
    """Finder Result
    """

    def __init__(self, model: str, cursor: _Cursor = None, ids: list = None):
        """Init
        """
        self._model = model
        self._cursor = cursor
        self._ids = [doc['_id'] for doc in list(cursor)] if cursor else ids
        self._total = len(self._ids)
        self._current = 0

    @property
    def model(self) -> str:
        return self._model

    @property
    def ids(self) -> list:
        return self._ids

    def __iter__(self):
        """Get iterator
        """
        return self

    def __next__(self) -> _model.Entity:
        """Get next item
        """
        if self._current == self._total:
            raise StopIteration()

        entity = _api.dispense(self._model, self._ids[self._current])
        self._current += 1

        return entity

    def __len__(self) -> int:
        return self._total

    def count(self) -> int:
        return self._total

    def explain(self) -> dict:
        """Explain the cursor
        """
        if not self._cursor:
            raise RuntimeError('Cannot explain cached results.')

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


class Finder:
    def __init__(self, model: str, cache_pool: _cache.Pool, limit: int = 0, skip: int = 0):
        """Init.
        """
        self._model = model
        self._cache_pool = cache_pool
        self._cache_ttl = _DEFAULT_CACHE_TTL
        self._cache_key = []
        self._mock = _api.dispense(model)
        self._query = _odm_query.ODMQuery(self._mock)
        self._skip = skip
        self._limit = limit
        self._sort = None

    @property
    def model(self) -> str:
        """Get entity mock.
        """
        return self._model

    @property
    def mock(self) -> _model.Entity:
        """Get entity mock.
        """
        return self._mock

    @property
    def query(self) -> _odm_query.ODMQuery:
        return self._query

    @property
    def id(self) -> str:
        """Get unique finder's ID to use as a cache key, etc
        """
        return _util.md5_hex_digest(str((self._cache_key, self._skip, self._limit, self._sort)))

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

    def add(self, op: _query.Operator, cache: bool = True):
        """Add a query operator
        """
        self._query.add(op)

        if cache:
            self._cache_key.append(op.compile())

        return self

    def eq(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.And(_query.Eq(field, arg)), cache)

    def gt(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.And(_query.Gt(field, arg)), cache)

    def gte(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.And(_query.Gte(field, arg)), cache)

    def lt(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.And(_query.Lt(field, arg)), cache)

    def lte(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.And(_query.Lte(field, arg)), cache)

    def ne(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.And(_query.Ne(field, arg)), cache)

    def inc(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.And(_query.In(field, arg)), cache)

    def ninc(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.And(_query.Nin(field, arg)), cache)

    def regex(self, field: str, pattern: str, case_insensitive: bool = False, multiline: bool = False,
              dot_all: bool = False, verbose: bool = False):
        """Shortcut
        """
        return self.add(_query.And(_query.Regex(field, pattern, case_insensitive, multiline, dot_all, verbose)))

    def or_eq(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.Or(_query.Eq(field, arg)), cache)

    def or_gt(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.Or(_query.Gt(field, arg)), cache)

    def or_gte(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.Or(_query.Gte(field, arg)), cache)

    def or_lt(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.Or(_query.Lt(field, arg)), cache)

    def or_lte(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.Or(_query.Lte(field, arg)), cache)

    def or_ne(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.Or(_query.Ne(field, arg)), cache)

    def or_inc(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.Or(_query.In(field, arg)), cache)

    def or_ninc(self, field: str, arg, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.Or(_query.Nin(field, arg)), cache)

    def text(self, search: str, language: str = None, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.And(_query.Text(search, language)), cache)

    def or_text(self, search: str, language: str = None, cache: bool = True):
        """Shortcut
        """
        return self.add(_query.Or(_query.Text(search, language)), cache)

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
        if fields:
            for f in fields:
                if f[0] != '_id' and not self._mock.has_field(f[0]):
                    raise RuntimeError("Unknown field '{}' in model '{}'".format(f[0], self._model))
            self._sort = fields
        else:
            self._sort = None

        return self

    def add_sort(self, field: str, direction: int = _model.I_ASC, pos: int = None):
        if self._sort is None:
            self._sort = []

        if pos is None:
            pos = len(self._sort)

        self._sort.insert(pos, (field, direction))

        return self

    def count(self) -> int:
        """Count documents in collection
        """
        if self._cache_ttl:
            try:
                return self._cache_pool.get(self.id + '_count')

            except _cache.error.KeyNotExist:
                pass

        count = self._mock.collection.count(filter=self._query.compile(), skip=self._skip)

        if self._cache_ttl:
            self._cache_pool.put(self.id + '_count', count, self._cache_ttl)

        return count

    def get(self, limit: int = None) -> Result:
        """Execute the query
        """
        if limit is not None:
            self._limit = limit

        query = self._query.compile()

        # Search for previous result in cache
        if self._cache_ttl:
            try:
                ids = self._cache_pool.get(self.id)
                if _DBG:
                    _logger.debug("GET cached query results: query: {}, {}, id: {}, entities: {}.".
                                  format(self.model, query, self.id, len(ids)))
                return Result(self._model, ids=ids)

            except _cache.error.KeyNotExist:
                pass

        cursor = self._mock.collection.find(
            filter=query,
            projection={'_id': True},
            skip=self._skip,
            limit=self._limit,
            cursor_type=_CursorType.NON_TAILABLE,
            sort=self._sort,
        )

        # Prepare result
        result = Result(self._model, cursor)

        # Put query result into cache
        if self._cache_ttl:
            if _DBG:
                _logger.debug("STORE query results: query: {}, {}, id: {}, entities: {}, TTL: {}.".
                              format(self.model, query, self.id, result.count(), self._cache_ttl))

            self._cache_pool.put(self.id, result.ids, self._cache_ttl)

        return result

    def first(self) -> _Union[_model.Entity, None]:
        """Execute the query and return a first result
        """
        result = list(self.get(1))

        if not result:
            return None

        return result[0]

    def delete(self):
        """Delete all the entities matching search criteria
        """
        for entity in self.get():
            entity.delete()

        return self

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

    def __len__(self) -> int:
        return self.count()

    def __iter__(self):
        return self.get()

    def __str__(self) -> str:
        return str(self._query.compile())
