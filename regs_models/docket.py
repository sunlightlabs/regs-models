from mongoengine import *

class Docket(Document):
    id = StringField(required=True, primary_key=True)

    title = StringField()
    agency = StringField()
    rin = StringField()
    year = IntField()

    details = DictField()
    stats = DictField()

    # extra bucket to put internally-constructed metadata that should be preserved across docket rebuilds
    annotations = DictField()

    scraped = StringField(
        default="no",
        choices=["no", "failed", "yes"]
    )
    in_search_index = BooleanField(default=False)

    source = StringField(default="regulations.gov")

    meta = {
        'allow_inheritance': False,
        'collection': 'dockets'
    }
