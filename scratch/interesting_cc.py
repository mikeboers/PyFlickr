import os
import datetime
from pprint import pprint

from flickr import Flickr
from flickr.util import *


key = os.environ.get('FLICKR_KEY')
secret = os.environ.get('FLICKR_SECRET')
if not (key and secret):
    print 'please set FLICKR_KEY and FLICKR_SECRET'
    exit(1)

flickr = Flickr((key, secret), format='json')


one_day = datetime.timedelta(days=1)
date = datetime.date.today() - one_day

    
found = 0
while found < 10:
    photos = None
    while photos is None or int(photos['page']) < int(photos['pages']):
        page = int(photos['page']) + 1 if photos is not None else 1
        result = flickr.interestingness.getList(date=str(date), extras='license', page=page)
        pprint(result)
        for photo in result['photos']['photo']:
            if photo['license'] == '0':
                continue
            found += 1
            print short_url(photo['id'])
    date -= one_day

