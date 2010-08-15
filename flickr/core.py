"""
Flickr API binding.

"""

import collections
import hashlib
import json
import logging
import os
import pprint
import re
import urllib

import treesoup


log = logging.getLogger(__name__)


REST_URL     = 'http://api.flickr.com/services/rest/';
AUTH_URL     = 'http://flickr.com/services/auth/';

PERMS_NONE   = 'none';
PERMS_READ   = 'read';
PERMS_WRITE  = 'write';
PERMS_DELETE = 'delete';

UPLOAD_URL   = 'http://api.flickr.com/services/upload/';
REPLACE_URL  = 'http://api.flickr.com/services/replace/';

DEFAULT_KEY = os.environ.get('PYFLICKR_DEFAULT_KEY')
DEFAULT_SECRET = os.environ.get('PYFLICKR_DEFAULT_SECRET')

if DEFAULT_KEY:
    logging.info('Default key: %s' % DEFAULT_KEY)


class APIError(ValueError):
    
    def __init__(self, code, message):
        super(APIError, self).__init__('(%d) %s' % (code, message))
        self.code = code


class FlickrMeta(type):
    
    def __new__(mcls, name, bases, dict):
        dict['_namespaces'] = namespaces = {}
        for key in dict.keys():
            m = re.match(r'^_call_([a-zA-Z]+)_([a-zA-Z]+)$', key)
            if not m:
                continue
            namespace, method = m.groups()
            ns_set = namespaces.setdefault(namespace, set())
            ns_set.add(method)
        cls = super(FlickrMeta, mcls).__new__(mcls, name, bases, dict)
        return cls


class FlickrNamespace(object):
    
    def __init__(self, api, name):
        self._api = api
        self._name = name
        self._methodset = api._namespaces[name]
    
    def __getattr__(self, name):
        if name not in self._methodset:
            raise AttributeError(name)
        return getattr(self._api, '_call_%s_%s' % (self._name, name))
    
    
