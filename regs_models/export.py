from mongoengine import QuerySet
from docket import Docket
import zipfile
import json

def extract(record, keys):
    out = {}
    for key in keys:
        if key in record:
            out[key] = record[key]
        elif hasattr(record, key):
            out[key] = record.key
    return out

def to_yaml(obj):
    import yaml
    return yaml.dump(obj, Dumper=yaml.dumper.SafeDumper, default_flow_style=False, indent=4)

class ExportQuerySet(QuerySet):
    def export_to_zip(self, filename):
        with zipfile.ZipFile(zip_path, 'a', zipfile.ZIP_DEFLATED, True) as export_zip:
            dockets = set()
            for doc in self:
                pass