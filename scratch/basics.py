import os
from flickr import Flickr
from lxml.etree import tostring
from pprint import pprint
from subprocess import call

key = os.environ.get('FLICKR_KEY')
secret = os.environ.get('FLICKR_SECRET')
if not (key and secret):
    print 'please set FLICKR_KEY and FLICKR_SECRET'
    exit(1)

flickr = Flickr(key, secret, format='json')

if False:
    
    pprint(flickr.test.echo())
    
if True:
    token = flickr.get_request_token('http://localhost')
    print token

    auth_url = flickr.get_auth_url(token)
    print auth_url

    call(['open', auth_url])
    exit()

if False:
    
    oauth_token='oauth_callback_confirmed=true&oauth_token=72157627056318817-bb00258df35ad251&oauth_token_secret=da781ef84d3c5727'
    query = 'oauth_token=72157627056318817-bb00258df35ad251&oauth_verifier=e0fc5846d62d0534'
    oauth_verifier='e0fc5846d62d0534'
    print flickr.get_access_token(oauth_token, oauth_verifier)


if False:
    token = 'fullname=Mike%20Boers&oauth_token=72157627055715565-3ac7ea96a536528a&oauth_token_secret=4770e80867f244c1&user_nsid=24585471%40N05&username=Mike%20Boers'
    flickr = Flickr((key, secret), token, format='json')
    
    for x in flickr.photosets.getPhotos.iter(photoset_id='72157626494298321', per_page=10, format='etree'):
        print x.get('id'), x.get('title')
