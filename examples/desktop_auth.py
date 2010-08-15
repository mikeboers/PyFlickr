
from subprocess import call

import flickr

api = flickr.Flickr()

frob = api.get_frob()
print 'frob:', frob

link = api.build_desktop_auth_link('read', frob)
print 'link:', link

call(['open', link])

print 'When you have authorized the link, hit return.',
raw_input()

token = api.get_token()
print 'token:', token