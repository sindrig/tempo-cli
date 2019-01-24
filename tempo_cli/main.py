import logging
from curses import wrapper

from tempo_cli.auth import ensure_auth
from tempo.api import Tempo, Jira
from tempo_cli.ui.container import TempoUI

logger = logging.getLogger(__name__)


@ensure_auth
def main(config):
    if config.jira.access_token:
        jira = Jira(config.jira.access_token)
        print(jira.base_url)
        jira.myself()
        tempo = Tempo(config.jira.access_token)
        for w in tempo.worklogs():
            print(w)
        wrapper(TempoUI(tempo, jira))
    print('Bye!')
    # tempo = Tempo(config.tempo.access_token)
    # jira = Jira.auth_by_tempo(tempo)
    # with TempoUI(tempo, jira) as ui:
    #     ui.start()
