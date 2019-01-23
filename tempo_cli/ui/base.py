import logging
from typing import Callable


logger = logging.getLogger(__name__)


class Component:
    def __init__(self, stdscr, tempo, jira, close):
        self.tempo = tempo
        self.jira = jira
        self.stdscr = stdscr
        self.close = close
        self.bound_keys = {}
        self.key_legend = {}
        self.bind_key('q', self.close, 'Close')

    def refresh(self):
        self.stdscr.clear()
        self.display()
        self.add_legend()
        self.stdscr.refresh()

    def add_legend(self):
        y, x = self.get_dimensions()
        legend = ', '.join(
            f'[{key}]: {description}'
            for key, description in self.key_legend.items()
        )
        self.addstr(y, 1, legend[:x])
        self.addstr(y + 1, 1, legend[x:])

    def key_up(self):
        pass

    def key_down(self):
        pass

    def key_right(self):
        pass

    def key_left(self):
        pass

    def key_select(self):
        pass

    def addstr(self, *args, **kwargs):
        self.stdscr.addstr(*args, **kwargs)

    def get_dimensions(self):
        y, x = self.stdscr.getmaxyx()
        # Reserve two lines on bottom for us to use
        return y - 2, x

    def bind_key(
        self,
        keys: list,
        callback: Callable,
        description: str=None
    ) -> None:
        '''
            Bind keys to a callable.
            The function should return a tuple of (Callable, kwargs)
            that it will be called with.
            In the case of a Container, required kwargs will be added
            automatically.
        '''
        if isinstance(keys, tuple):
            keys = list(keys)
        elif not isinstance(keys, list):
            keys = [keys]
        if description:
            self.key_legend[keys[0]] = description
        for i in range(len(keys)):
            if isinstance(keys[i], str):
                keys[i] = ord(keys[i])
        for key in keys:
            self.bound_keys[key] = callback
