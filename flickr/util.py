
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

def short_url(photo_id):
    return 'http://flic.kr/p/' + base58_encode(int(photo_id))