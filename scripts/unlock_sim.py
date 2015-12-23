### Do not use this script
### Always prefer cell phones over this script when switching SIM PIN query off

import rtb
from uasyncio.core import get_event_loop,sleep
from rtb.gsm import instance as gsm
rtb.pwr.GSM_VBAT.status()

get_event_loop().create_task(gsm.start())
get_event_loop().run_until_complete(gsm.at_mode_init())
get_event_loop().run_until_complete(lambda x: get_event_loop().call_soon(lambda l: yield from sleep(8000)))
get_event_loop().run_until_complete(gsm.unlock_sim_pin(code)) # <- Replace 'code' with SIM pin
get_event_loop().run_until_complete(gsm.stop())