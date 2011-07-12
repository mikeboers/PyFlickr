import abc
import collections
import hashlib
import json
import logging
import os
import pprint
import re
import urllib

import oauth2 as oauth

log = logging.getLogger(__name__)


REST_URL     = 'http://api.flickr.com/services/rest/'
AUTH_URL     = 'http://flickr.com/services/auth/'
UPLOAD_URL   = 'http://api.flickr.com/services/upload/'
REPLACE_URL  = 'http://api.flickr.com/services/replace/'


class FlickrError(ValueError):
    def __init__(self, code, message):
        super(FlickrError, self).__init__('(%d) %s' % (code, message))
        self.code = code
        

class FormatterInterface(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def prepare_data(self, data):
        pass
    
    @abc.abstractmethod
    def parse_response(self, meta, content):
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

class LXMLETreeFormatter(object):
    def prepare_data(self, data):
        data['format'] = 'rest'
    def parse_response(self, meta, content):
        from lxml.etree import XML
        return XML(content)

class LXMLObjectifyFormatter(object):
    def prepare_data(self, data):
        data['format'] = 'rest'
    def parse_response(self, meta, content):
        from lxml.objectify import fromstring
        return fromstring(content)
                
class JSONFormatter(object):
    def prepare_data(self, data):
        data['format'] = 'json'
        data['nojsoncallback'] = '1'
    def parse_response(self, meta, content):
        return json.loads(content)

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
    
    def __init__(self, keys, access_token=None, format='etree'):
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
        
        self.consumer = oauth.Consumer(*keys)
        self.token = oauth.Token(*access_token) if access_token else None
        self.client = oauth.Client(self.consumer, self.token)
    
    def __getattr__(self, name):
        return _MethodPlaceholder(self, 'flickr.' + name)
    
    def __call__(self, method, **data):
        if not method.startswith('flickr.'):
            method = 'flickr.' + method
        data['method'] = method
        formatter = formatters[data.get('format', self.format)]
        formatter.prepare_data(data)
        url = REST_URL + '?' + urllib.urlencode(data)
        resp, content = self.client.request(url)
        return formatter.parse_response(resp, content)
    
    # def __call__(self, method, **data):
    #     if 'format' in data:
    #         del data['format']
    #     res = treesoup.parse(self.raw_call(method, **data))
    #     if res['stat'] == 'fail':
    #         raise FlickrError(int(res.err['code']), res.err['msg'])
    #     return res[0]
    
    
    
    
    def build_web_auth_link(self, perms='read'):
        """Build a link to authorize a web user.
        
        Upon authorization, the user will be returned to the callback URL set
        for the current key along with a "frob" GET parameter to be passed to
        Flickr.authorize()
        
        See: http://www.flickr.com/services/api/auth.howto.web.html
            
        """
        
        request = dict(perms=perms)
        self._sign_request(data)
        return AUTH_URL + '?' + urllib.urlencode(request)
    
    def authorize(self, frob=None):
        """Authorize the instance after handshake with Flickr; returns token.
        
        Uses the last retrieved frob if one is not supplied. Automatically
        remembers the token and user info.
        
        See: http://www.flickr.com/services/api/auth.howto.web.html
        See: http://www.flickr.com/services/api/auth.howto.desktop.html
        
        """
        
        frob = frob or self.frob
        if not frob:
            raise ValueError('no frob')
        
        res = self('auth.getToken', frob=frob)
        self.token = res.token.text
        self._last_checked_token = self.token
        self._authed_user = res.user
        
        return self.token
    
    
