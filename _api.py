"""PytSite ODM Plugin API Functions
"""
__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from typing import Union as _Union, Optional as _Optional, List as _List, Tuple as _Tuple, Type as _Type
from bson import errors as _bson_errors
from bson.dbref import DBRef as _DBRef
from bson.objectid import ObjectId as _ObjectId
from pymongo.collection import Collection as _Collection
from pytsite import mongodb as _db, util as _util, events as _events, cache as _cache, lang as _lang, \
    console as _console
from plugins import query as _query
from . import _model, _error, _finder

_ENTITIES_CACHE = _cache.get_pool('odm.entities')
_MODEL_TO_CLASS = {}
_MODEL_TO_COLLECTION = {}
_COLLECTION_NAME_TO_MODEL = {}


def register_model(model: str, cls: _Union[str, _Type[_model.Entity]], replace: bool = False):
    """Register a new ODM model
    """
    if isinstance(cls, str):
        cls = _util.get_module_attr(cls)  # type: _Type[_model.Entity]

    if not issubclass(cls, _model.Entity):
        raise TypeError("Unable to register model '{}': subclass of odm.model.Entity expected."
                        .format(model))

    if is_model_registered(model) and not replace:
        raise _error.ModelAlreadyRegistered("Model '{}' is already registered.".format(model))

    # Create finder cache pool for each newly registered model
    if not replace:
        _cache.create_pool('odm.finder.' + model)

    _MODEL_TO_CLASS[model] = cls

    cls.on_register(model)
    _events.fire('odm@model.register', model=model, cls=cls, replace=replace)

    mock = dispense(model)

    # Save model's collection name
    _MODEL_TO_COLLECTION[model] = mock.collection
    _COLLECTION_NAME_TO_MODEL[mock.collection.name] = model

    # Automatically create indices on new collections
    if mock.collection.name not in _db.get_collection_names():
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


def get_model_class(model: str) -> _Type[_model.Entity]:
    """Get registered class for model name
    """
    try:
        return _MODEL_TO_CLASS[model]
    except KeyError:
        raise _error.ModelNotRegistered(model)


def get_model_collection(model: str) -> _Collection:
    try:
        return _MODEL_TO_COLLECTION[model]
    except KeyError:
        raise _error.ModelNotRegistered(model)


def get_registered_models() -> _Tuple[str, ...]:
    """Get registered models names
    """
    return tuple(_MODEL_TO_CLASS.keys())


def parse_manual_ref(ref: str) -> _List[str]:
    """Parse a manual reference string
    """
    try:
        parts = ref.split(':')
        if len(parts) != 2:
            raise ValueError()

        # Check if the ObjectID is valid
        _ObjectId(parts[1])

    except (ValueError, TypeError, _bson_errors.InvalidId):
        raise _error.InvalidReference(ref)

    if not is_model_registered(parts[0]):
        raise _error.ModelNotRegistered(parts[0])

    return parts


def resolve_ref(something: _Union[str, _model.Entity, _DBRef, None], implied_model: str = None) -> _Optional[_DBRef]:
    """Resolve DB object reference
    """
    if isinstance(something, _DBRef) or something is None:
        return something

    elif isinstance(something, _model.Entity):
        return something.ref

    elif isinstance(something, str):
        model, uid = parse_manual_ref(something)
        return _DBRef(dispense(model).collection.name, _ObjectId(uid))

    elif isinstance(something, dict):
        if 'uid' not in something:
            raise ValueError('UID must be specified')

        if not implied_model and 'model' not in something:
            raise ValueError('Model must be specified')

        if 'model' not in something and implied_model == '*':
            raise ValueError('Model must be specified')

        model = implied_model if implied_model else something['model']

        return resolve_ref('{}:{}'.format(model, something['uid']))

    raise _error.InvalidReference(something)


def resolve_refs(something: _List, implied_model: str = None) -> _List[_DBRef]:
    """Resolve multiple DB objects references
    """
    return [resolve_ref(v, implied_model) for v in something]


def get_by_ref(ref: _Union[str, _DBRef]) -> _model.Entity:
    """Dispense entity by DBRef or manual reference
    """
    ref = resolve_ref(ref)
    doc = _db.get_database().dereference(ref)

    if not doc:
        raise _error.ReferencedDocumentNotFound(ref)

    return dispense(doc['_model'], doc['_id'])


def resolve_manual_ref(something: _Union[str, _model.Entity, _DBRef]) -> str:
    """Resolve manual reference
    """
    if isinstance(something, str):
        return '{}:{}'.format(*parse_manual_ref(something))

    elif isinstance(something, _model.Entity):
        return something.manual_ref

    elif isinstance(something, _DBRef):
        try:
            return '{}:{}'.format(_COLLECTION_NAME_TO_MODEL[something.collection], something.id)
        except KeyError:
            raise _error.UnknownCollection(something.collection)

    raise ValueError("Cannot resolve DB manual reference from '{}'".format(something))


def resolve_manual_refs(something: _List) -> _List[str]:
    return [resolve_manual_ref(v) for v in something]


def dispense(model: str, uid: _Union[int, str, _ObjectId, None] = None) -> _model.Entity:
    """Dispense an entity
    """
    if not is_model_registered(model):
        raise _error.ModelNotRegistered(model)

    # Sanitize entity ID
    if uid in (0, '0'):
        uid = None

    model_class = get_model_class(model)

    # Get an existing entity
    if uid:
        return model_class(model, uid)

    # Create a new entity
    else:
        return model_class(model)


def reindex(model: str = None):
    """Reindex model(s)'s collection
    """
    if model:
        _console.print_info(_lang.t('odm@reindex_model', {'model': model}))
        dispense(model).reindex()
    else:
        for model in get_registered_models():
            reindex(model)


def find(model: str, limit: int = 0, skip: int = 0, query: _query.Query = None) -> _finder.Finder:
    """Get finder's instance
    """
    f = _finder.Finder(model, _cache.get_pool('odm.finder.' + model), limit, skip)

    if query:
        for op in query:
            f.add(op)

    return f


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
        _cache.get_pool('odm.finder.' + model).clear()

        # Cleanup entities cache
        for k in _ENTITIES_CACHE.keys():
            if k.startswith(model + '.'):
                _ENTITIES_CACHE.rm(k)

        _events.fire('odm@cache.clear', model=model)
    except _cache.error.PoolNotExist:
        pass


def on_model_register(handler, priority: int = 0):
    """Shortcut
    """
    _events.listen('odm@model.register', handler, priority)


def on_model_setup_fields(handler, priority: int = 0):
    """Shortcut
    """
    _events.listen('odm@model.setup_fields', handler, priority)


def on_model_setup_indexes(handler, priority: int = 0):
    """Shortcut
    """
    _events.listen('odm@model.setup_indexes', handler, priority)


def on_entity_pre_save(handler, priority: int = 0):
    """Shortcut
    """
    _events.listen('odm@entity.pre_save', handler, priority)


def on_entity_save(handler, priority: int = 0):
    """Shortcut
    """
    _events.listen('odm@entity.save', handler, priority)


def on_entity_pre_delete(handler, priority: int = 0):
    """Shortcut
    """
    _events.listen('odm@entity.pre_delete', handler, priority)


def on_entity_delete(handler, priority: int = 0):
    """Shortcut
    """
    _events.listen('odm@entity.delete', handler, priority)


def on_cache_clear(handler, priority: int = 0):
    """Shortcut
    """
    _events.listen('odm@cache.clear', handler, priority)
