#-*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
import httplib
from zato.server.service import Service
from .digest import compare_digest
import string
from urlparse import parse_qs
import time
from os import urandom

# Digest comparison, since HMAC compare digest is apparently not supported in Python 2.7 by default...
# Originally from  https://github.com/django/django/blob/master/django/utils/crypto.py#L80
def compare_digest_tmp(val1, val2):
	#if hasattr(hmac, "compare_digest"):
    		# Prefer the stdlib implementation, when available.
    	#	def constant_time_compare(val1, val2):
        		#return hmac.compare_digest(force_bytes(val1), force_bytes(val2))
	#def constant_time_compare(val1, val2):
	"""
	Returns True if the two strings are equal, False otherwise.
	The time taken is independent of the number of characters that match.
	For the sake of simplicity, this function executes in constant time only
	when the two strings have the same length. It short-circuits when they
	have different lengths. Since Django only uses it to compare hashes of
	known expected length, this is acceptable.
	"""
	if len(val1) != len(val2):
		return False
	result = 0
	
	if isinstance(val1, bytes) and isinstance(val2, bytes):
		for x, y in zip(val1, val2):
			result |= x ^ y
	else:
		for x, y in zip(val1, val2):
			result |= ord(x) ^ ord(y)
	return result == 0

def GenNonce(length):
	return sha1(str(urandom())).hexdigest()[:length]
	
class Stream(Service):
    def handle(self):
        self.logger.info(type(self.request.raw_request))
        self.logger.info(self.request.raw_request)
		self.response.status_code = httplib.UNAUTHORIZED
		self.response.payload = GenNonce(8) # Return server nonce that will be consumed in the next call
	
		qs = parse_qs(self.wsgi_environ['QUERY_STRING'])
		if qs and "auth" in str(qs):
			a = str(qs['auth'])
			a = a[2:-2] # Remove [' ']
			# TODO: In reality, invoke database and digest with nonces.
			client = 'afa51b4aacb42c3c3906057b9c47141b70ce600a4723b08e13cbd7457d7ad3d4'
			if compare_digest(a, client):
				self.response.status_code = httplib.OK
				# Authentication is validated - save to database.
				self.logger.info("Authentication validated.")
				self.logger.info(self.request.payload)

    def finalize_handle(self):
    	self.log_output('Output:', logging.DEBUG,
            ['wsgi_environ', 'name', 'impl_name'])