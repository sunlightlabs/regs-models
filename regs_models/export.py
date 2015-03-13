from mongoengine.queryset import QuerySet
from docket import Docket
from entity import Entity
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

def get_entity(entity_id, cache):
    if entity_id not in cache:
        entities = Entity.objects(id=entity_id)
        if len(entities):
            entity = entities[0]
            cache[entity_id] = {
                'id': entity_id,
                'name': entity.aliases[0], # use aliases[0] instead of td_name because aliases have been standardized
                'type': entity.td_type
            }
        else:
            cache[entity_id] = None
    return cache[entity_id]

class ExportQuerySet(QuerySet):
    def export_to_zip(self, filename):
        with zipfile.ZipFile(filename, 'a', zipfile.ZIP_DEFLATED, True) as export_zip:
            dockets = set()
            entity_cache = {}
            for doc in self:
                files = []
                    
                views = [('view', doc.views[i]) for i in xrange(len(doc.views))]
                for attachment in (doc.attachments[i] for i in xrange(len(doc.attachments))):
                    title = attachment.title
                    for view in (attachment.views[i] for i in xrange(len(attachment.views))):
                        if title:
                            view.title = title
                        views.append(('attachment', view))
                
                for type, view in views:
                    file = extract(
                        view,
                        ['downloaded', 'extracted']
                    )
                    file['url'] = view.download_url
                    if hasattr(view, 'title'):
                        file['title'] = view.title
                    if len(view.entities) > 0:
                        file['mentioned_entities'] = []
                        for entity_id in view.entities:
                            entity = get_entity(entity_id, entity_cache)
                            if entity:
                                file['mentioned_entities'].append(entity.copy())
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

                if len(doc.submitter_entities) > 0:
                    metadata['submitter_entities'] = []
                    for entity_id in doc.submitter_entities:
                        entity = get_entity(entity_id, entity_cache)
                        if entity:
                            metadata['submitter_entities'].append(entity.copy())

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