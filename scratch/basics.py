import os
from flickr import Flickr
from lxml.etree import tostring
from pprint import pprint

key = os.environ.get('FLICKR_KEY')
secret = os.environ.get('FLICKR_SECRET')
if not (key and secret):
    print 'please set FLICKR_KEY and FLICKR_SECRET'
    exit(1)

flickr = Flickr((key, secret), format='json')


res = flickr.photosets.getList(user_id='24585471@N05')
pprint(res)