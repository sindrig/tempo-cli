
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

lifecycle_handlers = []


def register_lifecycle_handler(handler):
    if not hasattr(handler, 'on_request'):
        raise TypeError(f'{handler}: Missing on_request handler')
    if not hasattr(handler, 'on_request_done'):
        raise TypeError(f'{handler}: Missing on_request_done handler')
    lifecycle_handlers.append(handler)


class Api:
    class ApiError(Exception):
        def __init__(self, original, error):
            self.original = original
            self.error = error
            super().__init__(str(original))

    REQUEST_COUNT = 0

    token_type = 'Bearer'
    token = None

    def get_headers(self, token: str = None):
        return {
            'Authorization': (
                f'{self.token_type} {token or config.jira.access_token}'
            ),
        }

    def request(
        self,
        method: str,
        path: str,
        params: dict = None,
        json: dict = None,
        access_token: str = None
    ):
        Api.REQUEST_COUNT += 1
        if params is None:
            params = {}
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
        for handler in lifecycle_handlers:
            handler.on_request(
                method=method,
                path=path,
                params=params,
                json=json,
                request_count=Api.REQUEST_COUNT,
            )
        r = getattr(requests, method)(
            url,
            headers=self.get_headers(token=access_token),
            params=formatted_params,
            json=json,
        )
        try:
            r.raise_for_status()
        except Exception as e:
            logger.exception('Exception calling %s', r.url)
            raise self.ApiError(e, r.text)
        finally:
            Api.REQUEST_COUNT -= 1
            for handler in lifecycle_handlers:
                handler.on_request_done(
                    method=method,
                    path=path,
                    params=params,
                    json=json,
                    request_count=Api.REQUEST_COUNT,
                )
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

    @property
    def base_url(self):
        return urljoin(
            config.jira.api_url,
            f'/ex/jira/{config.jira.site_id}'
        )

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
    def accessible_resources(
        self,
        access_token=None
    ) -> models.AccessibleResources:
        return self.get(
            '/oauth/token/accessible-resources',
            access_token=access_token,
        )


class Tempo(Api):
    base_url = config.tempo.api_url
    token_type = 'Jira-Bearer'

    def get_headers(self, **kwargs):
        return {
            'Jira-Cloud-Id': config.jira.site_id,
            **super().get_headers(**kwargs)
        }

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
            url = f'/core/3/worklogs/user/{account_id}'
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


tempo = Tempo()
jira = Jira()
jira_global = JiraGlobal()
