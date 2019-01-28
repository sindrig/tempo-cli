import logging
from curses import wrapper

from tempo_cli.auth import ensure_auth
from tempo_cli.ui.container import TempoUI

logger = logging.getLogger(__name__)


@ensure_auth
def main(config):
    if config.jira.access_token:
        wrapper(TempoUI())
    print('Bye!')
