"""PytSite ODM Plugin Query
"""
__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from typing import Union as _Union, Iterator as _Iterator
from bson import ObjectId as _ObjectId
from plugins import query as _query
from . import _model


class ODMQuery(_query.Query):
    """Query
    """

    def __init__(self, entity_mock: _model.Entity, ops: _Union[_query.Operator, _Iterator[_query.Operator]] = None,
                 query: _query.Query = None):
        """Init
        """
        # Mock entity to determine field types, etc
        self._entity_mock = entity_mock

        super().__init__(ops, query)

    @classmethod
    def _sanitize_object_ids(cls, ids: _Union[str, list, tuple]) -> _Union[_ObjectId, list]:
        if isinstance(ids, _ObjectId):
            return ids
        elif isinstance(ids, str):
            return _ObjectId(ids)
        elif isinstance(ids, (list, tuple)):
            clean_arg = []
            for i in ids:
                clean_arg.append(cls._sanitize_object_ids(i))

            return clean_arg
        else:
            TypeError('{} cannot be converted to object id(s).'.format(type(ids)))

    def _sanitize_operator(self, op: _query.Operator):
        if isinstance(op, _query.LogicalOperator):
            for sub_op in op:
                self._sanitize_operator(sub_op)

        # It is possible to perform checks only for top-level fields
        elif isinstance(op, _query.ComparisonOperator) and op.field.find('.') < 0:
            if op.field == '_id':
                op.arg = self._sanitize_object_ids(op.arg)
            else:
                # Ask entity's field to perform check
                op.arg = self._entity_mock.get_field(op.field).sanitize_finder_arg(op.arg)

        return op

    def add(self, op: _query.Operator) -> _query.Operator:
        return super().add(self._sanitize_operator(op))
