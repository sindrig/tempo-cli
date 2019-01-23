from curses import wrapper

from tempo_cli.auth import ensure_auth
from tempo.api import Tempo, Jira
from tempo_cli.ui.container import TempoUI


@ensure_auth
def main(config):
    tempo = Tempo(config.tempo.access_token)
    jira = Jira.auth_by_tempo(tempo)
    wrapper(TempoUI(tempo, jira))
    # with TempoUI(tempo, jira) as ui:
    #     ui.start()
