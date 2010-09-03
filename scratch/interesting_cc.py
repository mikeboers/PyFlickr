
import datetime

from flickr import Flickr

api = Flickr()

one_day = datetime.timedelta(days=1)
date = datetime.date.today() - one_day

def base58_encode(num):
    alphabet = '123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ'
    base = len(alphabet)
    encoded = []
    while num:
        div, mod = divmod(num, base)
        # print num, div, mod
        encoded.append(alphabet[mod])
        num = int(div)
    return ''.join(reversed(encoded))
    
found = 0
while found < 10:
    photos = None
    while photos is None or int(photos['page']) < int(photos['pages']):
        page = int(photos['page']) + 1 if photos is not None else 1
        photos = api('interestingness.getList', date=str(date), extras='license', page=page)
        for photo in photos:
            if photo['license'] == '0':
                continue
            found += 1
            print 'http://flic.kr/p/' + base58_encode(int(photo['id']))
            continue
            print api('photos.getInfo', photo_id=photo['id']).urls[0].text
    date -= one_day

