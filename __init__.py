"""PytSite ODM Plugin
"""
__author__ = 'Oleksandr Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

# Locally needed imports
from semaver import Version as _Version
from pytsite import cache as _cache

# This cache pool MUST be created before any imports
_cache.create_pool('odm.entities')

# Public API
from . import _field as field, _validation as validation, _error as error, _model as model
from ._model import Entity, I_ASC, I_DESC, I_TEXT, I_GEO2D, I_GEOSPHERE
from ._finder import Finder, SingleModelFinder, MultiModelFinder, SingleModelResult, MultiModelResult
from ._api import register_model, unregister_model, is_model_registered, get_model_class, get_registered_models, \
    resolve_ref, resolve_refs, get_by_ref, dispense, find, mfind, aggregate, clear_cache, reindex, on_model_register, \
    on_model_setup_fields, on_model_setup_indexes, on_entity_pre_save, on_entity_save, on_entity_pre_delete, \
    on_entity_delete, on_cache_clear


def plugin_load():
    from pytsite import console, events
    from . import _cc, _eh

    # Console commands
    console.register_command(_cc.Reindex())

    # Event listeners
    events.listen('pytsite.mongodb@restore', _eh.db_restore)


def plugin_update(v_from: _Version):
    from pytsite import console

    if v_from < '1.4':
        from pytsite import mongodb

        for collection_name in mongodb.get_collection_names():
            collection = mongodb.get_collection(collection_name)
            for doc in collection.find():
                if '_ref' in doc:
                    continue

                doc['_ref'] = '{}:{}'.format(doc['_model'], doc['_id'])
                collection.replace_one({'_id': doc['_id']}, doc)
                console.print_info('Document {} updated'.format(doc['_ref']))

    if v_from < '1.6':
        console.run_command('odm:reindex')

    if v_from < '4.0':
        # Update all entities that have `Ref` and `RefsList` fields
        for m in get_registered_models():
            console.print_info("Processing model '{}'".format(m))
            fields_to_update = []
            for f in dispense(m).fields.values():
                if f.name != '_parent' and isinstance(f, (field.Ref, field.RefsList)):
                    fields_to_update.append(f.name)

            if fields_to_update:
                for e in find(m).get():
                    for f_name in fields_to_update:
                        e.f_set(f_name, e.f_get(f_name))

                    e.save(update_timestamp=False)
                    console.print_info('Entity {} updated, fields {}'.format(e, fields_to_update))

    if v_from < '6.0':
        console.run_command('odm:reindex')
