from auth import get_auth
import rtb
from uasyncio.core import get_event_loop,sleep
from rtb.gps import instance as gps
from rtb.gsm import instance as gsm
from rtb.accelerometer import onboard as accel

get_event_loop().run_until_complete(gsm.start())
get_event_loop().run_until_complete(gsm.at_mode_init())
get_event_loop().run_until_complete(gsm.set_flow_control())
get_event_loop().run_until_complete(gsm.at_id_init())

PROXY_IP = "10.1.1.1"
USERNAME = "dna"
PASSWORD = "wap"

get_event_loop().run_until_complete(gsm.fetch_network_time())
get_event_loop().run_until_complete(gsm.at_connect(PROXY_IP, USERNAME, PASSWORD))
get_event_loop().run_until_complete(gsm.configure_tracker(auth=auth.get_auth(gsm._ID, b'42849900')))
get_event_loop().run_until_complete(gsm.at_disconnect())
gsm.set_configuration()

get_event_loop().call_later(8000, lambda: loop.run_until_complete(gsm.at_id()))
get_event_loop().call_later(13000, lambda: loop.run_until_complete(gsm.at_connect()))
loop = get_event_loop()
loop.run_forever()


# If SIM is locked:

# Whenever possible, use a cell phone to turn pin code feature off.
# If you are out of that equipment, use this GSM function.
get_event_loop().run_until_complete(gsm.unlock_sim_pin(1234))
# Replace the code with your real PIN code!