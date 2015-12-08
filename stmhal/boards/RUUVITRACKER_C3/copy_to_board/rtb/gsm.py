import pyb
import rtb
import uartparser
from uasyncio.core import get_event_loop, sleep

# TODO: This thing needs a proper state machine to keep track of the sleep modes

PORT = "9202"
PROXY_IP = "10.1.1.1" # Set by ISP
USERNAME = "dna"
PASSWORD = "wap"
server_url = "core.focusnet.eu" # root url

class GSM:
	uart_wrapper = None # Low-Level UART
	uart = None # This is the parser
	error = None # CME error

	ID = None
	network_time = None

	def __init__(self):
		pass

	def start(self):
		# Try without flow control first
		self.uart_wrapper = uartparser.UART_with_fileno(rtb.GSM_UART_N, 115200, read_buf_len=256)
		#self.uart_wrapper = uartparser.UART_with_fileno(rtb.GSM_UART_N, 115200, read_buf_len=256, flow=pyb.UART.RTS | pyb.UART.CTS)
		# TODO: schedule something that will reset the board to autobauding mode if it had not initialized within X seconds
		self.uart = uartparser.UARTParser(self.uart_wrapper)

		self.uart.add_line_callback('raw', None, None, self.uart.urc.save_line)
		
		self.uart.urc.add_event('+CNUM', self.obtain_num)
		self.uart.urc.add_event('PSUTTZ', self.obtain_time)
		#self.uart.urc.add_event('+HTTPDATA', self.obtain_data)

		# The parsers start method is a generator so it's called like this
		get_event_loop().create_task(self.uart.start())

		# Power on
		rtb.pwr.GSM_VBAT.request()
		yield from self.push_powerbutton()
		# Assert DTR to enable module UART (we can also sample the DTR pin to see if the module is powered on)
		rtb.GSM_DTR_PIN.low()

		# Just to keep consistent API, make this a coroutine too
		self.set_flow_control()
		yield from self.at_id()

	def push_powerbutton(self, push_time=2000):
		rtb.GSM_PWR_PIN.low()
		yield from sleep(push_time)
		rtb.GSM_PWR_PIN.high()

	def at_mode_init(self):
		# Make sure autobauding autobauds
		resp = yield from self.uart.cmd("AT")
		# Echo off
		resp = yield from self.uart.cmd("ATE0")
		# Set fixed baudrate
		resp = yield from self.uart.cmd("AT+IPR=115200")
		# Network registration messages enable
		resp = yield from self.uart.cmd("AT+CREG=2")

	def sleep():
		"""Put module to sleep. This assumes slow-clock is set to 1"""
		rtb.GSM_DTR_PIN.high()

	def wakeup():
		"""Wake up from sleep. This assumes slow-clock is set to 1"""
		rtb.GSM_DTR_PIN.low()
		# The serial port is ready after 50ms
		yield from sleep(50)

	def set_slow_clock(mode=1):
		"""Sets slow-clock mode, 1 is recommended, DTR controls sleep mode then"""
		resp = yield from self.uart.cmd("AT+CSCLK=%d" % mode)

	def set_flow_control(value=True):
		"""Enables/disables RTS/CTS flow control on the module and UART"""
		if value:
		    resp = yield from self.uart.cmd("AT+IFC=2,2")
		    self.uart_wrapper.init(115200, read_buf_len=256, flow=pyb.UART.RTS | pyb.UART.CTS)
		else:
		    resp = yield from self.uart.cmd("AT+IFC=0,0")
		    self.uart_wrapper.init(115200, read_buf_len=256, flow=0)


		# TODO: Autobauding -> set baud and flow control (rmember to reinit the UART...)
		# TODO: Add GSM command methods (putting the module to various sleep modes etc)
		# TODO: Add possibility to attach callbacks to SMS received etc

	def at_test(self):
		yield from self.execute_cmd('AT')

	def at_id(self):
		# Wait 7 seconds after fresh boot
		yield from sleep(7000)
		yield from self.execute_cmd('AT')
		# Init network time. Takes a while.
		yield from self.execute_cmd("AT+CLTS=1", urc="PSUTTZ")

		# Obtain phone number for ID
		yield from sleep(2000)
		yield from self.execute_cmd('AT+CNUM', wait="3000")

		# Is there GPRS context attached
		yield from self.execute_cmd('AT+CGATT?')

		# Is SIM inserted and ready?
		yield from self.execute_cmd('AT+CPIN?')

	def at_connect(self):
		# Can only be done if CPIN is ready.
		yield from self.uart.cmd("AT+CIPSHUT")
		yield from self.execute_cmd('AT+CIPSTATUS')

		yield from self.execute_cmd('AT+CGDCONT=1,"IP","%s"' %(PROXY_IP))
		yield from self.execute_cmd('AT+CIPMUX=0') # Set up single connection mode

		# Attach GPRS
		yield from self.execute_cmd("AT+CGATT=1")

		yield from self.execute_cmd('AT+CSTT="%s", "%s", "%s"' %(PROXY_IP, USERNAME, PASSWORD))
		yield from self.execute_cmd('AT+CIICR')

		yield from sleep(5000)
		yield from self.execute_cmd('AT+CIFSR') # Local IP get, might be mandatory?
		# TODO: is this even necessary T_T
		#yield from self.execute_cmd('AT+CIPSTART="TCP","%s","%s"' %(server_url, PORT)) #/test/state/

	def at_post(self, data, subaddr):

		size = len(data.encode('utf-8'))

		yield from self.execute_cmd('AT+HTTPINIT') # Init HTTP service

		yield from self.execute_cmd('AT+SAPBR=3,1,"CONTYPE","GPRS"')
		yield from self.execute_cmd('AT+SAPBR=3,1,"APN","%s"' %(PROXY_IP))
		yield from self.execute_cmd('AT+SAPBR=1,1')

		# Set HTTP params
		yield from self.execute_cmd('AT+HTTPPARA="CID",1')
		yield from self.execute_cmd('AT+HTTPPARA="URL","http://%s:%s/%s"' %(server_url, PORT, subaddr))
		#yield from self.execute_cmd('AT+HTTPPARA="URL","http://%s:%s/"' %(server_url, PORT))
		yield from self.execute_cmd('AT+HTTPDATA=%s,5000' %(size))
		yield from self.execute_cmd(data)

		yield from self.execute_cmd('AT+HTTPACTION=1') # POST
		yield from sleep(5000)
		yield from self.execute_cmd('AT+HTTPREAD')
		yield from sleep(2000)
		yield from self.execute_cmd('AT+HTTPTERM')

	def execute_cmd(self, cmd, *param, **kw_params):
		""" Command execution wrapper """
		cmd = yield from self.uart.cmd(cmd)
		urc = None
		if('urc' in kw_params):
			urc = kw_params['urc']

		resp = yield from self.uart.urc.retrieve_response(cmd, urc, 500)

	def configure_tracker(self, *args, **kwargs):
		yield from self.at_get("conf", *args, **kwargs)

	def at_get(self, subaddr, *args, **kwargs):
		url = '"http://%s:%s/%s?' % (server_url, PORT, subaddr)

		for x in kwargs:
			url += "%s=%s&" % (x, kwargs[x])

		self._time = "test"
		url += "time=%s" % self._time
		url += '"'
		print("Destination url: %s" %url)

		yield from self.execute_cmd('AT+HTTPINIT') # Init HTTP service
		yield from self.execute_cmd('AT+SAPBR=3,1,"CONTYPE","GPRS"')
		yield from self.execute_cmd('AT+SAPBR=3,1,"APN","%s"' %(PROXY_IP))
		yield from self.execute_cmd('AT+SAPBR=1,1')

		yield from self.execute_cmd('AT+HTTPPARA="CID",1')
		yield from self.execute_cmd('AT+HTTPPARA="URL",%s' %url)

		yield from sleep(2000)

		yield from self.execute_cmd('AT+HTTPACTION=0') # GET
		yield from sleep(5000)
		yield from self.execute_cmd('AT+HTTPREAD')
		yield from sleep(2000)
		yield from self.execute_cmd('AT+HTTPTERM')

	def at_disconnect(self):
		yield from self.execute_cmd('AT+SAPBR=0,1') # Close GPRS context
		yield from self.execute_cmd('AT+CIPCLOSE') # Shut down connections
		yield from self.execute_cmd('AT+CIPSHUT') # Shut down connections
		yield from self.execute_cmd('AT+CGATT=0') # Detach GPRS

	def obtain_num(self, line):
		self._ID = line
		return True

	def obtain_time(self, line):
		self.network_time = line
		return True

	def obtain_data(self, line):
		self.configuration = line
		return True

	def stop(self):
		self.uart.del_line_callback('raw')
		yield from self.push_powerbutton()
		yield from self.uart.stop()
		self.uart_wrapper.deinit()
		# de-assert DTR
		rtb.GSM_DTR_PIN.high()
		rtb.pwr.GSM_VBAT.release()

instance = GSM()
