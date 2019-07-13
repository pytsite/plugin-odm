"""PytSite ODM Plugin API Functions
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from typing import Union, Optional, List, Tuple, Type
from bson import errors as bson_errors
from bson.dbref import DBRef
from bson.objectid import ObjectId
from pymongo.collection import Collection
from pytsite import mongodb, util, events, cache, lang, console
from plugins.query import Query
from . import _model, _error, _finder

_ENTITIES_CACHE = cache.get_pool('odm.entities')
_MODEL_TO_CLASS = {}
_MODEL_TO_COLLECTION = {}
_COLLECTION_NAME_TO_MODEL = {}


def register_model(model: str, cls: Union[str, Type[_model.Entity]], replace: bool = False):
    """Register a new ODM model
    """
    if isinstance(cls, str):
        cls = util.get_module_attr(cls)  # type: Type[_model.Entity]

    if not issubclass(cls, _model.Entity):
        raise TypeError("Unable to register model '{}': subclass of odm.model.Entity expected."
                        .format(model))

    if is_model_registered(model) and not replace:
        raise _error.ModelAlreadyRegistered(model)

    # Create finder cache pool for each newly registered model
    if not replace:
        cache.create_pool('odm.finder.' + model)

    _MODEL_TO_CLASS[model] = cls

    cls.on_register(model)
    events.fire('odm@model.register', model=model, cls=cls, replace=replace)

    mock = dispense(model)

    # Save model's collection name
    _MODEL_TO_COLLECTION[model] = mock.collection
    _COLLECTION_NAME_TO_MODEL[mock.collection.name] = model

    # Automatically create indices on new collections
    if mock.collection.name not in mongodb.get_collection_names():
        mock.create_indexes()


def unregister_model(model: str):
    """Unregister model
    """
    if not is_model_registered(model):
        raise _error.ModelNotRegistered(model)

    del _MODEL_TO_CLASS[model]


def is_model_registered(model: str) -> bool:
    """Checks if the model already registered
    """
    return model in _MODEL_TO_CLASS


def get_model_class(model: str) -> Type[_model.Entity]:
    """Get registered class for model name
    """
    try:
        return _MODEL_TO_CLASS[model]
    except KeyError:
        raise _error.ModelNotRegistered(model)


def get_model_collection(model: str) -> Collection:
    """Get a collection connected to model
    """
    try:
        return _MODEL_TO_COLLECTION[model]
    except KeyError:
        raise _error.ModelNotRegistered(model)


def get_registered_models() -> Tuple[str, ...]:
    """Get registered models names
    """
    return tuple(_MODEL_TO_CLASS.keys())


def parse_ref_str(ref: str) -> List[str]:
    """Parse a reference string
    """
    try:
        parts = ref.split(':')
        if len(parts) != 2:
            raise ValueError()

        # Check if the ObjectID is valid
        ObjectId(parts[1])

    except (ValueError, TypeError, bson_errors.InvalidId):
        raise _error.InvalidReference(ref)

    if not is_model_registered(parts[0]):
        raise _error.ModelNotRegistered(parts[0])

    return parts


def resolve_ref(something: Union[None, str, _model.Entity, DBRef],
                as_str: bool = True) -> Optional[Union[str, Tuple[str, ...]]]:
    """Resolve a reference
    """
    if not something:
        return None

    model = uid = None

    if isinstance(something, str):
        model, uid = parse_ref_str(something)

    elif isinstance(something, _model.Entity):
        model, uid = parse_ref_str(something.ref)

    elif isinstance(something, DBRef):
        try:
            model, uid = _COLLECTION_NAME_TO_MODEL[something.collection], something.id
        except KeyError:
            raise _error.UnknownCollection(something.collection)

    if model and uid:
        return '{}:{}'.format(model, uid) if as_str else (model, uid)
    else:
        raise _error.InvalidReference(something)


def resolve_refs(something: Union[list, tuple]) -> List[str]:
    """Resolve multiple references
    """
    return [resolve_ref(v) for v in something]


def dispense(model: str, eid: Union[int, str, ObjectId, None] = None) -> _model.Entity:
    """Dispense an entity
    """
    if not is_model_registered(model):
        raise _error.ModelNotRegistered(model)

    return get_model_class(model)(model, None if eid in (0, '0') else eid)


def get_by_ref(ref: Union[None, str, _model.Entity, DBRef]) -> Optional[_model.Entity]:
    """Get entity by reference
    """
    return dispense(*resolve_ref(ref, False)) if ref else None


def reindex(model: str = None):
    """Reindex model(s)'s collection
    """
    if model:
        console.print_info(lang.t('odm@reindex_model', {'model': model}))
        dispense(model).reindex()
    else:
        for model in get_registered_models():
            reindex(model)


def find(model: Union[str, List[str]], query: Query = None) -> _finder.SingleModelFinder:
    """Get finder's instance
    """
    return _finder.SingleModelFinder(model, query)


def mfind(models: List[str], query: Query = None) -> _finder.MultiModelFinder:
    return _finder.MultiModelFinder(models, query)


def aggregate(model: str):
    """Get aggregator instance
    """
    from ._aggregation import Aggregator

    return Aggregator(model)


def clear_cache(model: str):
    """Get finder cache pool
    """
    try:
        # Clear finder cache
        cache.get_pool('odm.finder.' + model).clear()

        # Cleanup entities cache
        for k in _ENTITIES_CACHE.keys():
            if k.startswith(model + '.'):
                _ENTITIES_CACHE.rm(k)

        events.fire('odm@cache.clear', model=model)
    except cache.error.PoolNotExist:
        pass


def on_model_register(handler, priority: int = 0):
    """Shortcut
    """
    events.listen('odm@model.register', handler, priority)


def on_model_setup_fields(handler, priority: int = 0):
    """Shortcut
    """
    events.listen('odm@model.setup_fields', handler, priority)


def on_model_setup_indexes(handler, priority: int = 0):
    """Shortcut
    """
    events.listen('odm@model.setup_indexes', handler, priority)


def on_entity_pre_save(handler, priority: int = 0):
    """Shortcut
    """
    events.listen('odm@entity.pre_save', handler, priority)


def on_entity_save(handler, priority: int = 0):
    """Shortcut
    """
    events.listen('odm@entity.save', handler, priority)


def on_entity_pre_delete(handler, priority: int = 0):
    """Shortcut
    """
    events.listen('odm@entity.pre_delete', handler, priority)


def on_entity_delete(handler, priority: int = 0):
    """Shortcut
    """
    events.listen('odm@entity.delete', handler, priority)


def on_cache_clear(handler, priority: int = 0):
    """Shortcut
    """
    events.listen('odm@cache.clear', handler, priority)
