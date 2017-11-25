"""PytSite ODM Plugin Events Handlers
"""

from pytsite import console as _console, lang as _lang
from . import _api


def db_restore():
    _console.print_info(_lang.t('odm@entities_cache_cleared'))

    for model in _api.get_registered_models():
        _api.clear_finder_cache(model)
        _console.print_info(_lang.t('odm@finder_cache_cleared', {'model': model}))
