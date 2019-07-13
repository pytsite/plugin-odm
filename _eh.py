"""PytSite ODM Plugin Events Handlers
"""

from pytsite import console, lang
from . import _api


def db_restore():
    for model in _api.get_registered_models():
        _api.clear_cache(model)
        console.print_info(lang.t('odm@cache_cleared', {'model': model}))
