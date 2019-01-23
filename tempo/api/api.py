
import datetime
import requests
import logging
from typing import Union
from urllib.parse import urljoin

from tempo.config import config
from tempo.api import models
from tempo.api.models import DATE_FORMAT
from tempo.api.decorators import returns, api_request

logger = logging.getLogger(__name__)

DateType = Union[datetime.date, datetime.date]


class Api:
    class ApiError(Exception):
        def __init__(self, original):
            self.original = original
            super().__init__(str(original))

    headers = {}

    def __init__(self, token):
        self.headers = {
            'Authorization': f'Bearer {token}'
        }

    def request(
        self,
        method,
        path,
        params={},
        prefix=None
    ):
        formatted_params = {
            key: self.format_param(value)
            for key, value in params.items()
            if value
        }
        url = urljoin(self.base_url, path)
        logger.info(
            f'Making {method} request to {url} with params {formatted_params}'
        )
        r = getattr(requests, method)(
            url,
            headers=self.headers,
            params=formatted_params,
        )
        try:
            r.raise_for_status()
        except Exception as e:
            logger.exception('Exception calling %s', r.url)
            raise self.ApiError(e)
        return r.json()

    def get(self, *args, **kwargs):
        return self.request('get', *args, **kwargs)

    def format_param(self, param):
        if isinstance(param, (datetime.datetime, datetime.date)):
            return param.strftime(DATE_FORMAT)
        return param


class Tempo(Api):
    base_url = config.tempo.api_url

    @classmethod
    def matching_instances(cls, part: str) -> str:
        r = requests.get(
            urljoin(config.tempo.url, 'rest/jira/client/search/'),
            params={'sitename': part}
        )
        if not r.ok:
            logger.warning(
                f'Received {r.status_code} for matching instances. '
                f'Url: {r.url}'
            )
            return None
        return r.json()['path']

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


class Jira(Api):
    base_url = config.jira.url

    def __init__(self, token, expires, tempo):
        super().__init__(token)
        self.tempo = tempo
        self.expires = expires

    @classmethod
    def auth_by_tempo(cls, tempo: Tempo):
        token_request = tempo.get(
            '/jira/v1/get-jira-oauth-token/',
            prefix=None
        )
        return cls(
            token_request['token'],
            expires=token_request['expiresAt'],
            tempo=tempo
        )

    @api_request(cache=True)
    def myself(self) -> dict:
        return self.get('/rest/api/3/myself')
