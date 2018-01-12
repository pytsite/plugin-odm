"""PytSite ODM Plugin
"""
__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from pytsite import plugman as _plugman, semver as _semver

if _plugman.is_installed(__name__):
    from pytsite import cache as _cache

    # This cache pool MUST be created before any imports
    if not _cache.has_pool('odm.entities'):
        _cache.create_pool('odm.entities')

    # Public API
    from . import _field as field, _validation as validation, _error as error, _geo as geo, _model as model
    from ._model import I_ASC, I_DESC, I_TEXT, I_GEO2D, I_GEOSPHERE
    from ._finder import Finder, Result as FinderResult
    from ._api import register_model, unregister_model, is_model_registered, get_model_class, get_registered_models, \
        resolve_ref, resolve_refs, get_by_ref, dispense, find, aggregate, clear_finder_cache, resolve_manual_ref


def plugin_load():
    """Plugman hook
    """
    from pytsite import console, lang, events
    from . import _console_command, _eh

    # Resources
    lang.register_package(__name__)

    # Console commands
    console.register_command(_console_command.Reindex())

    # Event listeners
    events.listen('pytsite.mongodb@restore', _eh.db_restore)


def plugin_update(v_from: _semver.Version):
    if v_from < _semver.Version('1.4'):
        from pytsite import mongodb, console

        for collection_name in mongodb.get_collection_names():
            collection = mongodb.get_collection(collection_name)
            for doc in collection.find():
                if '_ref' in doc:
                    continue

                doc['_ref'] = '{}:{}'.format(doc['_model'], doc['_id'])
                collection.replace_one({'_id': doc['_id']}, doc)
                console.print_info('Document {} updated'.format(doc['_ref']))
