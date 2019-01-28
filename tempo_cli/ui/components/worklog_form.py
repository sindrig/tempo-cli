import datetime
import os
import tempfile
import subprocess
import logging
import curses

from tempo.api import tempo, jira
from tempo_cli.ui.base import Component
from tempo_cli.ui.utils import (
    sec_to_human, datetime_to_human, human_to_seconds, human_to_datetime,
)

logger = logging.getLogger(__name__)


class WorklogForm(Component):

    def __init__(
        self, create_callback, date=None, worklog=None, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.create_callback = create_callback
        if not date:
            date = datetime.date.today()
        self.worklog = worklog
        self.error = ''

        self.selected_line = 0

        if self.worklog:
            self.data = {
                'description': self.worklog.description,
                'issue_key': self.worklog.issue.key,
                'time_spent': self.worklog.time_spent.total_seconds(),
                'billable': self.worklog.billable.total_seconds(),
                # TODO edit
                'remaining_estimate': 0,
                'started': self.worklog.started,
                'author_account_id': self.worklog.author.account_id,
                'worklog_id': self.worklog.id,
            }
            self.bind_key('^X', self.update_worklog, 'Update worklog')
        else:
            self.data = {
                'description': '',
                'issue_key': None,
                'time_spent': 0,
                'billable': 0,
                'remaining_estimate': 0,
                'started': datetime.datetime.combine(
                    date,
                    datetime.time.min,
                ),
                'author_account_id': jira.myself(cache=True).account_id,
            }
            self.bind_key('^X', self.update_worklog, 'Create worklog')
        self.form = [
            ('Issue', (lambda x: x, 'issue_key'), IssueEditor(),),
            ('Description', (str, 'description'), Editor(),),
            ('Time spent', (sec_to_human, 'time_spent'), TimeEditor()),
            ('Billable', (sec_to_human, 'billable'), TimeEditor()),
            ('Started', (datetime_to_human, 'started'), DateEditor()),
            (
                'Remaining estimate',
                (sec_to_human, 'remaining_estimate'),
                TimeEditor()
            ),
            None,
            ('User', (str, 'author_account_id'), Editor()),  # TODO
        ]
        self.bind_key('i', self.key_select, 'Edit field')
        self.bind_key(['-', curses.KEY_NPAGE], self.decrease, 'Decrease value')
        self.bind_key(['+', curses.KEY_PPAGE], self.increase, 'Increase value')

    def add_field(self, y, x, text):
        if self.selected_line == y:
            mode = curses.A_REVERSE
        else:
            mode = curses.A_NORMAL
        self.addstr(y, x, text, mode)

    def display(self):
        for i, field in enumerate(self.form):
            if i == self.selected_line:
                mode = curses.A_REVERSE
            else:
                mode = curses.A_NORMAL
            if field:
                (label, (fn, key), editor) = field
                self.addstr(i + 1, 1, f'{label}: {fn(self.data[key])}', mode)
            else:
                self.addstr(i + 1, 1, ' ' * 10, mode)

        y, x = self.get_dimensions()
        for i, line in enumerate(self.error.splitlines()):
            lineno = len(self.form) + i + 2
            if lineno > y:
                break
            self.addstr(lineno, 1, line, curses.color_pair(curses.COLOR_RED))

    def update(self, key):
        def _inner(value):
            self.data[key] = value
            if key == 'time_spent':
                self.data['billable'] = value
        return _inner

    def key_up(self, key):
        if self.selected_line > 0:
            self.selected_line -= 1

    def key_down(self, key):
        if self.selected_line < len(self.form) - 1:
            self.selected_line += 1

    def key_select(self, key):
        field = self.form[self.selected_line]
        if field:
            label, (fn, key), editor = field
            kwargs = {'data': fn(self.data[key]), 'update': self.update(key)}
            return editor, kwargs

    def update_worklog(self, key):
        # Update without id creates worklog
        self.error = ''
        try:
            created = tempo.update_worklog(**self.data)
        except tempo.ApiError as e:
            self.error = e.error
        else:
            self.create_callback(created)
            self.close()

    def increase(self, key, mult=1):
        field = self.form[self.selected_line]
        if field:
            label, (fn, key), editor = field
            if isinstance(self.data[key], (int, float)):
                new_value = self.data[key] + mult * 60 * 30
                if new_value >= 0:
                    self.update(key)(new_value)
            elif isinstance(self.data[key], (datetime.datetime)):
                new_value = self.data[key] + datetime.timedelta(hours=1 * mult)
                self.update(key)(new_value)

    def decrease(self, key):
        self.increase(key, mult=-1)


class Editor:
    editor_params = {
        'vi': ['+startinsert'],
        'vim': ['+startinsert'],
    }

    def get_editor(self):
        return (
            os.environ.get('VISUAL') or
            os.environ.get('EDITOR') or
            'vi'
        )

    def __call__(self, update, data=None):
        self.data = data
        self._update = update
        with tempfile.NamedTemporaryFile(mode='r+') as tmpfile:
            if data:
                tmpfile.write(data)
                tmpfile.flush()
            editor = self.get_editor()
            subprocess.check_call(
                [editor] +
                self.editor_params.get(os.path.basename(editor), []) +
                [tmpfile.name]
            )
            tmpfile.seek(0)
            return self.update(self.convert(tmpfile.read().strip()))

    def update(self, value):
        self._update(value)

    def convert(self, value):
        return value


class DateEditor(Editor):

    def convert(self, value):
        if not value:
            return datetime.datetime.now()
        return human_to_datetime(value)


class TimeEditor(Editor):
    def convert(self, value):
        return human_to_seconds(value)


class IssueEditor(Editor):
    def update(self, data):
        return IssuePicker, {'search': data, 'callback': super().update}


class IssuePicker(Component):
    def __init__(self, search, callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sections = jira.issue_picker(search)
        self.selected_issue = None
        self.callback = callback

    def display(self):
        i = 0
        self.issues = []
        for section in self.sections:
            self.addstr(i, 1, section.label)
            i += 1
            for issue in section.issues:
                if not self.selected_issue:
                    self.selected_issue = issue
                if issue == self.selected_issue:
                    mode = curses.A_REVERSE
                else:
                    mode = curses.A_NORMAL
                self.addstr(i, 5, f'{issue.key} - {issue.summary}', mode)
                i += 1
                self.issues.append(issue)
        if not self.issues:
            self.callback(None)
            self.close()

    def key_up(self, key):
        idx = self.issues.index(self.selected_issue)
        if idx > 0:
            self.selected_issue = self.issues[idx - 1]

    def key_down(self, key):
        idx = self.issues.index(self.selected_issue)
        if idx + 1 < len(self.issues):
            self.selected_issue = self.issues[idx + 1]

    def key_select(self, key):
        self.callback(self.selected_issue.key)
        self.close()
