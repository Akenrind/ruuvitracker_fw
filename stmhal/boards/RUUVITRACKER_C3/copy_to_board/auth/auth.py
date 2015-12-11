import binascii, os
import hmac
from hashlib.sha256 import sha256

def generate_nonce(length):
	""" Generates a 30 digit hex string, in a lightweight way """
	if length > 1 and length%2 == 0:
		return binascii.b2a_hex(os.urandom(length/2))

def get_auth(data, snonce, key): # snonce ought to be e.g. 8 digits
	""" auth data: cnonce || h(snonce||cnonce||clientid) """
	cnonce = generate_nonce(30)
	dig = hmac.new(key, msg=snonce+cnonce+data, digestmod=sha256).hexdigest()
	return cnonce+data