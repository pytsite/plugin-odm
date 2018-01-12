"""PytSite ODM Plugin Aggregation
"""

from typing import Any as _Any, List as _List, Dict as _Dict, Union as _Union
from . import _api, _query

__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'


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

    def match(self, field_name: str, comparison_op: str, arg: _Any):
        """Add a match stage

        https://docs.mongodb.com/manual/reference/operator/aggregation/match/
        """
        q = _query.Query(self._mock)
        q.add_criteria('$and', field_name, comparison_op, arg)

        self._pipeline.append(('$match', q.compile()))

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

    def _compile(self) -> list:
        """Compile pipeline expression
        """
        r = []

        for stage in self._pipeline:
            r.append({stage[0]: stage[1]})

        return r

    def get(self) -> _List[_Dict]:
        """Perform aggregation operation.
        """
        return self._mock.collection.aggregate(self._compile())
