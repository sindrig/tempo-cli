
import datetime
import requests
import logging
from typing import Union
from urllib.parse import urljoin

from tempo.config import config
from tempo.api import models
from tempo.api.models import DATE_FORMAT, TIME_FORMAT
from tempo.api.decorators import returns, api_request

logger = logging.getLogger(__name__)

DateType = Union[datetime.date, datetime.date]


class Api:
    class ApiError(Exception):
        def __init__(self, original, error):
            self.original = original
            self.error = error
            super().__init__(str(original))

    token_type = 'Bearer'
    token = None

    def __init__(self, token):
        self.token = token

    def get_headers(self):
        return {
            'Authorization': f'{self.token_type} {self.token}',
        }

    def request(
        self,
        method,
        path,
        params={},
        json=None,
        prefix=None
    ):
        formatted_params = {
            key: self.format_param(value)
            for key, value in params.items()
            if value
        }
        url = '/'.join([
            self.base_url.rstrip('/'),
            path.lstrip('/'),
        ])
        logger.info(
            f'Making {method} request to {url} with params {formatted_params}'
        )
        r = getattr(requests, method)(
            url,
            headers=self.get_headers(),
            params=formatted_params,
            json=json,
        )
        try:
            r.raise_for_status()
        except Exception as e:
            logger.exception('Exception calling %s', r.url)
            raise self.ApiError(e, r.text)
        return r.json()

    def get(self, *args, **kwargs):
        return self.request('get', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.request('post', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.request('put', *args, **kwargs)

    def format_param(self, param):
        if isinstance(param, (datetime.datetime, datetime.date)):
            return param.strftime(DATE_FORMAT)
        return param


class Jira(Api):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = urljoin(
            config.jira.api_url,
            f'/ex/jira/{config.jira.site_id}'
        )

    # def __init__(self, token, expires, tempo):
    #     super().__init__(token)
    #     self.tempo = tempo
    #     self.expires = expires

    # @classmethod
    # def auth_by_tempo(cls, tempo: Tempo):
    #     token_request = tempo.get(
    #         '/jira/v1/get-jira-oauth-token/',
    #         prefix=None
    #     )
    #     return cls(
    #         token_request['token'],
    #         expires=token_request['expiresAt'],
    #         tempo=tempo
    #     )

    @api_request(cache=True)
    @returns(models.JiraUser)
    def myself(self) -> models.JiraUser:
        return self.get('/rest/api/3/myself')

    @api_request
    @returns(models.Issue)
    def issue(self, key):
        return self.get(f'/rest/api/3/issue/{key}')

    @api_request
    @returns(models.IssuePickerSections)
    def issue_picker(self, search):
        params = {
            'currentJQL': (
                'project in projectsWhereUserHasPermission("Work on issues")'
            ),
            'query': search,
            'showSubTaskParent': 'true',
            'showSubTasks': 'true',
        }
        return self.get('/rest/api/3/issue/picker', params=params)


class JiraGlobal(Api):
    base_url = config.jira.api_url

    @api_request(cache=True)
    @returns(models.AccessibleResources)
    def accessible_resources(self) -> models.AccessibleResources:
        return self.get('/oauth/token/accessible-resources')


class Tempo(Api):
    base_url = config.tempo.api_url
    token_type = 'Jira-Bearer'

    def get_headers(self):
        return {
            'Jira-Cloud-Id': config.jira.site_id,
            **super().get_headers()
        }

    # @classmethod
    # def matching_instances(cls, part: str) -> str:
    #     r = requests.get(
    #         urljoin(config.tempo.url, 'rest/jira/client/search/'),
    #         params={'sitename': part}
    #     )
    #     if not r.ok:
    #         logger.warning(
    #             f'Received {r.status_code} for matching instances. '
    #             f'Url: {r.url}'
    #         )
    #         return None
    #     return r.json()['path']

    @api_request
    @returns(models.Worklogs)
    def worklogs(
        self,
        account_id: str = None,
        from_date: DateType = None,
        to_date: DateType = None,
        updated_from: DateType = None,
        offset=0,
        limit=200
    ) -> models.Worklogs:
        if account_id:
            url = f'/core/3/worklogs/account/{account_id}'
        else:
            url = '/core/3/worklogs'
        return self.get(
            url,
            params={
                'from': from_date,
                'to': to_date,
                'updated_from': updated_from,
                'offset': offset,
                'limit': limit,
            }
        )

    @api_request(cache=True)
    @returns(models.UserSchedules)
    def user_schedules(
        self,
        account_id: str = None,
        from_date: DateType = None,
        to_date: DateType = None,
    ) -> models.UserSchedules:
        if account_id:
            url = f'/core/3/user-schedule/{account_id}'
        else:
            url = '/core/3/user-schedule'
        return self.get(
            url,
            params={
                'from': from_date,
                'to': to_date,
            }
        )

    @api_request
    @returns(models.Worklog)
    def update_worklog(
        self,
        worklog_id: int = None,
        description: str = '',
        issue_key: str = '',
        time_spent: int = 0,
        billable: int = 0,
        remaining_estimate: int = 0,
        started: datetime.datetime = None,
        author_account_id: str = None,
        attributes: list = None
    ):
        if attributes is None:
            attributes = []
        if author_account_id is None:
            jira = Jira.auth_by_tempo(self)
            author_account_id = jira.myself()['accountId']
        if started is None:
            started = datetime.datetime.now()
        data = {
            "issueKey": issue_key,
            "timeSpentSeconds": time_spent,
            "billableSeconds": billable,
            "startDate": started.strftime(DATE_FORMAT),
            "startTime": started.strftime(TIME_FORMAT),
            "description": description,
            "authorAccountId": author_account_id,
            "remainingEstimateSeconds": remaining_estimate,
            "attributes": attributes,
        }
        if worklog_id is not None:
            return self.put(
                f'/core/3/worklogs/{worklog_id}',
                json=data,
            )
        return self.post(f'/core/3/worklogs', json=data)

    create_worklog = update_worklog


# class Jira(Api):
#     base_url = config.jira.url

#     def __init__(self, token, expires, tempo):
#         super().__init__(token)
#         self.tempo = tempo
#         self.expires = expires

#     @classmethod
#     def auth_by_tempo(cls, tempo: Tempo):
#         token_request = tempo.get(
#             '/jira/v1/get-jira-oauth-token/',
#             prefix=None
#         )
#         return cls(
#             token_request['token'],
#             expires=token_request['expiresAt'],
#             tempo=tempo
#         )

#     @api_request(cache=True)
#     @returns(models.JiraUser)
#     def myself(self) -> models.JiraUser:
#         return self.get('/rest/api/3/myself')
