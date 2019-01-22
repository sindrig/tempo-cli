import os
import logging
import configparser

from appdirs import user_config_dir

logger = logging.getLogger(__name__)

CONFIG_FILE_NAME = os.path.join(
    user_config_dir(appname='tempo-cli'), 'config.ini'
)


def get_defaults():
    return {
        'tempo': {
            'api_url': 'https://api.tempo.io',
            'url': 'https://app.tempo.io',
            'access_token': None,
            'refresh_token': None,
            'client_id': None,
            'client_secret': None,
        },
        'jira': {
            'url': None
        }
    }


class Section:
    def __init__(self, name, update):
        super().__setattr__('name', name)
        super().__setattr__('update', update)
        super().__setattr__('_ready', False)

    def __setattr__(self, name, value):
        if self._ready and not hasattr(self, name):
            msg = f'Unknown key {name} in section {self.name}'
            logger.error(msg)
            raise ValueError(msg)
        super().__setattr__(name, value)
        if self._ready:
            self.update()

    def ready(self):
        super().__setattr__('_ready', True)


class Config:
    def __init__(self, disk_cfg):
        defaults = get_defaults()
        sections = disk_cfg.sections()
        self.sections = {}
        for section_name, default_values in defaults.items():
            section = Section(name=section_name, update=self.update)
            setattr(self, section_name, section)
            for key, value in default_values.items():
                if section_name in sections and key in disk_cfg[section_name]:
                    setattr(section, key, disk_cfg[section_name][key])
                else:
                    setattr(section, key, value)
            section.ready()
            self.sections[section_name] = section
        self.disk_config = disk_cfg

    def update(self):
        os.makedirs(os.path.dirname(CONFIG_FILE_NAME), exist_ok=True)
        for section, values in get_defaults().items():
            if section not in self.disk_config.sections():
                self.disk_config.add_section(section)
            for key, value in values.items():
                self.disk_config.set(
                    section, key, getattr(self.sections[section], key)
                )
        with open(CONFIG_FILE_NAME, 'w') as f:
            self.disk_config.write(f)


def get_disk_config():
    parser = configparser.ConfigParser(allow_no_value=True)
    if os.path.exists(CONFIG_FILE_NAME):
        parser.read(CONFIG_FILE_NAME)
    return parser


config = Config(get_disk_config())
