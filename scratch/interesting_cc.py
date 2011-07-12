import os
import sys
import datetime
from pprint import pprint
import logging

logging.basicConfig(file=sys.stderr, level=logging.DEBUG)

from flickr import Flickr
from flickr.util import *


key = os.environ.get('FLICKR_KEY')
secret = os.environ.get('FLICKR_SECRET')
if not (key and secret):
    print 'please set FLICKR_KEY and FLICKR_SECRET'
    exit(1)

flickr = Flickr((key, secret), format='json', echo=True)


one_day = datetime.timedelta(days=1)
date = datetime.date.today()

    
found = 0
while found < 10:
    date -= one_day
    print '---', date
    for photo in flickr.interestingness.getList.iter(date=str(date), extras='license', per_page=10):
        if photo['license'] == '0':
            continue
        found += 1
        print found, short_url(photo['id'])
        if found == 10:
            break

