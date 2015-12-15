# TODO: Flow control
# Always run this after boot
# TODO: Causes of sleep:
# CME error: SIM is locked
# CME error: SIM is not inserted
# (^ Hard-coded sleep time, eg. 15 minutes.)
# Fix was lost for more than 10 minutes and state tracking is not on
# Only wake up if accelerometer detects movement (interrupt)
# TODO: Causes of wakeup:
# Accelerometer sees that we are on the move. External interrupt.
# TODO: Auto-sleep configuration (with configuration call if it is provided):
# Sleep if fix was lost for more than: <10 minutes>
# Sleep between measurement intervals (only supported if measure interval is more than 30 seconds)
# Just sleep (do not track). Completely disables tracking.
# MODE: auto-sleep, sleep
# State is different... 0, 1, 2: none, fixed, dynamic

# STEP 1: INIT
from auth import get_auth
import rtb
from uasyncio.core import get_event_loop,sleep
from rtb.gps import instance as gps
from rtb.gsm import instance as gsm
from rtb.accelerometer import onboard as accel

get_event_loop().create_task(gsm.start())
get_event_loop().run_until_complete(gsm.at_id_init())

get_event_loop().create_task(gps.start())

# We do not really need a timestamp for a config call
# as nonces are enough for authorization

# STEP 2: CONFIGURE

PROXY_IP = "10.1.1.1"
USERNAME = "dna"
PASSWORD = "wap"

get_event_loop().run_until_complete(gsm.at_connect(PROXY_IP, USERNAME, PASSWORD))
get_event_loop().run_until_complete(gsm.configure_tracker(auth=auth.get_auth(gsm.CNUM, b'42849900')))
get_event_loop().run_until_complete(gsm.at_disconnect())
gsm.set_configuration() # ?? Is this even a function...

# IF TRACKING ENABLED:
# STEP 3: SET CLOCK
#if not gps._time: # Timestamp has not been obtained within ~ 20 seconds.
# This is normal if the device has been powered off for a long time or if fix is simply lost.
get_event_loop().run_until_complete(gsm.fetch_network_time())
time = gsm._network_time
time = gps._time

# By default, switch both tracking features on
# If mode is auto-sleep:
get_event_loop().call_later(5000, lambda: get_event_loop().call_soon(gps.set_interval(5000)))
get_event_loop().call_later(10000, lambda: get_event_loop().call_soon(gps.set_interval(1000)))
get_event_loop().call_later(10000, gps.stream(600000))
get_event_loop().call_later(8000, a.stream(600000))
get_event_loop().call_later(tracker.auto_sleep())

#get_event_loop().call_later(8000, lambda: loop.run_until_complete(gsm.at_id()))
#get_event_loop().call_later(13000, lambda: loop.run_until_complete(gsm.at_connect()))
loop = get_event_loop()
loop.run_forever()

get_event_loop().run_until_complete(gps.stop())
get_event_loop().run_until_complete(gsm.stop())
get_event_loop().run_until_complete(a.stop())

# If SIM is locked:
# Whenever possible, use a cell phone to turn pin code feature off.
# If you are out of that equipment, use this GSM function.
get_event_loop().run_until_complete(gsm.unlock_sim_pin(1234))
# Replace the code with your real PIN code!