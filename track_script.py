# TODO: Flow control
# Always run this after boot
# TODO: Causes of sleep:
# No GSM signal (try again within 5 minutes)
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

# get_event_loop().create_task(gps.start())
# We do not really need a timestamp for a config call
# as nonces are enough for authorization

# STEP 2: CONFIGURE

PROXY_IP = "10.1.1.1"
USERNAME = "dna"
PASSWORD = "wap"
#get_event_loop().run_until_complete(gsm.stop()) # Reboot module because of uart T_T
#get_event_loop().run_until_complete(gsm.start(False))
#get_event_loop().create_task(gsm.start(False))
get_event_loop().create_task(gsm.restart_uart())
get_event_loop().run_until_complete(gsm.at_connect(PROXY_IP, USERNAME, PASSWORD)) # If no work, retry
get_event_loop().run_until_complete(gsm.configure_tracker(auth=auth.get_auth(gsm.CNUM, b'42849900')))
get_event_loop().run_until_complete(gsm.at_disconnect())
gsm.set_configuration() # ?? Is this even a function...

# Started 6:16
# Ei saa häiritä muita laitteita
# 1) Lähtee hallilta
# 2) kiihdyttelee ja hidastelee, nvm that.
# 3) Myllytys. Speed: 0.6 - 0.09, Kaikilla accel. akseleilla varmasti eventtejä.
# Jos vaihe kestää yli 30 sekuntia, se on operointi
# Kesti 06;56 - 07:12
# Myös koordinaatit vaihteli
# Tästä pois jos nopeus ensin vähenee (speed loss: finishing operation?) ja sitten nousee.
# Varsinkin jos kiihtyvyydet nyt suuremmat (massa kasvoi)
# Ajaa 40 km/h -> 13.96
# 50 km/h -> 24.38, 24.45
# 07:30 suht stationary

# IF TRACKING ENABLED:
# STEP 3: SET CLOCK
#if not gps._time: # Timestamp has not been obtained within ~ 20 seconds.
# This is normal if the device has been powered off for a long time or if fix is simply lost.
get_event_loop().run_until_complete(gsm.fetch_network_time(False))
time = gsm._network_time
time = gps._time

# By default, switch both tracking features on
# If mode is auto-sleep:
accel.start()
accel.stream() # Not needed in production. Only use for state and mode examination
get_event_loop().create_task(gps.start())
get_event_loop().call_later(5000, lambda: get_event_loop().call_soon(gps.set_interval(5000)))
get_event_loop().call_later(10000, lambda: get_event_loop().call_soon(gps.set_interval(1000)))
get_event_loop().call_later(12000, lambda: get_event_loop().call_soon(gps.fill_buffer(1000, 300000)))
get_event_loop().call_later(12000, lambda: get_event_loop().call_soon(gps.stream(10000)))

loop = get_event_loop()
loop.run_forever()

#get_event_loop().call_later(tracker.auto_sleep())

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