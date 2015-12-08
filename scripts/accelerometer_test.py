# Proto
from uasyncio.core import get_event_loop,sleep
from rtb.accelerometer import onboard as a

a.start()
get_event_loop().call_later(5000, a.stream(500))
loop = get_event_loop()
loop.run_forever()