"""PytSite ODM Plugin Events Handlers
"""

from pytsite import console as _console, lang as _lang
from . import _api


def db_restore():
    for model in _api.get_registered_models():
        _api.clear_cache(model)
        _console.print_info(_lang.t('odm@cache_cleared', {'model': model}))
