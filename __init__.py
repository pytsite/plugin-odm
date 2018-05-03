"""PytSite ODM Plugin
"""
__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from pytsite import semver as _semver, cache as _cache

# This cache pool MUST be created before any imports
_cache.create_pool('odm.entities')

# Public API
from . import _field as field, _validation as validation, _error as error, _model as model
from ._model import Entity, I_ASC, I_DESC, I_TEXT, I_GEO2D, I_GEOSPHERE
from ._finder import Finder, Result
from ._api import register_model, unregister_model, is_model_registered, get_model_class, get_registered_models, \
    resolve_ref, resolve_refs, get_by_ref, dispense, find, aggregate, clear_cache, resolve_manual_ref, reindex, \
    on_model_register, on_model_setup_fields, on_model_setup_indexes, on_entity_pre_save, on_entity_save, \
    on_entity_pre_delete, on_entity_delete, on_cache_clear


def plugin_load():
    from pytsite import console, lang, events
    from . import _cc, _eh

    # Resources
    lang.register_package(__name__)

    # Console commands
    console.register_command(_cc.Reindex())

    # Event listeners
    events.listen('pytsite.mongodb@restore', _eh.db_restore)


def plugin_update(v_from: _semver.Version):
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

    elif v_from < '1.6':
        console.run_command('odm:reindex')
