import logging
import locale
import inspect
import curses

from tempo.api import register_lifecycle_handler
from tempo_cli.ui.components.my_work import MyWork
from tempo_cli.ui.base import Component

logger = logging.getLogger(__name__)


class TempoUI:
    stdscr = None
    _http_request_count = 0

    def __init__(self):
        self.running = True
        self.page_stack = []

    def __call__(self, stdscr):
        self.stdscr = stdscr
        self.container_kwargs = {
            'stdscr': self.stdscr,
            'close': self.go_back,
            'on_top': self.on_top,
            'get_http_request_count': self.get_http_request_count,
        }
        curses.use_default_colors()
        curses.init_pair(curses.COLOR_RED, curses.COLOR_RED, -1)
        curses.init_pair(curses.COLOR_GREEN, curses.COLOR_GREEN, -1)
        locale.setlocale(locale.LC_ALL, "")
        register_lifecycle_handler(self)
        self.start()

    def exit(self):
        self.running = False

    @property
    def page(self):
        if self.page_stack:
            return self.page_stack[-1]

    def go_back(self, key=None):
        self.page_stack.pop()
        if not self.page_stack:
            self.exit()

    def set_page(self, page):
        self.page_stack.append(page)

    def on_top(self, page):
        return page == self.page_stack[-1]

    def get_http_request_count(self):
        return self._http_request_count

    def start(self):
        self.set_page(MyWork(**self.container_kwargs))
        self.display()

    def navigate(self):
        key = self.stdscr.getch()
        keyname = curses.keyname(key)
        logger.info('key %s', key)
        logger.info('keyname %s', curses.keyname(key))
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
        elif keyname in self.page.bound_keys:
            target = self.page.bound_keys[keyname]
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

    def on_request(self, request_count, **kwargs):
        self._http_request_count = request_count
        if self.page:
            self.page.refresh()

    def on_request_done(self, request_count, **kwargs):
        self._http_request_count = request_count
        if self.page:
            self.page.refresh()
