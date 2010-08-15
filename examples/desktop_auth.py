
from subprocess import call

import flickr

api = flickr.Flickr()

link = api.build_desktop_auth_link('read')
print 'link:', link

call(['open', link])

print 'When you have authorized the link, hit return.',
raw_input()

token = api.authorize()
print 'token:', api.token
print 'user:', api._user