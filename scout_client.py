import base64
import json
import os
import urllib
import urllib2
import urlparse
import zlib


ENDPOINT = None
KEY = None


class Scout(object):
    def __init__(self, endpoint=ENDPOINT, key=KEY):
        self.endpoint = endpoint
        self.key = key

    def get_full_url(self, url):
        return urlparse.urljoin(self.endpoint, url)

    def get(self, url, **kwargs):
        headers = {'Content-Type': 'application/json'}
        if self.key:
            headers['key'] = self.key
        if kwargs:
            if '?' not in url:
                url += '?'
            url += urllib.urlencode(kwargs, True)
        request = urllib2.Request(self.get_full_url(url), headers=headers)
        fh = urllib2.urlopen(request)
        return json.loads(fh.read())

    def post(self, url, data=None):
        headers = {'Content-Type': 'application/json'}
        if self.key:
            headers['key'] = self.key
        request = urllib2.Request(
            self.get_full_url(url),
            data=json.dumps(data or {}),
            headers=headers)
        fh = urllib2.urlopen(request)
        return json.loads(fh.read())

    def delete(self, url):
        headers = {}
        if self.key:
            headers['key'] = self.key
        request = urllib2.Request(self.get_full_url(url), headers=headers)
        request.get_method = lambda: 'DELETE'
        fh = urllib2.urlopen(request)
        return json.loads(fh.read())

    def get_indexes(self):
        return self.get('/')['indexes']

    def create_index(self, name):
        return self.post('/', {'name': name})

    def rename_index(self, old_name, new_name):
        return self.post('/%s/' % old_name, {'name': new_name})

    def delete_index(self, name):
        return self.delete('/%s/' % name)

    def get_index(self, name, **kwargs):
        return self.get('/%s/' % name, **kwargs)

    def get_documents(self, **kwargs):
        return self.get('/documents/', **kwargs)

    def create_document(self, content, indexes, identifier=None, **metadata):
        if not isinstance(indexes, (list, tuple)):
            indexes = [indexes]
        return self.post('/documents/', {
            'content': content,
            'identifier': identifier,
            'indexes': indexes,
            'metadata': metadata})

    def update_document(self, document_id=None, content=None, indexes=None,
                        metadata=None, identifier=None):
        if not document_id and not identifier:
            raise ValueError('`document_id` must be provided.')

        data = {}
        if content is not None:
            data['content'] = content
        if indexes is not None:
            if not isinstance(indexes, (list, tuple)):
                indexes = [indexes]
            data['indexes'] = indexes
        if metadata is not None:
            data['metadata'] = metadata

        if not data:
            raise ValueError('Nothing to update.')

        return self.post('/documents/%s/' % document_id, data)

    def delete_document(self, document_id=None):
        if not document_id:
            raise ValueError('`document_id` must be provided.')

        return self.delete('/documents/%s/' % document_id)

    def get_document(self, document_id=None):
        if not document_id:
            raise ValueError('`document_id` must be provided.')

        return self.get('/documents/%s/' % document_id)

    def create_with_attachments(self, content, indexes, filenames,
                                identifier=None, **metadata):
        doc = self.create_document(content, indexes, identifier, **metadata)
        self.attach_files(doc['id'], filenames)

    def attach_file(self, document_id, filename, data, compress=False):
        post = {'filename': filename}
        if compress:
            data = zlib.compress(data)
        post['data'] = base64.b64encode(data)
        return self.post('/documents/%s/attachments/' % document_id, post)

    def attach_files(self, document_id, filenames):
        for filename in filenames:
            if filename.startswith('http:') or filename.startswith('https:'):
                parse_result = urlparse.urlparse(filename)
                fh = urllib2.urlopen(filename)
                filename = parse_result.path
                data = fh.read()
            elif os.path.isfile(filename):
                with open(filename, 'rb') as fh:
                    data = fh.read()
            elif os.path.isdir(filename):
                filenames = [os.path.join(filename, item)
                             for item in os.listdir(filename)
                             if os.path.isfile(item)]
                self.attach_files(document_id, filenames)
            else:
                raise ValueError('Unrecognized file: %s' % filename)

            self.attach_file(
                document_id,
                os.path.basename(filename),
                data,
                compress=True)

    def detach_file(self, document_id, filename):
        return self.delete('/documents/%s/attachments/%s/' %
                           (document_id, filename))

    def get_attachments(self, document_id):
        return self.get('/documents/%s/attachments/' % document_id)

    def get_attachment(self, document_id, filename):
        return self.get('/documents/%s/attachments/%s/' %
                        (document_id, filename))

    def download_attachment(self, document_id, filename):
        return self.get('/documents/%s/attachments/%s/download/' %
                        (document_id, filename))

    def search(self, index, query, **kwargs):
        kwargs['q'] = query
        return self.get('/%s/search/' % index, **kwargs)

    def search_attachments(self, index, query, **kwargs):
        kwargs['q'] = query
        return self.get('/%s/search/attachments/' % index, **kwargs)
