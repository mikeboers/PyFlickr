import os
from flickr import Flickr
from flickr.util import short_url
from pprint import pprint
from subprocess import call
from wsgiref.simple_server import make_server
import random
import cgi
import datetime


key = os.environ.get('FLICKR_KEY')
secret = os.environ.get('FLICKR_SECRET')
if not (key and secret):
    print 'please set FLICKR_KEY and FLICKR_SECRET'
    exit(1)



flickr = Flickr(key, secret, format='json')

host = 'localhost'
port = random.randint(8000, 9000)
hostname = '%s:%s' % (host, port)

class WSGIApp(object):
    
    def __init__(self):
        self.token = None
        self.flickr = Flickr(key, secret, format='json')
        self.request_token = self.flickr.get_request_token('http://%s/auth_return' % hostname)
        print 'REQUEST TOKEN:', self.request_token
    
    def __call__(self, environ, start):
        func_name = 'do_' + (
            environ.get('PATH_INFO', '').strip('/').replace('/', '__') or
            'index'
        )
        func = getattr(self, func_name, None)
        if not func:
            start('404 Not Found', [])
            return ['Not found.']
        fs = cgi.FieldStorage(environ=environ)
        self.args = args = {}
        for key in fs:
            args[key] = fs.getvalue(key)
        return func(environ, start)
        
    
    def do_index(self, environ, start):
        start('200 OK', [('Content-Type', 'text/html')])
        if not self.token:
            return [
                '''<html><body><a href="%s">Authorize with flickr.</a><br/>''' %
                self.flickr.get_auth_url(self.request_token)
            ]

        return ['''hi''']
    
    def do_interesting(self, environ, start):
        start('200 OK', [('Content-Type', 'text/html')])
        yield '<html><body>'
            
        one_day = datetime.timedelta(days=1)
        date = datetime.date.today()
        limit = int(self.args.get('n', 100))

        found = 0
        while found < limit:
            date -= one_day
            for photo in flickr.interestingness.getList.iter(date=str(date), extras='license', per_page=limit):
                if photo['license'] == '0':
                    continue
                found += 1

                src = 'http://farm%(farm)s.static.flickr.com/%(server)s/%(id)s_%(secret)s_s.jpg' % photo
                url = short_url(photo['id'])
                yield str('<a href="%s"><img src="%s" /></a>' % (url, src))
                
                if found == limit:
                    break
                    
    def do_auth_return(self, environ, start):
        verifier = self.args['oauth_verifier']
        self.token, self.userdata = self.flickr.get_access_token(self.request_token, verifier)
        print 'ACCESS TOKEN:', self.token
        print 'USERDATA:',
        pprint(self.userdata)
        self.flickr = Flickr(key, secret, self.token, format='json')
        start('303 See Other', [('Location', '/recent')])
        return ['']
    
    def do_recent(self, environ, start):
        start('200 OK', [('Content-Type', 'text/html')])
        yield '<html><body>'
        for photo in self.flickr.people.getPhotos.iter(user_id=self.userdata['user_nsid'], per_page=25):
            src = 'http://farm%(farm)s.static.flickr.com/%(server)s/%(id)s_%(secret)s_s.jpg' % photo
            url = short_url(photo['id'])
            yield str('<a href="%s"><img src="%s" /></a>' % (url, src))
        

httpd = make_server(host, port, WSGIApp())
call(['open', 'http://' + hostname])
httpd.serve_forever()
