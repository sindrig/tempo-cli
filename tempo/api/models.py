import datetime
from typing import Callable

DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class Item:
    def __init__(self, data: dict):
        self.self_link = data['self']
        self.populate(data)

    def populate(self, data: dict):
        for field in self.fields:
            setattr(self, field.name, field.value(data))


class List(Item):
    def __iter__(self):
        return iter(self._items)

    def get_type(self):
        if not hasattr(self, 'of'):
            raise NotImplementedError()
        return self.of

    def populate(self, data: dict):
        web_item_type = self.get_type()
        self.metadata = Metadata(data['metadata'])
        self._items = [
            web_item_type(item_data)
            for item_data in data['results']
        ]


class Metadata:
    def __init__(self, data: dict):
        self.count = data['count']
        self.offset = data['offset']
        self.limit = data['limit']


class Field:
    def __init__(self, name: str, data_key: str = None):
        self.name = name
        if data_key is None:
            components = name.split('_')
            self.data_key = (
                components[0] + ''.join(x.title() for x in components[1:])
            )
        else:
            self.data_key = data_key

    def value_getter(self, data):
        if callable(self.data_key):
            return self.data_key(data)
        return data[self.data_key]

    def value(self, data):
        return self.convert(self.value_getter(data))

    def convert(self, value):
        return value


class ItemField(Field):
    item = None

    def using(self, item: Item = None):
        self.item = item
        return self

    def convert(self, value):
        return self.item(value)


class TimeDeltaField(Field):
    def convert(self, value):
        if value:
            return datetime.timedelta(seconds=value)


class DateTimeField(Field):
    def convert(self, value):
        if value:
            return datetime.datetime.strptime(value, DATETIME_FORMAT)


# JIRA


class Issue(Item):
    fields = [
        Field('key')
    ]


class JiraUser(Item):
    fields = [
        Field('account_id')
    ]


# TEMPO


class WorkAttributeValues(Item):
    def populate(self, data: dict):
        self.values = data['values']


class Worklog(Item):
    fields = [
        ItemField('attributes').using(WorkAttributeValues),
        ItemField('author').using(JiraUser),
        TimeDeltaField('billable', 'billableSeconds'),
        Field('description'),
        ItemField('issue').using(Issue),
        Field('jira_worklog_id'),
        Field('id', 'tempoWorklogId'),
        DateTimeField('created_at'),
        DateTimeField('updated_at'),
        TimeDeltaField('time_spent', 'timeSpentSeconds'),
        DateTimeField(
            'started',
            lambda data: f'{data["startDate"]}T{data["startTime"]}Z'
        ),
    ]


class Worklogs(List):
    of = Worklog
