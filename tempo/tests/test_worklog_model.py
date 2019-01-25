import datetime

from tempo.api.models import Worklog


def test_from_dict():
    data = {
        'self': 'https://api.tempo.io/2/worklogs/12600',
        'tempoWorklogId': 126,
        'jiraWorklogId': 10100,
        'issue': {
            'self': 'https://instance.atlassian.net/rest/api/2/issue/DUM-1',
            'key': 'DUM-1'
        },
        'timeSpentSeconds': 3600,
        'billableSeconds': 5200,
        'startDate': '2017-02-06',
        'startTime': '20:06:00',
        'description': (
            'Investigating a problem with our external database system'
        ),
        'createdAt': '2017-02-06T16:41:41Z',
        'updatedAt': '2017-02-06T16:41:42Z',
        'author': {
            'self': (
                'https://instance.atlassian.net/rest/api/2/user?username=johnb'
            ),
            'accountId': '41321:32521-531-53151j51-51341',
            'displayName': 'John Brown'
        },
        'attributes': {
            'self': (
                'https://api.tempo.io/2/worklogs/126/work-attribute-values'
            ),
            'values': [
                {
                    'key': '_DELIVERED_',
                    'value': True
                },
                {
                    'key': '_EXTERNALREF_',
                    'value': 'EXT-44556'
                },
                {
                    'key': '_COLOR_',
                    'value': 'red'
                }
            ]
        }
    }
    w = Worklog(data)
    assert w.self_link == data['self']
    assert w.id == data['tempoWorklogId']
    assert w.jira_worklog_id == data['jiraWorklogId']
    assert w.author.account_id == data['author']['accountId']
    assert w.billable.total_seconds() == data['billableSeconds']
    assert w.description == data['description']
    assert w.created_at == datetime.datetime(2017, 2, 6, 16, 41, 41)
    assert w.updated_at == datetime.datetime(2017, 2, 6, 16, 41, 42)
    assert w.time_spent.total_seconds() == data['timeSpentSeconds']
    assert w.started == datetime.datetime(2017, 2, 6, 20, 6)
