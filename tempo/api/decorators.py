import functools
import uuid
import threading
import logging

logger = logging.getLogger(__name__)


def returns(_type):
    def wrapper(f):
        @functools.wraps(f)
        def inner(*args, **kwargs):
            data = f(*args, **kwargs)
            return _type(data)
        return inner
    return wrapper


mem_cache = {}


class RestRequestThread(threading.Thread):
    def __init__(self, f, callback, *args, **kwargs):
        self.callback = callback
        self.f = f
        self.kwargs = kwargs
        self.args = args
        super().__init__()
        self.start()

    def run(self):
        self.callback(self.f(*self.args, **self.kwargs))


def api_request(original_function=None, cache=False):
    method_uuid = str(uuid.uuid4())

    def decorate(f):

        @functools.wraps(f)
        def wrapper(*args, cache=cache, callback=None, **kwargs):
            cache_key = f'{method_uuid}_{str(kwargs)}'
            if cache and cache_key in mem_cache:
                return mem_cache[cache_key]
            if callback:
                RestRequestThread(f, callback, *args, **kwargs)
            else:
                result = f(*args, **kwargs)
                if cache:
                    mem_cache[cache_key] = result
                return result
        return wrapper

    if original_function:
        return decorate(original_function)
    return decorate
