"""PytSite ODM Plugin Aggregation
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from typing import List as _List, Dict as _Dict, Union as _Union
from pymongo.command_cursor import CommandCursor as _CommandCursor
from plugins import query as _query
from . import _api, _odm_query, _model


class Aggregator:
    """Abstraction of MongoDB Pipeline Aggregation

    https://docs.mongodb.com/manual/reference/operator/aggregation-pipeline/
    """

    def __init__(self, model: str):
        """Init
        """
        self._model = model
        self._mock = _api.dispense(model)
        self._pipeline = []

    @property
    def model(self) -> str:
        """Get model of the aggregator
        """
        return self._model

    @property
    def mock(self) -> _model.Entity:
        """Get mock of the aggregator
        """
        return self._mock

    @property
    def pipeline(self) -> list:
        """Get pipeline of the aggregator
        """
        return self._pipeline

    def match(self, op: _query.Operator):
        """Add a match stage

        https://docs.mongodb.com/manual/reference/operator/aggregation/match/
        """
        self._pipeline.append(('$match', _odm_query.ODMQuery(self._mock, op).compile()))

        return self

    def group(self, expression: dict):
        """Add a group stage

        https://docs.mongodb.com/manual/reference/operator/aggregation/group/
        """
        self._pipeline.append(('$group', expression))

        return self

    def lookup(self, foreign_model: str, local_field: str, foreign_field: str, as_field: str):
        """Add a lookup stage

        https://docs.mongodb.com/manual/reference/operator/aggregation/lookup/
        """
        self._pipeline.append(('$lookup', {
            'from': _api.get_model_collection(foreign_model).name,
            'localField': local_field,
            'foreignField': foreign_field,
            'as': as_field,
        }))

        return self

    def sort(self, fields: _Dict[str, _Union[int, _Dict[str, str]]]):
        """Add a sort stage

        https://docs.mongodb.com/manual/reference/operator/aggregation/sort/
        """
        self._pipeline.append(('$sort', fields))

        return self

    def limit(self, limit: int):
        """Add a limit stage

        https://docs.mongodb.com/manual/reference/operator/aggregation/limit/
        """
        self._pipeline.append(('$limit', limit))

        return self

    def _compile(self) -> _List[_Dict]:
        """Compile pipeline expression
        """
        return [{stage[0]: stage[1]} for stage in self._pipeline]

    def get(self) -> _CommandCursor:
        """Perform aggregation operation and get cursor
        """
        return self._mock.collection.aggregate(self._compile())

    def __iter__(self):
        return self.get()

    def __str__(self) -> str:
        return str(self._compile())
