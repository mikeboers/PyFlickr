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

flickr = Flickr((key, secret), format='json')


if False:
    req_token, req_token_secret = flickr.get_request_token('http://mikeboers.com')
    print req_token, req_token_secret

    auth_url = flickr.get_auth_url(req_token)
    print auth_url

    call(['open', auth_url])
    exit()

if False:
    
    oauth_token='72157627180244800-cd8b2407a3f5d845'
    oauth_secret='195809aeb7ba9e94'
    oauth_verifier='9d535adf3a4bef3c'
    print flickr.get_access_token(oauth_token, oauth_secret, oauth_verifier)


if True:
    token = '72157627055715565-3ac7ea96a536528a'
    token_secret = '4770e80867f244c1'
    flickr = Flickr((key, secret), (token, token_secret), format='json')
    
    pprint(flickr.not_a_method())