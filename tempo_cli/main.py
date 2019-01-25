import logging
from curses import wrapper

from tempo_cli.auth import ensure_auth
from tempo.api import Tempo, Jira
from tempo_cli.ui.container import TempoUI

logger = logging.getLogger(__name__)


@ensure_auth
def main(config):
    try:
        tempo = Tempo(config.tempo.access_token)
        jira = Jira.auth_by_tempo(tempo)
        wrapper(TempoUI(tempo, jira))
    except Exception:
        logging.exception('Uncaught exception')
