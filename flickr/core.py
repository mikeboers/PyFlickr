import abc
import collections
import hashlib
import json
import logging
import os
import pprint
import re
from urlparse import parse_qsl
from urllib import urlencode

import oauth2 as oauth

log = logging.getLogger(__name__)



UPLOAD_URL = 'https://api.flickr.com/services/upload/'
REPLACE_URL = 'https://api.flickr.com/services/replace/'


class FlickrError(ValueError):
    def __init__(self, status, code, message):
        super(FlickrError, self).__init__('%s code %s; %s' % (status, code, message))
        self.code = code
        

class FormatterInterface(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def prepare_data(self, data):
        pass
    
    @abc.abstractmethod
    def parse_response(self, meta, content):
        pass
    
    @abc.abstractmethod
    def get_status(self, response):
        # return stat, err_core, err_message
        pass
    
    @abc.abstractmethod
    def get_page_count(self, response):
        """Get the integer number of pages in a response, or None."""
        pass
    
    @abc.abstractmethod
    def get_page_contents(self, response):
        """Get an iterator across the elements in this page."""
        pass
    
class ETreeFormatter(object):
    def prepare_data(self, data):
        data['format'] = 'rest'
    def parse_response(self, meta, content):
        try:
            import xml.etree.CElementTree as etree
        except ImportError:
            import xml.etree.ElementTree as etree
        return etree.fromstring(content)
    def get_status(self, response):
        stat = response.get('stat')
        code, msg = None, None
        if stat == 'fail':
            code = response.find('err').get('code')
            msg = response.find('err').get('msg')
        return stat, code, msg
    def get_page_count(self, response):
        return int(response[0].get('pages'))
    def get_page_contents(self, response):
        return response[0]

class LXMLETreeFormatter(ETreeFormatter):
    def parse_response(self, meta, content):
        from lxml.etree import XML
        return XML(content)

class LXMLObjectifyFormatter(LXMLETreeFormatter):
    def parse_response(self, meta, content):
        from lxml.objectify import fromstring
        return fromstring(content)
                
class JSONFormatter(object):
    def prepare_data(self, data):
        data['format'] = 'json'
        data['nojsoncallback'] = '1'
    def parse_response(self, meta, content):
        return json.loads(content)
    def get_status(self, response):
        return tuple(response.get(name) for name in ('stat', 'code', 'message'))
    def get_page_count(self, response):
        for k, v in response.iteritems():
            if isinstance(v, dict):
                return int(v['pages'])
    def get_page_contents(self, response):
        for k, v in response.iteritems():
            if isinstance(v, dict):
                for k, v2 in v.iteritems():
                    if isinstance(v2, list):
                        return v2

formatters = {
    'etree': ETreeFormatter(),
    'lxml.etree': LXMLETreeFormatter(),
    'lxml.objectify': LXMLObjectifyFormatter(),
    'json': JSONFormatter(),
}

    
class _MethodPlaceholder(object):
    def __init__(self, root, name):
        self.root = root
        self.name = name
    def __repr__(self):
        return '<%s method of %r>' % (self.name, self.root)
    def __call__(self, **kwargs):
        return self.root(self.name, **kwargs)
    def __getattr__(self, name):
        return _MethodPlaceholder(self.root, self.name +'.' + name)
    def iter(self, **kwargs):
        return self.root.iter(self.name, **kwargs)
    def pages(self, **kwargs):
        return self.root.pages(self.name, **kwargs)

    
class Flickr(object):
    
    def __init__(self, key, secret, token=None, format='etree', strict=True,
        echo=False
    ):
        """Create a Flickr API object
        
        Params:
            key/secret: Flickr API keys
            access_token: string, oauth.Token, or None
            format: one of 'etree', 'lxml.etree', 'lxml.objectify', 'json'
        """

        self.format = format
        self.strict = strict
        self.echo = echo
        
        if isinstance(token, basestring):
            token = oauth.Token.from_string(token)
        elif token is not None and not isinstance(token, oauth.Token):
            raise TypeError('token of unexpected type %r' % type(token))
                
        self._oauth_consumer = oauth.Consumer(key, secret)
        self._oauth_client = oauth.Client(self._oauth_consumer, token)        
            
    def __getattr__(self, name):
        return _MethodPlaceholder(self, 'flickr.' + name)
    
    def _get_formatter(self, **kwargs):
        return formatters[kwargs.get('format', self.format)]
        
    def __call__(self, method, **data):
        strict = data.pop('strict', self.strict)
        if self.echo:
            log.info('%s(%s)' % (method, ', '.join('%s=%r' % x for x in data.iteritems())))
        data['method'] = method
        formatter = self._get_formatter(**data)
        formatter.prepare_data(data)
        url = 'https://api.flickr.com/services/rest/?' + urlencode(data)
        meta, content = self._oauth_client.request(url)
        response = formatter.parse_response(meta, content)
        stat, err_code, err_msg = formatter.get_status(response)
        if strict and stat != 'ok':
            raise FlickrError(stat, err_code, err_msg)
        return response
    
    def pageiter(self, method, **data):
        page = int(data.pop('page', 1))
        pages = page
        formatter = self._get_formatter(**data)
        while page <= pages:
            data['page'] = page
            res = self(method, **data.copy())
            yield formatter.get_page_contents(res)
            pages = formatter.get_page_count(res)
            page += 1
                
    def iter(self, method, **data):
        for page in self.pageiter(method, **data):
            for x in page:
                yield x
        
    def get_request_token(self, oauth_callback):
        url = 'https://www.flickr.com/services/oauth/request_token'
        query = urlencode(dict(oauth_callback=oauth_callback))
        resp, content = self._oauth_client.request(url + '?' + query)
        return content
    
    def get_auth_url(self, oauth_token):
        url = 'https://www.flickr.com/services/oauth/authorize'
        if isinstance(oauth_token, basestring):
            oauth_token = oauth.Token.from_string(oauth_token)
        request = oauth.Request.from_token_and_callback(token=oauth_token, http_url=url)
        return url + '?' + urlencode(request)
    
    def get_access_token(self, oauth_token, oauth_verifier):
        url = 'https://www.flickr.com/services/oauth/access_token'
        if isinstance(oauth_token, basestring):
            oauth_token = oauth.Token.from_string(oauth_token)
        
        client = oauth.Client(self._oauth_consumer, oauth_token)    
        query = urlencode(dict(oauth_verifier=oauth_verifier))
        resp, content = client.request(url + '?' + query)
        return str(oauth.Token.from_string(content)), dict(parse_qsl(content))
        
        
    
    
