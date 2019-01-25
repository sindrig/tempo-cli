import datetime


def sec_to_human(seconds: int) -> str:
    return ('%0.2f' % (seconds / 3600, )).rstrip('0').rstrip('.') + 'h'


def delta_to_human(timedelta: datetime.timedelta) -> str:
    return sec_to_human(timedelta.total_seconds())


def date_to_human(date: datetime.date) -> str:
    return date.strftime('%a %Y-%m-%d')


def datetime_to_human(dt: datetime.datetime) -> str:
    return dt.strftime('%Y-%m-%d %H:%M')


def human_to_datetime(human: str) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(human, '%Y-%m-%d %H:%M')
    except ValueError:
        return datetime.datetime.min


def human_to_seconds(human: str) -> int:
    human = human.rstrip('h').replace(',', '.')
    try:
        hours = float(human)
    except ValueError:
        return 0
    return hours * 3600
