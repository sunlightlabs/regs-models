from doc import Doc, Attachment, View, DOC_TYPES
from docket import Docket
from agency import Agency
from entity import Entity

from mongoengine import connect

try:
    from django.conf import settings
    # force evaluation of the settings so the ImportError gets raised in the right place
    dir(settings)
except ImportError:
    import settings

connect(getattr(settings, "DB_NAME", "regulations"), **getattr(settings, "DB_SETTINGS", {}))