from tempo_cli.auth import ensure_auth
from tempo.api import Tempo, Jira


@ensure_auth
def main(config):
    tempo = Tempo(config.tempo.access_token)
    jira = Jira.auth_by_tempo(tempo)
    print(jira.myself())
    # t = tempo.worklogs(account_id=myself['accountId'])
    for worklog in tempo.worklogs():
        print(worklog.issue.key, worklog.started, worklog.time_spent.seconds)
