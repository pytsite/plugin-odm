"""PytSite ODM Plugin ODM Console Commands
"""
from pytsite import console as _console, maintenance as _maintenance
from . import _api

__author__ = 'Oleksandr Shepetko'
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

        _api.reindex()

        if not no_maint:
            _maintenance.disable()
