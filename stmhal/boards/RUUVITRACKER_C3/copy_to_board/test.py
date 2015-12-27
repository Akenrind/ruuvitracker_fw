from auth import get_auth
from logging import Logger
import rtb, pyb
from uasyncio.core import get_event_loop,sleep
from rtb.gsm import instance as gsm
from rtb.gps import instance as gps
from rtb.accelerometer import onboard as accel

PROXY_IP = "10.1.1.1" # This information is set by ISP.
USERNAME = "dna"
PASSWORD = "wap"
port = "9202"
server_url = "core.focusnet.eu" # root url

track_location = True # Location tracking - On by default
track_state = True # State tracking - on by default
fixed_state_track = True # Stream state information dynamically or with fixed intervals
measure_ms = 5000 # Measure interval (5 secs by default)
stream_ms = 30000 # 20sec min #600000 # Stream interval (10 minutes by default)
verbose = False # Notices enabled/disabled

THRESHOLD = 1.0 # Low speed state examination activation
time = None # Timestamp time

stationary = None # Slow speed state

state = "INIT"

def url(server_url, PORT, subaddr):
	return 'http://%s:%s/%s' % (server_url, port, subaddr)

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

def wakeup():
	""" Wakeup callback for RTC """
	#gsm.wakeup()
	gps.wakeup()
	#gsm.set_slow_clock(0)
	gsm.start()
	# TODO: also add RTC wakeup event from accelerometer.

def sleep(cause=""):
	""" Put modules to sleep """
	print("Sleep time.")
	if cause:
		print("Cause: %s" %cause)
	# Set GSM slow clock to 1
	#gsm.set_slow_clock()
	#gsm.sleep()
	gsm.stop()
	if gps.nofix: # Module running
		gps.sleep()
	pyb.stop() # Remember to enable RTC wakeup

def auto_sleep():
	while True:
		if gps.nofix >= 1020000: # if gps.nofix == 0 or # 17 min and no fix / flown over
			sleep("No fix in 17 minutes")
		if track_state and gps.last_fix:
			if gps.last_fix.speed < THRESHOLD:
				next_state = yield from examine_state(20, THRESHOLD+0.5) # check from Blinky
				print("State: %s" %next_state)
				if not fixed_state_track:
					if next_state is not state:
						pass # Post state as a Notice
				else:
					state = next_state
					
		yield
		# TODO: State is stationary for more than 30 minutes (sleep & accel external interrupt)
		# (Accelerometer rtc check)
		# TODO: gps 'today'

def timestamp():
	""" Prefer GPS time over GSM network time """
	if not gps.last_fix:
		time = gsm.dt
	else:
		time = gps.last_fix.dt
	if time:
		time.update_rtc()
	else:
		return "no_timestamp" # Can't connect to network and can't get GPS fix. Sad.
	return time.__repr__()

def stream(stream_ms):
	while True:
		yield from sleep(stream_ms)
		print("Authorizing...")
		auth = get_auth(gsm.CNUM, "", b'26485001')
		get_event_loop().call_soon(gsm.at_connect(PROXY_IP, USERNAME, PASSWORD))
		print("Preauth: %s" %auth)
		print("Initializing HTTP session...")
		get_event_loop().call_soon(gsm.start_http_session(PROXY_IP))
		print("Retrieving server nonce...")
		get_event_loop().call_soon(gsm.start_http_session(PROXY_IP))
		server_nonce = yield from gsm.http_action("GET", url(server_url, port, "stream"), time=timestamp(), auth=auth)
		print("Possible server nonce: %s" %server_nonce[:])
		if server_nonce and not "CME" in server_nonce:
			print("Succesfully obtained server nonce %s" %server_nonce)
			auth = get_auth(gsm.CNUM, server_nonce, b'42849900')
		else:
			print("Unable to obtain server nonce")

		print("Stopping.")
		get_event_loop().call_soon(gsm.terminate_http_session())

		print("Running production authorization.")
		coords = "test"
		state = "test"
		data = '{"auth":%s, %s, ' %(auth, coords)
		if track_state:
			data += '"state":%s, ' %state
		data += '"time":%s}' %(timestamp())
		print(data)
		print("Posting location data...")

		get_event_loop().call_soon(gsm.start_http_session(PROXY_IP))
		post = yield from gsm.http_action("POST", url(server_url, port, "stream"), data=data)
		get_event_loop().call_soon(gsm.terminate_http_session())
		get_event_loop().call_soon(gsm.at_disconnect())
		#get_event_loop().call_soon(gsm.stop()) # TODO: Should we start & Stop?

