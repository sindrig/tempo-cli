import datetime
import logging

from tempo_cli.ui.base import Component

logger = logging.getLogger(__name__)


class WorklogForm(Component):

    def __init__(self, date=None, worklog=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not date:
            date = datetime.date.today()
        self.date = date
        self.worklog = worklog

    def display(self):
        pass
