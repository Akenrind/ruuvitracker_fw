from auth import get_auth
import rtb
from uasyncio.core import get_event_loop,sleep
from rtb.gps import instance as gps
from rtb.gsm import instance as gsm
from rtb.accelerometer import onboard as accel
import leds

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

class Tracker():
	track_location = True # Location tracking - On by default
	track_state = False # State tracking - off by default
	fixed_state_track = False # Stream state information dynamically or with fixed intervals
	measure_ms = 5000 # Measure interval (5 secs by default)
	stream_ms = 600000 # Stream interval (10 minutes by default)
	verbose = False # Notices enabled/disabled

	maximum_fix_age = 600000 # Do not use fixes that are more than 60 seconds old
	state = None # States: In transit, Idle, Performing operation, Emergency
	loop = None
	rtc = None

	# TODO: These *could* be updated via SMS.
	# Configuration response informs that SMS data or update is coming
	# TODO: OTA update requires micro-SD
	# Connection parameters
	PORT = "9202"
	PROXY_IP = "10.1.1.1" # This information is set by ISP.
	USERNAME = "dna"
	PASSWORD = "wap"
	server_url = "core.focusnet.eu" # root url

	def __init__(self):
		pass

	def start(self):
		self.rtc = pyb.RTC()
		self.rtc.wakeup(1800000, self.wakeup()) # Initially, wake up every 30 minutes
		self.state = "INITIAL"
		rtb.mode = rtb.ACTIVE
		green = leds.Led('green')

		# Make a daily configuration call to see if we must track
		get_event_loop().create_task(gsm.start())
		get_event_loop().run_until_complete(gsm.at_mode_init(save=True)) # Set profile
		get_event_loop().run_until_complete(gsm.at_me_init()) # Obtain parameters for connection, such as CNUM
		if not gsm.READY: # Can't read SIM or something
			self.sleep(gsm.error)
		else:
			get_event_loop().run_until_complete(self.configure()) # Make a configuration call to the server

			if self.track_location:
				green.on()
				# Add streaming coroutine
				get_event_loop().create_task(gps.start())

				get_event_loop().call_later(5000, lambda: get_event_loop().call_soon(gps.set_interval(5000)))
				get_event_loop().call_later(10000, lambda: get_event_loop().call_soon(gps.set_interval(self.measure_ms)))
				get_event_loop().call_later(10000, lambda: get_event_loop().call_soon(gps.fill_buffer(self.measure_ms, self.maximum_fix_age)))

				# Actual streaming
				get_event_loop().call_later(5000, self.stream_location())

			if self.track_state:
				get_event_loop().call_later(5000, self.state_loop(2.8))

				if self.fixed_state_track:
					get_event_loop().call_later(5000, self.stream_state())

		# Run main loop to not suspend
		get_event_loop().call_soon(self.main_loop())

		self.loop = get_event_loop()
		self.loop.run_forever()

	def stop(self):
		pass
		# TODO

	def notice(self, notice):
		""" Ought to be used as a callback """
		pass

	def state_loop(self, threshold):
		while True: #rtb.mode == rtb.ACTIVE:
			if self.track_state:
				if gps.speed < threshold: # Trigger in semi-realtime
					next_state = yield from track.examine_state(20, threshold)

					if not track.fixed_state_track:
						if next_state is not self.state:
							pass # Post state as a Notice
					else:
						self.state = next_state
			yield

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

	def notice(self):
		while self.verbose:
			pass # TODO

	def stream_state(self): # unless non-fixed
		while self.track_state: # and self.fixed_state_track (check in the beginning)
			yield from sleep(self.stream_ms)
			data = '{"state":"%s"}' %(self.time, self.state)
			print(data)
			post = yield from gsm.http_action("POST", self.url("stream"), time=self.timestamp(), data=data, auth=authorize("stream"))
			gsm.at_terminate_http_session()
			gsm.at_disconnect()
			yield

	def stream_location(self):
		while self.track_location:
			yield from sleep(self.stream_ms)	
			coords = gps._buffer[len(gps._buffer)-1] # JSON'd. TODO: 3 last items maybe
			data = '{%s}' %coords
			print(data)
			post = yield from gsm.http_action("POST", self.url("stream"), time=self.timestamp(), data=data, auth=authorize("stream"))
			gsm.at_terminate_http_session()
			gsm.at_disconnect()
			yield

	def configure(self):
		""" Daily configuration call. Make sure that gsm is READY """

		get_event_loop().run_until_complete(gsm.at_connect(self.PROXY_IP, self.USERNAME, self.PASSWORD))
		auth = get_auth(gsm.CNUM, "", b'26485001') # Retrieve a server nonce
		get_event_loop().run_until_complete(gsm.at_start_http_session())
		server_nonce = yield from gsm.http_action("GET", self.url("conf"), time=self.timestamp(), auth=auth) # Retrieve servernonce
		get_event_loop().run_until_complete(gsm.at_terminate_http_session())
		auth = get_auth(gsm.CNUM, server_nonce, b'42849900')

		get_event_loop().run_until_complete(gsm.at_start_http_session())
		conf = yield from gsm.http_action("GET", self.url("conf"), time=self.timestamp(), auth=auth)

		get_event_loop().run_until_complete(gsm.at_terminate_http_session())
		get_event_loop().run_until_complete(gsm.at_disconnect())

		self.track_location = parse_conf("track_location", conf)
		self.track_state = parse_conf("track_state", conf)
		self.measure_ms = parse_conf("measure_interval", conf)
		self.stream_ms = parse_conf("stream_interval", conf)
		self.fixed_state_track = parse_conf("fixed_state_track", conf)
		self.verbose = parse_conf("verbose", conf)

	def sleep(self, cause=""):
		""" Put modules to sleep """
		if cause:
			print("Putting modules to sleep. Cause: %s" %cause)
		rtb.mode = rtb.SLEEP
		# Set GSM slow clock to 1
		gsm.set_slow_clock()
		gsm.sleep()
		red = leds.Led('red')
		red.on()
		#gsm.stop()
		if gps.nofix: # Module running
			gps.sleep()
		pyb.stop() # Remember to enable RTC wakeup

	def standby(self):
		""" Put modules to deep sleep """
		# Stop submodules...?
		#gsm.stop()
		#if gps.nofix:
		#	gps.stop()
		rtb.mode = rtb.STANDBY
		pyb.standby()

	def wakeup(self):
		""" Wakeup callback for RTC """
		rtb.mode = rtb.ACTIVE
		gsm.wakeup()
		gps.wakeup()
		gsm.set_slow_clock(0)

	def examine_state(self, speed_threshold, timeout):
		""" We have triggered this examination and start investigating """
		accel.set_sensitivity(0x01)
		averaged_mt = 0
		averaged_speed = 0
		original_timeout = timeout

		# TODO: GPS speed
		if gps.speed < speed_threshold and not not timeout:
			averaged_mt += accel.mt.x
			averaged_speed += gps.speed
			yield from sleep(self.measure_ms)
			timeout-=1

		accel.set_sensitivity(0x08) # TODO: sdsd
		check = original_timeout-timeout
	
		try:
			averaged_mt /= check
			averaged_speed /= check

			if check >= 10: # Low speed state lasted longer than 10*measure_ms
				if averaged_mt > 0xfd and averaged_speed < 1.0:
					return "STATIONARY"
				else:
					return "OPERATING"
			else:
				return "IN_TRANSIT" # Just traffic lights or something.
		except ZeroDivisionError:
			return "IN_TRANSIT" # TODO: re-check with smaller timeout?

def main():
	t = Tracker()
	t.start()

if __name__ == "__main__":
	main()