class Flickr(object):
    __metaclass__ = FlickrMeta
    
    def __init__(self, key=DEFAULT_KEY, secret=DEFAULT_SECRET, token=None):
        
        if not key:
            raise ValueError('missing api key')
        
        self.key = key
        self.secret = secret
        self.token = token
        
        self.frob = None
        self._last_checked_token = None
        self._user = None
    
    def __getattr__(self, name):
        if name in self._namespaces:
            return FlickrNamespace(self, name)
        raise AttributeError(name)
    
    def _sign_request(self, data):    
        data['api_key'] = self.key
        if self.secret:
            to_sign = self.secret + ''.join('%s%s' % i for i in sorted(data.items()))
            data['api_sig'] = hashlib.md5(to_sign).hexdigest()
    
    def raw_call(self, method, **data):
        if not method.startswith('flickr.'):
            method = 'flickr.' + method
        data['method'] = method
        # Do auth if we have a user auth token.
        if self.token is not None:
            data['auth_token'] = self.token
        self._sign_request(data)
        url = REST_URL + '?' + urllib.urlencode(data)
        # Don't need to manually decode the UTF-8 here as the XML parser will.
        return urllib.urlopen(url).read()
    
    def __call__(self, method, **data):
        if 'format' in data:
            del data['format']
        res = treesoup.parse(self.raw_call(method, **data))
        if res['stat'] == 'fail':
            raise APIError(int(res.err['code']), res.err['msg'])
        return res[0]
    
    
    
    
    def build_web_auth_link(self, perms=PERMS_READ):
        """Build a link to authorize a web user.
        
        Upon authorization, the user will be returned to the callback-URL as
        define in the Flickr API setup at
        http://www.flickr.com/services/api/keys/ along with a GET frob
        parameter.
        
        Flickr docs are here:
            http://www.flickr.com/services/api/auth.howto.web.html
        """
        
        data = {'perms': perms}
        self._sign_request(data)
        return AUTH_URL + '?' + urllib.urlencode(data)
    
    
    def get_frob(self):
        """Retrieve a one-time use frob from Flickr server.
        
        Remembers the last retrieved frob for use in authenticating.
        
        For use when authenticating using desktop-app method.
        See: http://www.flickr.com/services/api/auth.howto.desktop.html
        """
        
        res = self.call('auth.getFrob')
        self.frob = res['frob']['_content']
        return self.frob
            
    def build_desktop_auth_link(self, perms=PERMS_READ, frob=None):
        """Build a link to authorize a desktop user.
        
        Accepts a frob, or automatically generates one and stores it at
        flickr.frob.
        
        See: http://www.flickr.com/services/api/auth.howto.desktop.html
        """
        
        data = {'perms': perms, 'frob': frob or self.get_frob()}
        self._sign_request(data)
        return AUTH_URL + '?' + urllib.urlencode(data)
    
    def get_token(self, frob=None):
        """Convert a (supposedly) authenticated frob into a user auth token.
        
        Will use flickr.frob if one is not supplied.
        
        This method only returns the token. The API call does return a lot
        more data, however. If you want the username, fullname, nsid, etc, you
        should make the API call yourself by:
            
            res = flickr.call('auth.getToken', frob=frob)
            token = res['token']['_content']
        
        Or use the flickr.authorize() method.
        
        See: http://www.flickr.com/services/api/auth.howto.web.html
        See: http://www.flickr.com/services/api/auth.howto.desktop.html
        See: http://www.flickr.com/services/api/flickr.auth.getToken.html
        """
        
        if not frob or self.frob:
            raise ValueError('No frob availible.')
        res = self.call('auth.getToken', frob=frob or self.frob)
        return res['auth']['token']['_content']
    
    def authorize(self, frob=None):
        """Authorize the instance after the user has shaken hands with Flickr.
        Returns the token.
        
        Uses the last retrieved frob if one is not supplied. Automatically
        remembers the token and user info.
        
        See: http://www.flickr.com/services/api/auth.howto.web.html
        See: http://www.flickr.com/services/api/auth.howto.desktop.html
        """
        
        if not frob or self.frob:
            raise ValueError('No frob availible.')
        
        res = self.call('auth.getToken', frob=frob or self.frob)
        self.token = res['auth']['token']['_content']
        self._last_checked_token = self.token
        self._user = res['auth']['user']
        
        return self.token
    
    def _assert_user_properties(self):
        if self.token is None:
            raise ValueError('Token is not set.')
        if self._last_checked_token != self.token:
            res = self.call('auth.checkToken', auth_token=self.token)
            self._user = res.auth.user
            self._last_checked_token = self.token
    
    @property
    def username(self):
        self._assert_user_properties()
        return self._user.username
        
    @property
    def fullname(self):
        self._assert_user_properties()
        return self._user.fullname
                    
    @property
    def nsid(self):
        self._assert_user_properties()
        return self._user.nsid
    
    def _call_photos_getInfo(self, photo_id):
        return self.call('photos.getInfo', photo_id=photo_id)
        

if __name__ == '__main__':
    
    flickr = Flickr()
    
    methods = flickr('reflection.getMethods')
    for method in methods:
        name = method.text
        print name
        filename = 'methods/%s.xml' % name
        if not os.path.exists(filename) or not open(filename).read(1):
            info = flickr.raw_call('reflection.getMethodInfo', method_name=name)
            print info
            print '=' * 80
            print
            open(filename, 'w').write(info)
    
    
    
    
    exit()
    nsid = '24585471@N05'
    flickr = Flickr()
    
    
    frob = '72157621859939455-094639bf91886163-235409' or flickr.get_frob()
    print 'frob    :', frob
    # print flickr.build_desktop_auth_link(frob=frob, perms='write')
    token = '72157621859940537-b999efdd20da1866' or flickr.get_token(frob)
    print 'token   :', token
    
    flickr.token = token
    print 'username:', flickr.username
    print 'fullname:', flickr.fullname
    print 'nsid    :', flickr.nsid
    
    exit()
    
    res = flickr.call('photosets.getList', user_id=flickr.nsid)
    for photoset in res['photosets']['photoset']:
        photoset_id = photoset['id']
        res = flickr.call('photosets.getPhotos', photoset_id=photoset_id)
        for photo in res['photoset']['photo']:
            photo_id = photo['id']
            res = flickr.call('photos.getInfo', photo_id=photo_id)
            title = res['photo']['title']['_content']
            desc = res['photo']['description']['_content']
            
            print title, desc
            # flickr.call('photos.setMeta', photo_id=photo_id, title=desc, description=title)
            # exit()
