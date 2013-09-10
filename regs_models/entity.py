from mongoengine import *

class Entity(Document):
    id = StringField(required=True, primary_key=True)
    td_type = StringField(
        required=True,
        choices=['individual', 'politician', 'organization', 'industry']
    )
    td_name = StringField()
    aliases = ListField()
    filtered_aliases = ListField()

    searchable = BooleanField(default=False)

    stats = DictField()

    meta = {
        'allow_inheritance': False,
        'collection': 'entities',
        'indexes': [
            'td_type',
            (('searchable', 1), ('aliases', 'text'))
        ]
    }
