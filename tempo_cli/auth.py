import logging
import uuid
import sys
import datetime
from functools import wraps
from urllib.parse import urljoin
import webbrowser

from oauth2_client.credentials_manager import (
    CredentialManager, ServiceInformation, OAuthError
)

from tempo.api import Tempo
from tempo.config import config


logger = logging.getLogger(__name__)
HTTP_ADDRESS = '0.0.0.0'
HTTP_PORT = 8158
NEED_JIRA_URL = (
    'We need your JIRA url. You only need to type the part after "https://" '
    'and ".atlassian.net". So if your JIRA url is '
    '"https://tempo.atlassian.net", only type "tempo": '
)

BAD_ACCESS_TOKEN = (
    'Could not communicate with jira using your stored tokens. Do you want '
    'to authenticate again? (Yy/Nn): '
)


def ensure_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        authenticate()
        return f(*args, **kwargs, config=config)
    return wrapper


def validate_access_token(access_token):
    tempo = Tempo(access_token)
    try:
        tempo.worklogs(
            from_date=datetime.datetime.now(),
            to_date=datetime.datetime.now(),
            limit=1
        )
    except Tempo.ApiError:
        return False
    return True


def authenticate():
    while not config.jira.url:
        part = input(NEED_JIRA_URL)
        path = Tempo.matching_instances(part)
        if path:
            config.jira.url = path
    if config.tempo.access_token:
        if validate_access_token(config.tempo.access_token):
            return
        logger.info(
            f'Could not validate access using {config.tempo.access_token}'
        )
        # config.tempo.access_token = None
    if config.tempo.client_id and config.tempo.client_secret:
        service_information = ServiceInformation(
            urljoin(
                config.jira.url,
                '/plugins/servlet/ac/io.tempo.jira/oauth-authorize/'
            ),
            urljoin(
                config.tempo.api_url,
                '/oauth/token/',
            ),
            config.tempo.client_id,
            config.tempo.client_secret,
            [],
        )
        manager = CredentialManager(
            service_information,
        )
        if config.tempo.refresh_token:
            try:
                manager.init_with_token(config.tempo.refresh_token)

                if validate_access_token(manager._access_token):
                    config.tempo.access_token = manager._access_token
                    return
            except OAuthError:
                pass

            if input(BAD_ACCESS_TOKEN).lower()[0] != 'y':
                sys.exit(1)
        redirect_uri = 'http://localhost:8158/oauth/code'

        url = manager.init_authorize_code_process(
            redirect_uri,
            str(uuid.uuid4())
        )
        url = f'{url}&access_type=tenant_user'
        logger.info('Opening this url in your browser: %s', url)
        webbrowser.open(url)
        print('Please finish the authorization process in your browser.')

        code = manager.wait_and_terminate_authorize_code_process()
        logger.debug('Code got = %s', code)
        manager.init_with_authorize_code(redirect_uri, code)
        logger.debug('Access got = %s', manager._access_token)
        config.tempo.access_token = manager._access_token
        config.tempo.refresh_token = manager.refresh_token
    else:
        webbrowser.open(
            urljoin(
                config.jira.url,
                '/plugins/servlet/ac/io.tempo.jira/tempo-configuration/'
            )
        )
        access_token = input(
            'I opened a new browser window where you can get an access token. '
            'Paste your access token here:'
        )
        if validate_access_token(access_token):
            config.tempo.access_token = access_token
        else:
            print('Could not communicate with tempo. Check the logs.')
            sys.exit(1)
