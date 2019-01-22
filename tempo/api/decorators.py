import functools


def returns(_type):
    def wrapper(f):
        @functools.wraps(f)
        def inner(*args, **kwargs):
            return _type(f(*args, **kwargs))
        return inner
    return wrapper
