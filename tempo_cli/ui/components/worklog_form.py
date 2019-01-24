import datetime
import logging
import curses

from tempo_cli.ui.base import Component
from tempo_cli.ui.utils import sec_to_human, datetime_to_human

from curses import textpad

logger = logging.getLogger(__name__)


class WorklogForm(Component):

    def __init__(self, date=None, worklog=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not date:
            date = datetime.date.today()
        self.worklog = worklog

        self.selected_line = 0

        if self.worklog:
            self.data = {
                'description': self.worklog.description,
                'issueKey': self.worklog.issue.key,
                'timeSpentSeconds': self.worklog.time_spent.total_seconds(),
                'billableSeconds': self.worklog.billable.total_seconds(),
                'started': self.worklog.started,
                'author': self.worklog.author.account_id,
            }
        else:
            self.data = {
                'description': '',
                'issueKey': None,
                'timeSpentSeconds': 0,
                'billableSeconds': 0,
                'started': datetime.datetime.now(),
                'author': self.jira.myself(cache=True).account_id,
            }
        self.form = [
            ('Description', (str, 'description'), TextEdit,),
            ('Issue', (str, 'issueKey'), TextEdit,),  # TODO
            ('Time spent', (sec_to_human, 'timeSpentSeconds'), TimeEdit),
            ('Billable', (sec_to_human, 'billableSeconds'), TimeEdit),
            ('Started', (datetime_to_human, 'started'), DateTimeEdit),
            ('User', (str, 'author'), TextEdit),  # TODO
        ]

    def add_field(self, y, x, text):
        if self.selected_line == y:
            mode = curses.A_REVERSE
        else:
            mode = curses.A_NORMAL
        self.addstr(y, x, text, mode)

    def display(self):
        for i, (label, (fn, key), editor) in enumerate(self.form):
            if i == self.selected_line:
                mode = curses.A_REVERSE
            else:
                mode = curses.A_NORMAL
            self.addstr(i + 1, 1, f'{label}: {fn(self.data[key])}', mode)

    def update(self, key):
        def _inner(value):
            self.data[key] = value
        return _inner

    def key_up(self):
        if self.selected_line > 0:
            self.selected_line -= 1

    def key_down(self):
        if self.selected_line < len(self.form) - 1:
            self.selected_line += 1

    def key_select(self):
        label, (fn, key), editor = self.form[self.selected_line]
        return editor, {'data': self.data[key], 'update': self.update(key)}


class Editor(Component):
    def __init__(self, data, update, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = data
        self.update = update


class TextEdit(Editor):
    def display(self):
        win = curses.newwin(5, 60, 5, 10)
        tb = textpad.Textbox(win)
        win.addstr(0, 0, self.data)
        text = tb.edit()
        self.close()
        self.update(text)


class TimeEdit(Editor):
    pass


class DateTimeEdit(Editor):
    pass