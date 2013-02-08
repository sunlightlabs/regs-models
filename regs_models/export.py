from mongoengine.queryset import QuerySet
from docket import Docket
from collections import OrderedDict
import zipfile
import json
import os
from regs_yaml import *
import datetime

dthandler = lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime) else None

def extract(record, keys):
    if hasattr(record, "to_mongo"):
        record = record.to_mongo()

    out = OrderedDict()
    for key in keys:
        if key in record and record[key]:
            out[key[1:] if key.startswith("_") else key] = record[key]
    return out

class ExportQuerySet(QuerySet):
    def export_to_zip(self, filename):
        with zipfile.ZipFile(filename, 'a', zipfile.ZIP_DEFLATED, True) as export_zip:
            dockets = set()
            for doc in self:
                files = []
                    
                views = [('view', view) for view in doc.views]
                for attachment in doc.attachments:
                    title = attachment.title
                    for view in attachment.views:
                        if title:
                            view.title = title
                        views.append(('attachment', view))
                
                for type, view in views:
                    file = extract(
                        view,
                        ['downloaded', 'extracted', 'url']
                    )
                    if hasattr(view, 'title'):
                        file['title'] = view.title
                    if view.extracted == 'yes':
                        filename = '%s_%s_%s.txt' % (type, view.object_id, view.type)
                        file['filename'] = filename
                        
                        export_zip.writestr(os.path.join(doc.docket_id, doc.id, filename), view.as_text().encode('utf8'))
                        
                    files.append(file)
                    
                metadata = extract(
                    doc,
                    ['_id', 'title', 'agency', 'docket_id', 'type', 'topics', 'details', 'rin', 'source']
                )
                if doc.comment_on:
                    metadata['comment_on'] = extract(doc.comment_on, ['document_id', 'title', 'type'])

                metadata['files'] = files
                
                try:
                    export_zip.writestr(os.path.join(doc.docket_id, doc.id, 'metadata.yaml'), to_yaml(metadata))
                except:
                    export_zip.writestr(os.path.join(doc.docket_id, doc.id, 'metadata.json'), json.dumps(metadata, default=dthandler, indent=4))

                dockets.add(doc.docket_id)

            for docket_id in dockets:
                docket = Docket.objects(id=docket_id)
                if docket:
                    export_zip.writestr(
                        os.path.join(docket_id, 'metadata.yaml'),
                        to_yaml(
                            extract(
                                docket[0],
                                ['_id', 'title', 'agency', 'rin', 'details', 'year']
                            )
                        )
                    )