def configure():
	get_event_loop().run_until_complete(gsm.at_connect(PROXY_IP, USERNAME, PASSWORD))
	auth = get_auth(gsm.CNUM, "", b'26485001')
	get_event_loop().run_until_complete(gsm.start_http_session(PROXY_IP))
	server_nonce = yield from gsm.http_action("GET", url(server_url, port, "conf"), time=timestamp(), auth=auth)
	get_event_loop().run_until_complete(gsm.terminate_http_session())
	auth = get_auth(gsm.CNUM, server_nonce, b'42849900')

	get_event_loop().run_until_complete(gsm.start_http_session(PROXY_IP))
	conf = yield from gsm.http_action("GET", url(server_url, port, "conf"), time=timestamp(), auth=auth)

	get_event_loop().run_until_complete(gsm.terminate_http_session())
	get_event_loop().run_until_complete(gsm.at_disconnect())

	# Parse configuration settings
	if conf:
		track_location = parse_conf("track_location", conf)
		track_state = parse_conf("track_state", conf)
		measure_ms = parse_conf("measure_interval", conf)
		stream_ms = parse_conf("stream_interval", conf)
		fixed_state_track = parse_conf("fixed_state_track", conf)
		verbose = parse_conf("verbose", conf)

#rtc = pyb.RTC()
#rtc.wakeup(1800000, wakeup()) # Initially, wake up every 30 minutes (maximum is 131000ms, about 2 hours)
# TODO: schedule reboot (gps today)
maximum_fix_age = 600000
maximum_fix_age = stream_ms if maximum_fix_age >= stream_ms else maximum_fix_age

#get_event_loop().create_task(gsm.start())
#get_event_loop().run_until_complete(gsm.at_mode_init())
#get_event_loop().run_until_complete(gsm.add_callbacks())
#get_event_loop().run_until_complete(configure())
#get_event_loop().call_later(10000, lambda: get_event_loop().call_soon(gsm.at_me_init()))
#get_event_loop().call_later(10000, lambda: get_event_loop().call_soon(stream(stream_ms)))

# TODO: only power on when the rest is asleep or if examination triggered
#accel.start()
# TODO: investigate memory leak...
#accel.set_sensitivity(0x01) # Set sensitivity
#accel.conf_mt()
#accel.set_fast_read(True) # 8-bit results

get_event_loop().create_task(gps.start())
get_event_loop().call_later(5000, lambda: get_event_loop().call_soon(gps.set_interval(5000)))
get_event_loop().call_later(10000, lambda: get_event_loop().call_soon(gps.set_interval(1000)))
get_event_loop().call_later(10000, lambda: get_event_loop().call_soon(gps.fill_buffer(measure_ms, maximum_fix_age)))
get_event_loop().call_later(15000, lambda: get_event_loop().call_soon(auto_sleep()))

loop = get_event_loop()
loop.run_forever()

def examine_state(speed_threshold, timeout):
	""" We have triggered this examination and start investigating """
	averaged_mt = 0
	averaged_speed = 0
	original_timeout = timeout

	if gps.last_fix.speed < speed_threshold and timeout:
		#averaged_mt += int(accel.stream()[3:5]) #accel.mt.x # TODO: buffer
		averaged_speed += gps.last_fix.speed
		yield from sleep(1000)
		timeout-=1

	check = original_timeout-timeout
	#try:
		#averaged_mt /= check
	if check > 0:
		a = (float) averaged_speed / check # Floating point math eats up all RAM...

		if check >= 10: # Low speed state lasted longer than 10*measure_ms
			if a < 1.0: # averaged_mt > 0xfd and 
				return "STATIONARY"
			else:
				return "OPERATING"
		else:
			return "IN_TRANSIT" # Just traffic lights or something
#except ZeroDivisionError:
	return "IN_TRANSIT" # TODO: re-check with smaller timeout?
