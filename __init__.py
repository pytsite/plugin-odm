"""PytSite ODM Plugin
"""
__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'

from pytsite import plugman as _plugman

if _plugman.is_installed(__name__):
    from pytsite import cache as _cache

    # This cache pool MUST be created before any imports
    _cache.create_pool('odm.entities')

    # Public API
    from . import _field as field, _validation as validation, _error as error, _geo as geo, _model as model
    from ._model import I_ASC, I_DESC, I_TEXT, I_GEO2D, I_GEOSPHERE
    from ._finder import Finder, Result as FinderResult
    from ._api import register_model, unregister_model, is_model_registered, get_model_class, get_registered_models, \
        resolve_ref, resolve_refs, get_by_ref, dispense, find, aggregate, clear_finder_cache


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
