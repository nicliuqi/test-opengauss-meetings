from django.conf import settings
from Crypto.Cipher import AES
from binascii import a2b_hex, b2a_hex


key = settings.SECRET_KEY[:16].encode('utf-8')

def add_to_16(text):
    if len(text.encode('utf-8')) % 16:
        add = 16 - len(text.encode('utf-8')) % 16
    else:
        add = 0
    text = text + ('\0' * add)
    return text.encode('utf-8')


def encrypt(text, iv):
    mode = AES.MODE_CBC
    text = add_to_16(text)
    cryptos = AES.new(key, mode, iv)
    cipher_text = cryptos.encrypt(text)
    return b2a_hex(cipher_text).decode('utf-8')


def decrypt(text, iv):
    mode = AES.MODE_CBC
    cryptos = AES.new(key, mode, iv)
    plain_text = cryptos.decrypt(a2b_hex(text.encode('utf-8')))
    return bytes.decode(plain_text).rstrip('\0')
