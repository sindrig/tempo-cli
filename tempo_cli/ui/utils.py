import datetime


def sec_to_human(seconds: int) -> str:
    return ('%0.2f' % (seconds / 3600, )).rstrip('0').rstrip('.')


def delta_to_human(timedelta: datetime.timedelta) -> str:
    return sec_to_human(timedelta.total_seconds())


def date_to_human(date: datetime.date) -> str:
    return date.strftime('%a %Y-%m-%d')
