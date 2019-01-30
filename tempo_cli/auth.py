import logging
import uuid
import sys
from functools import wraps
from urllib.parse import urljoin
import webbrowser

from oauth2_client.credentials_manager import (
    CredentialManager, ServiceInformation, OAuthError
)

from tempo.api import jira_global, tempo
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


service_information = ServiceInformation(
    urljoin(
        config.jira.auth_url,
        'authorize'
    ),
    urljoin(
        config.jira.auth_url,
        '/oauth/token',
    ),
    config.jira.client_id,
    config.jira.client_secret,
    [
        'read:jira-user',
        'read:jira-work',
        'write:jira-work',
        # Need this for refresh token
        'offline_access'
    ],
)
manager = CredentialManager(
    service_information,
)


def refresh_tokens():
    if config.jira.refresh_token:
        try:
            manager.init_with_token(config.jira.refresh_token)
            validate_access_token(manager._access_token)
            config.jira.access_token = manager._access_token
            return True
        except (OAuthError, TokenNotValid):
            pass
    return False


class TokenNotValid(Exception):
    pass


def validate_access_token(access_token):
    try:
        resource = jira_global.accessible_resources(
            access_token=access_token
        )[0]
        logger.info('Success. Jira name: %s', resource.name)
        config.jira.site_id = resource.id
    except jira_global.ApiError:
        raise TokenNotValid('Could not validate token with JIRA')
    try:
        # We want to get 404, everything else should fail
        tempo.account('PROBABLY_NOT_VALID_KEY')
    except tempo.ApiError as e:
        if e.original.response.status_code != 404:
            raise TokenNotValid('Could not validate token with Tempo')


def authenticate():
    if config.jira.access_token:
        try:
            validate_access_token(config.jira.access_token)
            return
        except TokenNotValid:
            logger.info(
                f'Could not validate access using {config.jira.access_token}'
            )
    if config.jira.refresh_token:
        if refresh_tokens():
            return
        elif input(BAD_ACCESS_TOKEN).lower()[0] != 'y':
            sys.exit(1)

    redirect_uri = 'http://localhost:8158/oauth/code'

    url = manager.init_authorize_code_process(
        redirect_uri,
        str(uuid.uuid4())
    )
    url = f'{url}&audience=api.atlassian.com&prompt=consent'
    logger.info('Opening this url in your browser: %s', url)
    webbrowser.open(url)
    print('Please finish the authorization process in your browser.')

    code = manager.wait_and_terminate_authorize_code_process()
    logger.debug('Code got = %s', code)
    manager.init_with_authorize_code(redirect_uri, code)
    logger.debug('Access got = %s', manager._access_token)
    config.jira.access_token = manager._access_token
    config.jira.refresh_token = manager.refresh_token
    validate_access_token(config.jira.access_token)
