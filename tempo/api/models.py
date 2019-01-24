from typing import Union
import datetime

DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class Item:
    def __init__(self, data: dict):
        self.raw_data = data
        self.self_link = data.get('self')
        self.populate(data)

    def populate(self, data: dict):
        for field in self.fields:
            setattr(self, field.name, field.value(data))


class List(Item):
    def __init__(self, data: Union[dict, list]):
        if isinstance(data, dict):
            super().__init__(data)
        else:
            super().__init__({
                'results': data,
            })

    def __iter__(self):
        return iter(self._items)

    def __getitem__(self, idx):
        return self._items[idx]

    def get_type(self):
        if not hasattr(self, 'of'):
            raise NotImplementedError()
        return self.of

    def populate(self, data: dict):
        web_item_type = self.get_type()
        if 'metadata' in data:
            self.metadata = Metadata(data['metadata'])
        else:
            self.metadata = None
        self._items = [
            web_item_type(item_data)
            for item_data in data['results']
        ]
        # if isinstance(data, dict):
        # else:
        #     self._items = [web_item_type(item_data) for item_data in data]


class Metadata:
    def __init__(self, data: dict):
        self.count = data['count']
        self.offset = data.get('offset')
        self.limit = data.get('limit')


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
        self.required = True

    def value_getter(self, data):
        if callable(self.data_key):
            return self.data_key(data)
        if self.required:
            return data[self.data_key]
        else:
            return data.get(self.data_key)

    def value(self, data):
        value = self.value_getter(data)
        if value or self.required:
            return self.convert(value)
        return value

    def convert(self, value):
        return value

    def optional(self):
        self.required = False
        return self


class ItemField(Field):
    item = None

    def using(self, item: Item = None):
        self.item = item
        return self

    def convert(self, value):
        return self.item(value)


class TimeDeltaField(Field):
    def convert(self, value):
        return datetime.timedelta(seconds=value)


class DateTimeField(Field):
    frmt = DATETIME_FORMAT

    def convert(self, value):
        return datetime.datetime.strptime(value, self.frmt)


class DateField(DateTimeField):
    frmt = DATE_FORMAT

    def convert(self, value):
        value = super().convert(value)
        return value.date()


class ArrayField(Field):
    data_type = str

    def of(self, data_type):
        self.data_type = data_type

    def convert(self, value):
        return [
            self.data_type(val)
            for val in value
        ]


# JIRA
class Issue(Item):
    fields = [
        Field('key')
    ]


class JiraUser(Item):
    fields = [
        Field('account_id'),
        Field('display_name'),
    ]


class AccessibleResource(Item):
    fields = [
        Field('id'),
        Field('name'),
        ArrayField('scopes'),
        Field('avatar_url'),
    ]


class AccessibleResources(List):
    of = AccessibleResource


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


class Holiday(Item):
    fields = [
        Field('name'),
        Field('description').optional(),
        TimeDeltaField('duration', 'durationSeconds'),
    ]


class UserSchedule(Item):
    fields = [
        DateField('date'),
        TimeDeltaField('required', 'requiredSeconds'),
        Field('type'),
        ItemField('holiday').using(Holiday).optional(),
    ]


class UserSchedules(List):
    of = UserSchedule
