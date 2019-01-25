import logging
import locale
import inspect
import curses

from tempo_cli.ui.components.my_work import MyWork
from tempo_cli.ui.base import Component

logger = logging.getLogger(__name__)


class TempoUI:
    stdscr = None

    def __init__(self, tempo, jira):
        self.tempo = tempo
        self.jira = jira
        self.running = True
        self.page_stack = []

    def __call__(self, stdscr):
        self.stdscr = stdscr
        self.container_kwargs = {
            'stdscr': self.stdscr,
            'tempo': self.tempo,
            'jira': self.jira,
            'close': self.go_back,
        }
        curses.use_default_colors()
        curses.init_pair(curses.COLOR_RED, curses.COLOR_RED, -1)
        curses.init_pair(curses.COLOR_GREEN, curses.COLOR_GREEN, -1)
        locale.setlocale(locale.LC_ALL, "")
        self.start()

    def exit(self):
        self.running = False

    @property
    def page(self):
        return self.page_stack[-1]

    def go_back(self, key=None):
        self.page_stack.pop()
        if not self.page_stack:
            self.exit()

    def set_page(self, page):
        self.page_stack.append(page)

    def start(self):
        self.set_page(MyWork(**self.container_kwargs))
        self.display()

    def navigate(self):
        key = self.stdscr.getch()
        target = None
        if key in (curses.KEY_ENTER, ord('\n')):
            target = self.page.key_select
        elif key in (curses.KEY_UP, ord('k')):
            target = self.page.key_up
        elif key in (curses.KEY_DOWN, ord('j')):
            target = self.page.key_down
        elif key in (curses.KEY_LEFT, ord('h')):
            target = self.page.key_left
        elif key in (curses.KEY_RIGHT, ord('l')):
            target = self.page.key_right
        elif key == curses.KEY_RESIZE:
            target = self.page.refresh
        elif key in self.page.bound_keys:
            target = self.page.bound_keys[key]
        if target:
            result = target(key)
            while result is not None:
                callback, kwargs = result
                result = None
                if (
                    inspect.isclass(callback) and
                    issubclass(callback, Component)
                ):
                    self.set_page(callback(**self.container_kwargs, **kwargs))
                else:
                    result = callback(**kwargs)

    def display(self):
        while self.running:
            self.page.refresh()
            self.navigate()
