from mongoengine import *

import re, html2text, HTMLParser
html2text.IGNORE_IMAGES = True
html2text.BODY_WIDTH = 0

_tag_stripper = re.compile(r'<[^>]*?>')
def strip_tags(text):
    return _tag_stripper.sub('', text)

class View(EmbeddedDocument):
    # data
    type = StringField(required=True)
    object_id = StringField()
    url = URLField(required=True)

    content = FileField(collection_name='files')
    mode = StringField(
        default="text",
        choices=["text", "html"]
    )
    
    file_path = StringField()
    entities = ListField(field=StringField())

    # flags
    downloaded = StringField(
        default="no",
        choices=["no", "failed", "yes"]
    )
    extracted = StringField(
        default="no",
        choices=["no", "failed_no_extractor", "failed_extraction", "failed_ocr", "yes"]
    )
    ocr=BooleanField(default=False)

    meta = {
        'allow_inheritance': False,
    }

    def as_text(self):
        out = unicode(self.content.read(), 'utf-8', 'ignore') if self.content else u''
        if self.mode == "text":
            return out
        else:
            try:
                return html2text.html2text(out)
            except HTMLParser.HTMLParseError:
                # if we get bad HTML, just strip out the tags
                return strip_tags(out)

    def as_html(self):
        out = unicode(self.content.read(), 'utf-8', 'ignore') if self.content else u''
        if self.mode == "text":
            # could probably do this better, but can wait
            return u"<html><body><pre>%s</pre></body></html>" % out
        else:
            return out


class Attachment(EmbeddedDocument):
    # data
    title = StringField(required=True)
    object_id = StringField()
    abstract = StringField()

    # sub-docs
    views = ListField(field=EmbeddedDocumentField(View))

    def canonical_view(self):
        return _preferred_view(views)

    meta = {
        'allow_inheritance': False,
    }


class Doc(Document):
    id = StringField(required=True, primary_key=True)

    # data
    title = StringField(required=True)
    agency = StringField(required=True)
    docket_id = StringField(required=True)
    type = StringField(
        required=True,
        choices=['public_submission', 'other', 'supporting_material', 'notice', 'rule', 'proposed_rule']
    )
    topics = ListField(field=StringField())
    object_id = StringField()
    details = DictField()

    abstract = StringField()
    rin = StringField()
    comment_on = DictField(default=None)

    submitter_entities = ListField(field=StringField())

    # sub-docs
    views = ListField(field=EmbeddedDocumentField(View))
    attachments = ListField(field=EmbeddedDocumentField(Attachment))

    def canonical_view(self):
        all_views = [_preferred_view(self.views)] + [_preferred_view(a.views) for a in self.attachments]
        if all_views:
            all_views.sort(key=lambda v: len(v.as_text()), reverse=True)
            return all_views[0]

        return None



    # flags
    deleted = BooleanField(default=False)
    scraped = StringField(
        default="no",
        choices=["no", "failed", "yes"]
    )
    renamed = BooleanField(default=False)
    in_search_index = BooleanField(default=False)
    in_aggregates = BooleanField(default=False)
    in_cluster_db = BooleanField(default=False)
    fr_doc = BooleanField(default=False)
    
    # dates
    created = DateTimeField()
    last_seen = DateTimeField()
    entities_last_extracted = DateTimeField()

    source = StringField(required=True, default="regulations.gov")

    # aggregate dict for FR docs
    stats = DictField()

    meta = {
        'allow_inheritance': False,
        'collection': 'docs',

        'indexes': [
            'docket_id',
            ('source', 'agency'),
            ('source', 'deleted', 'scraped', 'agency'),
            ('deleted', 'views.downloaded', 'agency'),
            ('deleted', 'attachments.views.downloaded', 'agency'),
            ('deleted', 'views.downloaded', 'views.extracted', 'agency'),
            ('deleted', 'attachments.views.downloaded', 'attachments.views.extracted', 'agency')
        ]
    }

DOC_TYPES = {
    'Public Submission': 'public_submission',
    'Other': 'other',
    'Supporting & Related Material': 'supporting_material',
    'Notice': 'notice',
    'Rule': 'rule',
    'Proposed Rule': 'proposed_rule'
}

def _preferred_view(views):
    """Return the preferred canonical view based on file type."""

    html_views = [v for v in views if v.type == 'html']
    if html_views:
        return html_views[0]
    
    pdf_views = [v for v in views if v.type == 'pdf']
    if pdf_views:
        return pdf_views[0]

    return views[0]
