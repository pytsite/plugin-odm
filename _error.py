"""PytSite ODM Plugin Errors
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from pytsite import errors as _errors


class Error(Exception):
    pass


class ModelAlreadyRegistered(Error):
    def __init__(self, model: str):
        self._model = model

    def __str__(self) -> str:
        return "ODM model '{}' is already registered".format(self._model)


class ModelNotRegistered(Error):
    def __init__(self, model: str):
        self._model = model

    def __str__(self) -> str:
        return "ODM model '{}' is not registered".format(self._model)


class UnknownCollection(Error):
    def __init__(self, collection: str):
        self._collection = collection

    def __str__(self) -> str:
        return "There is no model registered for collection '{}'".format(self._collection)


class InvalidReference(Error):
    def __init__(self, ref):
        self._ref = ref

    def __str__(self) -> str:
        return "Invalid reference: {}".format(self._ref)


class EntityNotFound(Error, _errors.NotFound):
    def __init__(self, model: str, eid: str):
        self._model = model
        self._eid = eid

    @property
    def model(self) -> str:
        return self._model

    @property
    def eid(self) -> str:
        return self._eid

    def __str__(self):
        return "Entity '{}:{}' is not found in database".format(self._model, self._eid)


class EntityNotStored(Error):
    def __init__(self, model: str):
        self._model = model

    def __str__(self) -> str:
        return "Entity of model '{}' must be stored before you can get its reference".format(self._model)


class FieldNotDefined(Error):
    def __init__(self, model: str, field_name: str):
        super().__init__()

        self._model = model
        self._field_name = field_name

    def __str__(self) -> str:
        return "Field '{}' is not defined in model '{}'".format(self._field_name, self._model)


class EntityDeleted(Error):
    def __init__(self, ref: str):
        super().__init__()

        self._ref = ref

    def __str__(self) -> str:
        return "Entity '{}' was deleted".format(self._ref)


class RequiredFieldEmpty(Error):
    def __init__(self, model: str, field_name: str):
        super().__init__()

        self._model = model
        self._field_name = field_name

    def __str__(self) -> str:
        return "Field '{}.{}' cannot be empty".format(self._model, self._field_name)
