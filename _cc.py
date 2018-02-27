"""PytSite ODM Plugin ODM Console Commands
"""
from pytsite import console as _console, lang as _lang, logger as _logger, maintenance as _maintenance
from . import _api

__author__ = 'Alexander Shepetko'
__email__ = 'a@shepetko.com'
__license__ = 'MIT'


class Reindex(_console.Command):
    """Cleanup All Command.
    """

    def __init__(self):
        super().__init__()

        self.define_option(_console.option.Bool('no-maint'))

    @property
    def name(self) -> str:
        """Get name of the command.
        """
        return 'odm:reindex'

    @property
    def description(self) -> str:
        """Get description of the command.
        """
        return 'odm@console_command_description_reindex'

    def exec(self):
        """Execute the command.
        """
        no_maint = self.opt('no-maint')

        if not no_maint:
            _maintenance.enable()

        for model in _api.get_registered_models():
            msg = _lang.t('odm@reindex_model', {'model': model})
            _console.print_info(msg)
            _logger.info(msg)
            _api.dispense(model).reindex()

        if not no_maint:
            _maintenance.disable()
