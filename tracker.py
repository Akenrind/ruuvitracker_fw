# Proto
from auth import get_auth
import rtb
from uasyncio.core import get_event_loop,sleep
from rtb.gps import instance as gps
from rtb.gsm import instance as gsm
from rtb.accelerometer import onboard as accel

def main():
	t = Tracker()

	# add main loop to loop
	#t.loop = get_event_loop()
	#t.loop.run_forever()

if __name__ = "__main__":
	main()

# Dummy function because we are seriously running out of space
def parse_conf(keyword, data):
	""" Dummy JSON parser, returns a value for key """
	BACKSLASH = r'\n\r\t'
	found = False
	data.split(",")
	for line in data:
		if keyword in line:
			found = True
			a = line.split(":")
			for c in a[1]:
				if c in BACKSLASH:
					a[1].replace(c,'')
			return a[1]

def main_loop(track):
	""" Semi-realtime main loop """
	while True:
		if track.mode == "ACTIVE":

			# TODO: iterate over stream responsibilities
			if track.track_state:
				if gps.speed < 0.05: # Trigger in semi-realtime
					new_state = yield from track.examine_state(20)

					if not track.fixed_state_track:
						if next_state is not self.state:
							pass # Post state as a Notice
					else:
						track.state = new_state

			#if track.track_location:
			# Add this to loop
			#	gps.fill_buffer(track.measure_ms, track.maximum_fix_age)

			# Call back with notice
			if track.verbose:
				if gps._notice:
					# Post notice
					gps._notice = None

		else:
			pass # Enter sleep/standby state -> put slow clock on, enable interrupts, etc.
		yield

class Tracker():
	mode = None # Modes: sleep, standby, active
	track_location = True # Location tracking - On by default
	track_state = False # State tracking
	fixed_state_track = False # Stream state information dynamically or with fixed intervals
	measure_ms = None # Measure interval
	stream_ms = None # Stream interval
	verbose = False # Notices enabled/disabled

	maximum_fix_age = 600000 # Do not use fixes that are more than 60 seconds old
	state = None # States: In transit, Idle, Performing operation, Emergency
	loop = None

	# TODO: These *could* be updated via SMS
	PORT = "9202"
	PROXY_IP = "10.1.1.1" # This information is set by ISP.
	USERNAME = "dna"
	PASSWORD = "wap"
	server_url = "core.focusnet.eu" # root url

	def __init__(self):
		self.state = "INITIAL"

    def start(self):
		# Check time
		# get_event_loop().run_until_complete(gsm.at_connect())

	def url(self, subaddr):
		return 'http://%s:%s/%s' % (self.server_url, self.PORT, subaddr)

	def timestamp(self):
		""" Prefer GPS time over GSM network time """
		if not gps.time:
			return gsm.fetch_network_time() # No ZZ time
		else:
			return gps.fetch_time()

	def authorize(self, subaddr):
		gsm.at_connect(self.PROXY_IP, self.USERNAME, self.PASSWORD)
		auth = get_auth(gsm.CNUM, "", b'26485001') # Retrieve a server nonce
		self.at_start_http_session()
		server_nonce = yield from self.http_action("GET", self.url(subaddr), time=self.timestamp(), auth=auth) # Retrieve servernonce
		auth = get_auth(gsm.CNUM, server_nonce, b'42849900')

		return auth

	def stream(self):
		yield from sleep(self.stream_ms)	
		coords = gps._buffer(len(gps._buffer)) # JSON'd. TODO: 3 last items maybe?
		data = '{%s}' %coords
		post = yield from self.http_action("POST", self.url("stream"), time=self.timestamp(), data=data, auth=authorize("stream"))
		self.at_terminate_http_session()
		self.at_disconnect()

	def configure(self):
		""" Daily configuration call. gsm.at_id() must be performed, as well as at_connect """

		gsm.at_connect(self.PROXY_IP, self.USERNAME, self.PASSWORD)
		auth = get_auth(gsm.CNUM, "", b'26485001') # Retrieve a server nonce
		# urc add event "CONNECT OK"
		self.at_start_http_session()
		server_nonce = yield from self.http_action("GET", self.url("conf"), time=self.timestamp(), auth=auth) # Retrieve servernonce

		auth = get_auth(gsm.CNUM, server_nonce, b'42849900')
		# urc event del and if everything worked out fine,
		# Obtain configuration
		conf = yield from self.http_action("GET", self.url("conf"), time=self.timestamp(), auth=auth)

		self.at_terminate_http_session() # TODO: folded with individual requests or like this?

		self.at_disconnect()

		self.track_location = parse_conf("track_location", conf)
		self.track_state = parse_conf("track_state", conf)
		self.measure_ms = parse_conf("measure_interval", conf)
		self.stream_ms = parse_conf("stream_interval", conf)
		self.fixed_state_track = = parse_conf("fixed_state_track", conf)
		self.verbose = parse_conf("verbose", conf)

	def sleep(self):
		""" Put modules to sleep """
		# Set GSM slow clock to 1

	def wakeup(self):
		gsm.wakeup()
		gps.wakeup()

	def examine_state(self, timeout):
		""" We have triggered this examination and start investigating """
		# TODO: SET STANDBY MODE to enable config to the function exhibit
		# TODO: Only wake up if triggered
		accel.set_sensitivity(0x00) # Veeery sensitive

		if gps.speed < 0.05 and not not timeout:
			averaged_mt += accel.mt.x
			yield from sleep(1000)
			timeout-=1

		accel.set_sensitivity(0x08) # TODO: What do we even need this mode for...?
		
		try:
			averaged_mt /= (20-timeout)

			if check >= 10: # Low speed state lasted longer than 10 seconds
				if averaged_mt > 0xfd:
					return "STATIONARY"
				else:
					return "OPERATING" # Or... in a traffic jam...?
			else:
				return "IN_TRANSIT" # Just traffic lights or something.
		except ZeroDivisionError:
			return "IN_TRANSIT" # TODO: re-check with smaller timeout?