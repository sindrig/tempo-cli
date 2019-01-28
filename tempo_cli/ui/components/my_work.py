import datetime
import time
import logging
import curses

from tempo.config import config
from tempo.api import tempo, jira
from tempo_cli.ui.base import Component
from tempo_cli.ui.utils import delta_to_human, sec_to_human, date_to_human
from tempo_cli.ui.components.worklog_form import WorklogForm

logger = logging.getLogger(__name__)


class MyWork(Component):

    def __init__(self, date=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not date:
            date = datetime.date.today()
        self.selected_worklog = None
        self.date = date
        self.get_data()
        self.bind_key('c', self.create_worklog, 'Log work')
        self.bind_key('u', self.key_select, 'Update worklog')

    def get_data(self):
        while self.get_http_request_count():
            time.sleep(.1)
        self.user = jira.myself(cache=True)
        self.get_worklogs()
        self.get_schedules()

    def create_worklog(self, key):
        return WorklogForm, {
            'date': self.date,
            'create_callback': self.worklog_created,
        }

    def daterange(self):
        from_date = self.date
        while from_date.weekday() != int(config.tempo.first_day_of_week):
            from_date -= datetime.timedelta(1)
        to_date = from_date + datetime.timedelta(6)
        return from_date, to_date

    def select_first_worklog(self):
        if self.worklogs[self.date]:
            self.selected_worklog = self.worklogs[self.date][0]
            logger.info(f'Selected worklog {self.selected_worklog.id}')
        else:
            self.selected_worklog = None

    def receive_worklogs(self, worklogs):
        for worklog in sorted(worklogs, key=lambda x: x.started):
            self.worklogs[worklog.started.date()].append(worklog)

        self.select_first_worklog()
        self.refresh()

    def get_worklogs(self):
        self.worklogs = {}
        from_date, to_date = self.daterange()
        walker = from_date

        while walker <= to_date:
            self.worklogs[walker] = []
            walker += datetime.timedelta(1)

        tempo.worklogs(
            account_id=self.user.account_id,
            from_date=from_date,
            to_date=to_date,
            callback=self.receive_worklogs
        )

    def receive_schedules(self, user_schedules):
        logger.info('schedules: %s', user_schedules)
        for schedule in user_schedules:
            self.schedules[schedule.date] = schedule
        logger.info('selfsched: %s', self.schedules.keys())
        self.refresh()

    def get_schedules(self):
        self.schedules = {}
        from_date, to_date = self.daterange()
        tempo.user_schedules(
            account_id=self.user.account_id,
            from_date=from_date,
            to_date=to_date,
            callback=self.receive_schedules
        )

    def short_worklog_display(self, worklog):
        return (
            f'{worklog.issue.key} - {delta_to_human(worklog.time_spent)}'
        )

    def display(self):
        y, x = self.get_dimensions()
        column_width = int(x / 7)
        self.addstr(1, 1, f'Hi {self.user.display_name}!')
        for col, (date, worklogs) in enumerate(self.worklogs.items()):
            colstart = col * column_width + 1
            if date == self.date:
                mode = curses.A_REVERSE
            else:
                mode = curses.A_NORMAL
            self.addstr(
                2, colstart, date_to_human(date), mode
            )
            if date in self.schedules:
                schedule = self.schedules[date]
                if date in self.worklogs:
                    worked_seconds = sum(
                        worklog.time_spent.total_seconds()
                        for worklog in self.worklogs[date]
                    )
                else:
                    worked_seconds = 0
                if schedule.required.total_seconds() > worked_seconds:
                    mode = curses.color_pair(curses.COLOR_RED)
                else:
                    mode = curses.color_pair(curses.COLOR_GREEN)
                self.addstr(
                    3,
                    colstart,
                    (
                        f'{sec_to_human(worked_seconds)}/'
                        f'{delta_to_human(schedule.required)}'
                    ),
                    mode,
                )
            self.addstr(
                4, colstart, '-' * column_width, curses.A_NORMAL
            )
            for i, worklog in enumerate(worklogs):
                if worklog == self.selected_worklog:
                    mode = curses.A_REVERSE
                else:
                    mode = curses.A_NORMAL
                self.addstr(
                    i * 2 + 5,
                    colstart,
                    self.short_worklog_display(worklog),
                    mode,
                )
                self.addstr(
                    i * 2 + 6,
                    colstart,
                    worklog.description[:column_width],
                    mode,
                )

    def key_up(self, key):
        worklogs = self.worklogs[self.date]
        if self.selected_worklog in worklogs:
            idx = worklogs.index(self.selected_worklog)
            if idx > 0:
                worklog = worklogs[idx - 1]
                self.selected_worklog = worklog
                logger.info(f'Selected worklog {self.selected_worklog.id}')

    def key_down(self, key):
        worklogs = self.worklogs[self.date]
        if self.selected_worklog in worklogs:
            idx = worklogs.index(self.selected_worklog)
            if idx + 1 < len(worklogs):
                worklog = worklogs[idx + 1]
                self.selected_worklog = worklog
                logger.info(f'Selected worklog {self.selected_worklog.id}')

    def key_left(self, key):
        self.date -= datetime.timedelta(1)
        logger.info(f'Selected date {self.date}')
        if self.date in self.worklogs:
            self.select_first_worklog()
        else:
            self.get_data()

    def key_right(self, key):
        self.date += datetime.timedelta(1)
        logger.info(f'Selected date {self.date}')
        if self.date in self.worklogs:
            self.select_first_worklog()
        else:
            self.get_data()

    def key_select(self, key):
        if self.selected_worklog:
            return WorklogForm, {
                'worklog': self.selected_worklog,
                'create_callback': self.worklog_created,
            }

    def worklog_created(self, worklog):
        for date in self.worklogs:
            for i in range(len(self.worklogs[date])):
                if self.worklogs[date][i].id == worklog.id:
                    del self.worklogs[date][i]
                    break
        if worklog.started.date() in self.worklogs:
            self.worklogs[worklog.started.date()].append(worklog)
            self.selected_worklog = worklog
