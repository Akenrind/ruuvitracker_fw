from ubinascii import b2a_base64
from hmac import new
from os import urandom
from hashlib import sha256
#import uhashlib

def generate_nonce(length):
	""" Generates a pseudorandom hex string, in a lightweight way """
	if length > 1:
		l = [ x for x in b2a_base64(urandom(length*2)).decode() if x.isalpha() ]
		return (''.join(l))[:length]

def get_auth(data, snonce, key): # snonce ought to be e.g. 16 digits
	""" auth data: cnonce || h(snonce||cnonce||clientid) """
	cnonce = generate_nonce(30)
	msg = snonce+cnonce+data
	dig = new(key, msg=msg.encode('utf-8'), digestmod=sha256).hexdigest()
	return cnonce+dig