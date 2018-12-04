"""PytSite ODM Plugin Entity Model
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from typing import Any as _Any, Dict as _Dict, List as _List, Tuple as _Tuple, Union as _Union
from abc import ABC as _ABC, abstractmethod as _abstractmethod
from collections import OrderedDict as _OrderedDict
from datetime import datetime as _datetime
from pymongo import ASCENDING as I_ASC, DESCENDING as I_DESC, GEO2D as I_GEO2D, TEXT as I_TEXT, GEOSPHERE as I_GEOSPHERE
from bson.objectid import ObjectId as _ObjectId
from pymongo.collection import Collection as _Collection
from pymongo.errors import OperationFailure as _OperationFailure
from pytsite import mongodb as _db, events as _events, lang as _lang, errors as _errors, cache as _cache, reg as _reg
from . import _error, _field, _queue

_CACHE_POOL = _cache.get_pool('odm.entities')
_CACHE_TTL = _reg.get('odm.cache_ttl', 86400)


class Entity(_ABC):
    """ODM Model.
    """

    def __init__(self, model: str, obj_id: _Union[str, _ObjectId, None] = None):
        """Init.
        """
        # Let developer to specify collection name manually
        if not hasattr(self, '_collection_name'):
            self._collection_name = None

        # Define collection name if it wasn't specified
        if self._collection_name is None:
            if model[-1:] in ('s', 'h'):
                self._collection_name = model + 'es'
            elif model[-1:] in ('y',):
                self._collection_name = model[:-1] + 'ies'
            else:
                self._collection_name = model + 's'

        self._model = model
        self._is_new = True
        self._is_modified = True
        self._is_being_deleted = False
        self._is_deleted = False
        self._indexes = []
        self._has_text_index = False
        self._pending_children = []

        self._fields = _OrderedDict()  # type: _Dict[str, _field.Abstract]

        # Define 'system' fields
        self.define_field(_field.ObjectId('_id', required=True))
        self.define_field(_field.String('_ref', required=True))
        self.define_field(_field.String('_model', required=True, default=self._model))
        self.define_field(_field.Ref('_parent', model=model))
        self.define_field(_field.Integer('_depth', required=True, default=0))
        self.define_field(_field.DateTime('_created', default=_datetime.now()))
        self.define_field(_field.DateTime('_modified', default=_datetime.now()))

        # Delegate fields setup process to the hook method
        self._setup_fields()
        _events.fire('odm@model.setup_fields', entity=self)
        _events.fire('odm@model.setup_fields.{}'.format(model), entity=self)

        # Delegate indexes setup process to the hook method
        self.define_index([('_parent', I_ASC)])
        self._setup_indexes()
        _events.fire('odm@model.setup_indexes', entity=self)
        _events.fire('odm@model.setup_indexes.{}'.format(model), entity=self)

        # Load fields data from database or cache
        if obj_id:
            self._load_fields_data(_ObjectId(obj_id) if isinstance(obj_id, str) else obj_id)

    @classmethod
    def on_register(cls, model: str):
        pass

    def _load_fields_data(self, eid: _ObjectId):
        """Load fields data from the database
        """
        cache_key = '{}.{}'.format(self._model, eid)

        # Try to load entity data from cache
        try:
            data = _CACHE_POOL.get(cache_key)

        # Get entity data from database
        except _cache.error.KeyNotExist:
            data = self.collection.find_one({'_id': eid})
            if not data:
                raise _error.EntityNotFound(self._model, str(eid))

            # Put loaded data into the cache
            _CACHE_POOL.put(cache_key, data, _CACHE_TTL)

        # Fill fields with values from loaded data
        for f_name, f_value in data.items():
            try:
                field = self.get_field(f_name)

                # Fields that must not be overwritten
                if f_name == '_model' or not field.storable:
                    continue

                field.uid = '{}.{}.{}'.format(self._model, eid, f_name)
                field.set_val(f_value, from_db=True)
            except _error.FieldNotDefined:
                # Fields definition may be removed from version to version, so just ignore this situation
                pass

        # On versions prior to 1.4 field '_ref' didn't exist, so we need to check it
        if not self.f_get('_ref'):
            self.f_set('_ref', '{}:{}'.format(self.model, self.id))

        # Of course, loaded entity cannot be 'new' and 'modified'
        self._is_new = False
        self._is_modified = False

    def define_index(self, definition: _List[_Tuple], unique: bool = False, name: str = None):
        """Define an index.
        """
        opts = {
            'unique': unique,
        }

        if name:
            opts['name'] = name

        for item in definition:
            if not isinstance(item, tuple):
                raise TypeError("Model '{}'. List of tuples expected as index definition, got: '{}'".
                                format(self._model, definition))
            if len(item) != 2:
                raise ValueError("Index definition single item must have exactly 2 members.")

            field_name, index_type = item

            # Check for field existence
            if not self.has_field(field_name.split('.')[0]):
                raise RuntimeError("Entity {} doesn't have field {}.".format(self._model, field_name))

            # Check index type
            if index_type not in (I_ASC, I_DESC, I_GEO2D, I_TEXT, I_GEOSPHERE):
                raise ValueError("Invalid index type.")

            # Language field for text indexes
            if index_type == I_TEXT:
                self._has_text_index = True
                opts['language_override'] = 'language_db'

        self._indexes.append((definition, opts))

    def define_field(self, field_obj: _field.Abstract):
        """Define a field.
        """
        if self.has_field(field_obj.name):
            raise RuntimeError("Field '{}' already defined in model '{}'.".format(field_obj.name, self._model))

        self._fields[field_obj.name] = field_obj
        field_obj.entity = self

        return self

    def remove_field(self, field_name: str):
        """Remove field definition.
        """
        if not self.has_field(field_name):
            raise Exception("Field '{}' is not defined in model '{}'.".format(field_name, self._model))

        del self._fields[field_name]

    def create_indexes(self):
        """Create indices.
        """
        for index_data in self.indexes:
            self.collection.create_index(index_data[0], **index_data[1])

    @property
    def indexes(self) -> list:
        """Get index information.
        """
        return self._indexes

    @property
    def has_text_index(self) -> bool:
        return self._has_text_index

    def reindex(self):
        """Rebuild indices.
        """
        try:
            # Drop existing indices
            indices = self.collection.index_information()
            for i_name, i_val in indices.items():
                if i_name != '_id_':
                    self.collection.drop_index(i_name)
        except _OperationFailure:  # Collection does not exist in database
            pass

        self.create_indexes()

    @_abstractmethod
    def _setup_fields(self):
        """Hook.
        """
        pass

    def _setup_indexes(self):
        """Hook
        """
        pass

    def _check_is_not_deleted(self):
        """Raise an exception if the entity has 'deleted' state.
        """
        if self._is_deleted:
            raise _error.EntityDeleted(self.ref)

    def has_field(self, field_name: str) -> bool:
        """Check if the entity has a field.
        """
        return False if field_name not in self._fields else True

    def get_field(self, field_name: str) -> _field.Abstract:
        """Get field's object.
        """
        if not self.has_field(field_name):
            raise _error.FieldNotDefined(self._model, field_name)

        return self._fields[field_name]

    @property
    def collection(self) -> _Collection:
        """Get entity's collection.
        """
        return _db.get_collection(self._collection_name)

    @property
    def fields(self) -> _Dict[str, _field.Abstract]:
        """Get all field objects.
        """
        return self._fields

    @property
    def id(self) -> _Union[_ObjectId, None]:
        """Get entity ID.
        """
        return self.f_get('_id')

    @property
    def ref(self) -> str:
        if not self.id:
            raise _error.EntityNotStored(self._model)

        return self.f_get('_ref')

    @property
    def model(self) -> str:
        """Get model name.
        """
        return self._model

    @property
    def parent(self):
        """Get parent entity
        :rtype: Entity
        """
        return self.f_get('_parent')

    @parent.setter
    def parent(self, value):
        """Get parent entity
        """
        self.f_set('_parent', value)

    @property
    def children(self):
        """Get children entities

        :rtype: typing.Iterable[Entity]
        """
        if self.is_new:
            return []

        from . import _api

        return _api.find(self._model).eq('_parent', self).get()

    @property
    def children_count(self) -> int:
        """Get number of children
        """
        if self.is_new:
            return 0

        from . import _api

        return _api.find(self._model).eq('_parent', self).count()

    @property
    def has_children(self) -> bool:
        """Check if the entity has at least one child
        """
        return bool(self.children_count)

    @property
    def descendants(self):
        """Get descendant entities

        :rtype: typing.Iterable[Entity]
        """
        for child in self.children:
            yield child
            for d in child.descendants:
                yield d

    @property
    def depth(self) -> int:
        """Get depth of the entity in the tree
        """
        return self.f_get('_depth')

    @depth.setter
    def depth(self, value: int):
        """Get depth of the entity in the tree
        """
        self.f_set('_depth', value)

    @property
    def created(self) -> _datetime:
        """Get date/time when the entity was created
        """
        return self.f_get('_created')

    @created.setter
    def created(self, value: int):
        """Set date/time when the entity was created
        """
        self.f_set('_created', value)

    @property
    def modified(self) -> _datetime:
        """Get date/time when the entity was modified
        """
        return self.f_get('_modified')

    @modified.setter
    def modified(self, value: int):
        """Set date/time when the entity was modified
        """
        self.f_set('_modified', value)

    @property
    def is_new(self) -> bool:
        """Is the entity stored in the database?
        """
        return self._is_new

    @property
    def is_modified(self) -> bool:
        """Is the entity has been modified?
        """
        return self._is_modified

    @property
    def is_deleted(self) -> bool:
        """Is the entity has been deleted?
        """
        return self._is_deleted

    @property
    def is_being_deleted(self) -> bool:
        """Is entity is being deleted?
        """
        return self._is_being_deleted

    def f_set(self, field_name: str, value, update_state: bool = True, **kwargs):
        """Set field's value.
        """
        field = self.get_field(field_name)

        field.set_val(self._on_f_set(field_name, value, **kwargs), **kwargs)

        # Check relations
        if field_name == '_parent':
            parent = field.get_val()  # type: Entity

            if parent:
                if not self.is_new and parent == self:
                    raise RuntimeError('Entity cannot be parent of itself')
                if parent.is_descendant_of(self):
                    raise RuntimeError('Entity {} cannot be parent of {} as it is its descendant'.format(parent, self))

            # Update depth
            self.depth = parent.depth + 1 if parent else 0

            # Recalculate depths of children
            for child in self.children:
                child.depth = self.depth + 1

        elif field_name == '_depth':
            # Recalculate depths of children
            for child in self.children:
                child.depth = field.get_val() + 1
                self._pending_children.append(child)

        if update_state:
            self._is_modified = True

        return self

    def f_set_multiple(self, data: dict):
        """Set multiple fields's values
        """
        for f_name, f_val in data.items():
            self.f_set(f_name, f_val)

        return self

    def _on_f_set(self, field_name: str, value, **kwargs):
        """On set field's value hook.
        """
        return value

    def f_get(self, field_name: str, **kwargs):
        """Get field's value.
        """
        # Get value
        orig_val = self.get_field(field_name).get_val(**kwargs)

        # Pass value through hook method
        hooked_val = self._on_f_get(field_name, orig_val, **kwargs)
        if orig_val is not None and hooked_val is None:
            raise RuntimeWarning("_on_f_get() for field '{}.{}' returned None".format(self._model, field_name))

        return hooked_val

    def _on_f_get(self, field_name: str, value, **kwargs):
        """On get field's value hook.
        """
        return value

    def f_add(self, field_name: str, value, update_state: bool = True, **kwargs):
        """Add a value to the field.
        """
        value = self._on_f_add(field_name, value, **kwargs)
        self.get_field(field_name).add_val(value, **kwargs)

        if update_state:
            self._is_modified = True

        return self

    def _on_f_add(self, field_name: str, value, **kwargs):
        """On field's add value hook.
        """
        return value

    def f_sub(self, field_name: str, value, update_state: bool = True, **kwargs):
        """Subtract value from the field.
        """
        # Call hook
        value = self._on_f_sub(field_name, value, **kwargs)

        # Subtract value from the field
        self.get_field(field_name).sub_val(value, **kwargs)

        if update_state:
            self._is_modified = True

        return self

    def _on_f_sub(self, field_name: str, value, **kwargs) -> _Any:
        """On field's subtract value hook.
        """
        return value

    def f_inc(self, field_name: str, update_state: bool = True, **kwargs):
        """Increment value of the field.
        """
        self._on_f_inc(field_name, **kwargs)
        self.get_field(field_name).inc_val(**kwargs)

        if update_state:
            self._is_modified = True

        return self

    def _on_f_inc(self, field_name: str, **kwargs):
        """On field's increment value hook.
        """
        pass

    def f_dec(self, field_name: str, update_state: bool = True, **kwargs):
        """Decrement value of the field
        """
        self._on_f_dec(field_name, **kwargs)
        self.get_field(field_name).dec_val(**kwargs)

        if update_state:
            self._is_modified = True

        return self

    def _on_f_dec(self, field_name: str, **kwargs):
        """On field's decrement value hook.
        """
        pass

    def f_rst(self, field_name: str, update_state: bool = True, **kwargs):
        """Clear field.
        """
        self._on_f_rst(field_name, **kwargs)
        self.get_field(field_name).rst_val()

        if update_state:
            self._is_modified = True

        return self

    def _on_f_rst(self, field_name: str, **kwargs):
        """On field's clear value hook.
        """
        pass

    def f_is_empty(self, field_name: str) -> bool:
        """Checks if the field is empty.
        """
        return self.get_field(field_name).is_empty

    def append_child(self, child):
        """Append child to the entity

        :type child: Entity
        """
        if child.is_new:
            raise RuntimeError('Entity should be saved before it can be a child')

        if child == self:
            raise RuntimeError('Entity cannot be child of itself')

        self._pending_children.append(child.f_set('_parent', self).f_set('_depth', self.depth + 1))

        return self

    def remove_child(self, child):
        """Remove child from the entity.

        :type child: Entity
        """
        if child.is_new:
            raise RuntimeError('Entity should be saved before it can be a child')

        self._pending_children.append(child.f_set('_parent', None).f_set('_depth', 0))

        return self

    def is_child_of(self, parent):
        """Check if the entity is a child of a parent

        :type parent: Entity
        """
        return not self.is_new and self.parent == parent

    def is_parent_of(self, child):
        """Check if the entity is a parent of a child

        :type child: Entity
        """
        return not self.is_new and child.parent == self

    def is_descendant_of(self, ancestor):
        """Check if the entity is a descendant of an ancestor

        :type ancestor: Entity
        """
        if ancestor.is_new:
            return False

        par = self.parent
        while par:
            if par == ancestor:
                return True

            par = par.parent

        return False

    def is_ancestor_of(self, descendant):
        """Check if the entity is an ancestor of a descendant

        :type descendant: Entity
        """
        return descendant.is_descendant_of(self)

    def save(self, **kwargs):
        """Save the entity.
        """
        # Don't save entity if it wasn't changed
        if not (self._is_modified or kwargs.get('force')):
            return self

        # Shortcut
        if kwargs.get('fast'):
            kwargs['update_timestamp'] = False
            kwargs['pre_hooks'] = False
            kwargs['after_hooks'] = False

        # Update timestamp
        if kwargs.get('update_timestamp', True):
            self.f_set('_modified', _datetime.now())

        if self._is_new:
            # Create object's ID
            oid = _ObjectId()
            self.f_set('_id', oid)
            self.f_set('_ref', '{}:{}'.format(self.model, oid))

        # Pre-save hook
        if kwargs.get('pre_hooks', True):
            self._pre_save()
            _events.fire('odm@entity.pre_save', entity=self)
            _events.fire('odm@entity.pre_save.{}'.format(self._model), entity=self)

        # Save into storage
        _queue.put('entity_save', {
            'is_new': self._is_new,
            'collection_name': self._collection_name,
            'fields_data': self.as_storable(),
        }).execute(True)

        # Saved entity cannot be 'new'
        if self._is_new:
            first_save = True
            self._is_new = False
        else:
            first_save = False

        # After-save hook
        if kwargs.get('after_hooks', True):
            self._after_save(first_save, **kwargs)
            _events.fire('odm@entity.save', entity=self, first_save=first_save)
            _events.fire('odm@entity.save.{}'.format(self._model), entity=self, first_save=first_save)

        # Saved entity is not 'modified'
        self._is_modified = False

        # Save children with updated '_parent' field
        for child in self._pending_children:
            child.save(update_timestamp=False)

        # Clear finder cache
        from . import _api
        _api.clear_cache(self._model)

        return self

    def _pre_save(self, **kwargs):
        """Pre save hook.
        """
        pass

    def _after_save(self, first_save: bool = False, **kwargs):
        """After save hook.
        """
        pass

    def delete(self, **kwargs):
        """Delete the entity
        """
        from . import _api

        if self._is_new:
            raise _errors.ForbidDeletion('Non stored entities cannot be deleted')

        self._check_is_not_deleted()

        # Search for entities that refers to this entity
        if not kwargs.get('force'):
            for model in _api.get_registered_models():
                for field in _api.dispense(model).fields.values():
                    f = _api.find(model)
                    if isinstance(field, _field.Ref) and field.model == self.model:
                        f.eq(field.name, self)
                    elif isinstance(field, _field.RefsList) and field.model == self.model:
                        f.inc(field.name, self)
                    else:
                        continue

                    e = f.first()
                    if e:
                        raise _errors.ForbidDeletion("{}.{} refers to the {}".format(e, field.name, self))

        # Flag that deletion is in progress
        self._is_being_deleted = True

        # Pre delete events and hook
        _events.fire('odm@entity.pre_delete', entity=self)
        _events.fire('odm@entity.pre_delete.{}'.format(self._model), entity=self)
        self._pre_delete(**kwargs)

        # Notify each field about entity deletion
        for f_name, field in self._fields.items():
            field.entity_delete(self)

        # Clear parent reference from orphaned children
        for child in self.children:
            child.f_set('_parent', None).save()

        # Actual deletion from the database and cache
        _queue.put('entity_delete', {
            'model': self._model,
            'collection_name': self._collection_name,
            '_id': self.id,
        }).execute(True)

        # Clear finder cache
        _api.clear_cache(self._model)

        # After delete events and hook. It is important to call them BEFORE entity entity data will be
        # completely removed from the cache
        self._after_delete(**kwargs)
        _events.fire('odm@entity.delete', entity=self)
        _events.fire('odm@entity.delete.{}'.format(self._model), entity=self)

        self._is_deleted = True
        self._is_being_deleted = False

        return self

    def _pre_delete(self, **kwargs):
        """Pre delete hook.
        """
        pass

    def _after_delete(self, **kwargs):
        """After delete hook.
        """
        pass

    def as_storable(self, check_required_fields: bool = True) -> dict:
        """Get storable representation of the entity
        """
        r = {}

        for f_name, f in self.fields.items():
            # Check if the field is storable
            if not f.storable:
                continue

            # Required fields should be filled
            if check_required_fields and f.required and f.is_empty:
                raise _error.RequiredFieldEmpty(self._model, f_name)

            r[f_name] = f.get_storable_val()

        return r

    def as_jsonable(self, **kwargs) -> _Dict:
        """Get JSONable dictionary representation of the entity
        """
        return {
            '_ref': str(self.ref),
        }

    @classmethod
    def http_api_finder(cls, finder, **kwargs):
        pass

    def http_api_get(self, **kwargs):
        return self.as_jsonable(**kwargs)

    @classmethod
    def package_name(cls) -> str:
        """Get package name of the object class
        """
        return '.'.join(cls.__module__.split('.')[:-1])

    @classmethod
    def lang_package_name(cls) -> str:
        """Get lang's package name to use in t() and t_plural() methods
        """
        return cls.package_name()

    @classmethod
    def resolve_lang_msg_id(cls, partial_msg_id: str) -> str:
        # Searching for translation up in hierarchy
        for super_cls in cls.__mro__:
            if hasattr(super_cls, 'package_name') and callable(super_cls.package_name):
                full_msg_id = super_cls.package_name() + '@' + partial_msg_id
                if _lang.is_translation_defined(full_msg_id):
                    return full_msg_id

        return cls.lang_package_name() + '@' + partial_msg_id

    @classmethod
    def t(cls, partial_msg_id: str, args: dict = None) -> str:
        """Translate a string in model context
        """
        return _lang.t(cls.resolve_lang_msg_id(partial_msg_id), args)

    @classmethod
    def t_plural(cls, partial_msg_id: str, num: int = 2) -> str:
        """Translate a string into plural form.
        """
        return _lang.t_plural(cls.resolve_lang_msg_id(partial_msg_id), num)

    def __str__(self):
        """__str__ overloading
        """
        return self.ref

    def __eq__(self, other) -> bool:
        """__eq__ overloading
        """

        return hasattr(other, 'ref') and self.ref == other.ref
