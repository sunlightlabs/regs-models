from mongoengine import *
from export import ExportQuerySet

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
            text_out = None
            if len(out) <= 100000:
                try:
                    text_out = html2text.html2text(out)
                except HTMLParser.HTMLParseError:
                    pass
            # if we get bad HTML or the HTML is too long, just strip out the tags
            return text_out if text_out is not None else strip_tags(out)

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

    meta = {
        'allow_inheritance': False,
    }

    def canonical_view(self):
        return _preferred_view(self.views)


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

    def canonical_view(self):
        return _preferred_view(self.views)

    def get_summary(self):
        # for FR docs, do some regex schenanigans to try to extract some summary text
        if self.type not in ['proposed_rule', 'rule', 'notice']:
            raise NotImplementedError()

        # find a candidate view
        views = [view for view in self.views if view.type == "html" and view.extracted == "yes"]
        if not views:
            return None

        text = views[0].as_text()

        # strip extra indentation
        text = text.replace("\n    ", "\n")

        # strip page breaks
        text = re.sub(r"[\n\r]+\[\[Page \d+\]\][\r\n]+", "\n", text)

        # find the summary block
        matches = re.findall(r"SUMMARY: (.*?)(?:\r?\n){2,}", text, re.MULTILINE | re.DOTALL)
        if not matches:
            return None

        # collapse spaces and return
        return re.sub("\s+", " ", matches[0])

DOC_TYPES = {
    'Public Submission': 'public_submission',
    'Other': 'other',
    'Supporting & Related Material': 'supporting_material',
    'Notice': 'notice',
    'Rule': 'rule',
    'Proposed Rule': 'proposed_rule'
}

class EmptyView(object):
    def as_text(self):
        return ""

    type = None

VIEW_TYPE_PREFERENCE = {
    'html': 4, 'xml': 4, 'crtext': 4,
    'msw':3, 'msw6': 3, 'msw8': 3, 'msw12': 3,
    'docx': 3,
    'rtf': 3,
    'wp8': 3,
    'txt': 2,
    'pdf': 1
}
def _preferred_view(views):
    """Return the preferred canonical view based on file type."""

    extracted_views = [v for v in views if v.extracted == 'yes']
    if not extracted_views:
        return EmptyView()

    sorted_views = sorted(extracted_views, key=lambda v: VIEW_TYPE_PREFERENCE.get(v.type, 0), reverse=True)
    return sorted_views[0]
