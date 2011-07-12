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


REST_URL = 'http://api.flickr.com/services/rest/'

REQUEST_TOKEN_URL = 'http://www.flickr.com/services/oauth/request_token'
USER_AUTH_URL = 'http://www.flickr.com/services/oauth/authorize'
ACCESS_TOKEN_URL = 'http://www.flickr.com/services/oauth/access_token'

UPLOAD_URL = 'http://api.flickr.com/services/upload/'
REPLACE_URL = 'http://api.flickr.com/services/replace/'


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

    
class Flickr(object):
    
    def __init__(self, keys, access_token=None, format='etree', strict=True):
        """Create a Flickr API object
        
        Params:
            keys: tuple of (api_key, api_secret)
            access_token: tuple of (access_token, token_secret), or None
            format: one of 'etree', 'lxml.etree', 'lxml.objectify', 'json'
        """
        
        assert len(keys) == 2
        assert len(access_token) == 2 if access_token else access_token is None
        self.keys = keys
        self.access_token = access_token
        
        self.format = format
        self.strict = strict
        
        self.consumer = oauth.Consumer(*keys)
        self.token = oauth.Token(*access_token) if access_token else None
        self.client = oauth.Client(self.consumer, self.token)
    
    def __getattr__(self, name):
        return _MethodPlaceholder(self, 'flickr.' + name)
    
        
    def __call__(self, method, **data):
        strict = data.pop('strict', self.strict)
        if not method.startswith('flickr.'):
            method = 'flickr.' + method
        data['method'] = method
        formatter = formatters[data.get('format', self.format)]
        formatter.prepare_data(data)
        url = REST_URL + '?' + urlencode(data)
        meta, content = self.client.request(url)
        response = formatter.parse_response(meta, content)
        stat, err_code, err_msg = formatter.get_status(response)
        if strict and stat != 'ok':
            raise FlickrError(stat, err_code, err_msg)
        
    
    def get_request_token(self, oauth_callback):
        url = 'http://www.flickr.com/services/oauth/request_token'
        query = urlencode(dict(oauth_callback=oauth_callback))
        resp, content = self.client.request(url + '?' + query)
        parsed = dict(parse_qsl(content))
        return parsed['oauth_token'], parsed['oauth_token_secret']
    
    def get_auth_url(self, oauth_token):
        url = 'http://www.flickr.com/services/oauth/authorize'
        query = urlencode(dict(oauth_token=oauth_token))
        return url + '?' + query
    
    def get_access_token(self, oauth_token, oauth_token_secret, oauth_verifier):
        url = 'http://www.flickr.com/services/oauth/access_token'
        query = urlencode(dict(oauth_verifier=oauth_verifier))
        token = oauth.Token(oauth_token, oauth_token_secret)
        client = oauth.Client(self.consumer, token)
        resp, content = client.request(url + '?' + query)
        parsed = dict(parse_qsl(content))
        return parsed
        
        
    
    
