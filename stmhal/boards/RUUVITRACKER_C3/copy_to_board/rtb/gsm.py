import pyb
import rtb
import uartparser
from uasyncio.core import get_event_loop, sleep

# TODO: This thing needs a proper state machine to keep track of the sleep modes
# NOTE: tracker.py keeps track of the sleep modes.

GET=0
POST=1
HEAD=2

class GSM:
	uart_wrapper = None # Low-Level UART
	uart = None # This is the parser

	error = None # CME error
	network_time = None # Indicates whether network time has been fetched, NOT updated in real-time
	CNUM = None # Subscriber number

	CGATT = False # GPRS context attached
	CPIN = False # PIN inserted / ready
	PDP = False # GPRS PDP context

	def __init__(self):
		pass

	def start(self):
		# Try without flow control first
		self.uart_wrapper = uartparser.UART_with_fileno(rtb.GSM_UART_N, 115200, read_buf_len=256)
		#self.uart_wrapper = uartparser.UART_with_fileno(rtb.GSM_UART_N, 115200, read_buf_len=256, flow=pyb.UART.RTS | pyb.UART.CTS)
		# TODO: schedule something that will reset the board to autobauding mode if it had not initialized within X seconds
		self.uart = uartparser.UARTParser(self.uart_wrapper)

		#self.uart.add_line_callback('sms', 'startswith', '+CTS', self.SMS_receive)
		self.uart.add_line_callback('urc', None, None, self.uart.urc.parse_urc)
		# Network time fetch will have a special callback because execution takes a LONG time
		self.uart.urc._events.append('PSUTTZ')
		self.uart.urc._events.append('HTTPREAD')

		# The parsers start method is a generator so it's called like this
		get_event_loop().create_task(self.uart.start())

		# Power on
		rtb.pwr.GSM_VBAT.request()
		yield from self.push_powerbutton()
		# Assert DTR to enable module UART (we can also sample the DTR pin to see if the module is powered on)
		rtb.GSM_DTR_PIN.low()

		# Just to keep consistent API, make this a coroutine too
		yield

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

	def at_sms_init(self):
		# Use Text mode with SMS
		yield from self.uart.cmd('AT+CMGF=1')
		# Indicate with CMTI
		yield from self.uart.cmd('AT+CNMI=1,2,0,0,0')

	# TODO: Add GSM command methods (putting the module to various sleep modes etc)

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

	# TODO: Autobauding -> set baud and flow control (rmember to reinit the UART...)
	def set_flow_control(value=True):
		"""Enables/disables RTS/CTS flow control on the module and UART"""
		if value:
		    resp = yield from self.uart.cmd("AT+IFC=2,2")
		    self.uart_wrapper.init(115200, read_buf_len=256, flow=pyb.UART.RTS | pyb.UART.CTS)
		else:
		    resp = yield from self.uart.cmd("AT+IFC=0,0")
		    self.uart_wrapper.init(115200, read_buf_len=256, flow=0)

	def at_test(self):
		yield from self.uart.cmd('AT')

	def fetch_network_time(self):
		""" Use GSM network time as a timestamp """
		if not self.network_time:
			self.uart.urc.OVERRIDE = True # Data must be raw
			self.network_time = yield from self.retrieve_urc("AT+CLTS=1", urc="PSUTTZ", index=1)
		else: # Network time has been fetched at least once, and CCLK is local time. TODO: indicate.
			self.network_time = yield from self.retrieve_urc("AT+CCLK") # This is local time

		self.uart.urc.OVERRIDE = False
		return self.network_time

	def at_id_init(self):
		# Obtain subscriber number for 'client ID'
		self.CNUM = yield from self.retrieve_urc('AT+CNUM', index=1, timeout=2000)

		# TODO: Why??
		#attached = yield from self.retrieve_urc('AT+CGATT?')
		#self.CGATT = '1' in attached
		#if self.CGATT:
		#	yield from self.uart.cmd('AT+CGATT=0') # Detach GPRS

	def at_ready(self):
		ready = yield from self.retrieve_urc('AT+CPIN?')
		self.CPIN = 'READY' in ready
		return self.CPIN

	def at_connect(self, PROXY_IP, USERNAME, PASSWORD):
		""" Connects to GPRS proxy server. Connection may only be carried out if CPIN is ready """
		if self.at_ready():
			# Query connection status
			status = yield from self.retrieve_urc('AT+CIPSTATUS', urc='STATE')
			if int(status):
				# Close all previous IP sessions
				self.uart.cmd("AT+CIPSHUT")

			# Define PDP context
			pdp = yield from self.uart.cmd('AT+CGDCONT=1,"IP","%s"' %(PROXY_IP))
			self.PDP = not 'ERROR' in pdp
			# Set up single connection mode
			yield from self.uart.cmd('AT+CIPMUX=0')
			# Attach GPRS
			attached = yield from self.retrieve_urc("AT+CGATT=1")
			self.CGATT = '1' in attached

			if self.CGATT and self.PDP:
				# Start task and set APN, user name and password
				yield from self.uart.cmd('AT+CSTT="%s", "%s", "%s"' %(PROXY_IP, USERNAME, PASSWORD))
				# Bring up the wireless. This takes a while.
				error = yield from self.retrieve_urc('AT+CIICR') # TODO: run until complete
				yield from sleep(5000)
				# Local IP get. Might be mandatory in some cases. Must be called after PDP context activation.
				yield from self.uart.cmd('AT+CIFSR', 'CIFSR')

				# -> Raw TCP:
				# yield from self.uart.cmd('AT+CIPSTART="TCP","%s","%s"' %(server_url, PORT))
				
				if not 'ERROR' in str(error):
					return True
		return False
	
	def at_disconnect(self):
		# Shut down TCP/UDP connections
		# yield from self.uart.cmd('AT+CIPCLOSE')
		# Deactivate GPRS PDP Context
		if self.PDP:
			yield from self.uart.cmd('AT+CIPSHUT')
		# Detach GPRS
		if self.CGATT:
			yield from self.uart.cmd('AT+CGATT=0')

    def start_http_session(self, PROXY_IP):
		""" Called after at_connect """
		# Init HTTP service
		yield from self.uart.cmd('AT+HTTPINIT')

		# Set bearer parameters
		yield from self.uart.cmd('AT+SAPBR=3,1,"CONTYPE","GPRS"')
		yield from self.uart.cmd('AT+SAPBR=3,1,"APN","%s"' %(PROXY_IP))
		yield from self.uart.cmd('AT+SAPBR=1,1')

	def terminate_http_session(self):
		# Terminate HTTP session
		yield from self.uart.cmd('AT+HTTPTERM')
		# Close bearer
		yield from self.uart.cmd('AT+SAPBR=0,1')

	def http_action(self, method, url, data=None, *args, **kwargs):
		""" Called after HTTP session is started """
		# A new HTTP session must be started and stopped

		self.uart.urc.OVERRIDE = True # return raw data
		if kwargs:
			# Add parameters
			url += '?'
			for x in kwargs:
				url += "%s=%s&" % (x, kwargs[x])
		
		url = url[:-1] # Take off final '&'
		print("Destination url: %s" %url) # Debug output

		# Set HTTP params
		yield from self.uart.cmd('AT+HTTPPARA="CID",1')
		yield from self.uart.cmd('AT+HTTPPARA="URL","%s"' %url)

		if method == POST:
			# Set additional HTTP params for data
			size = len(data.encode('utf-8'))
			yield from self.uart.cmd('AT+HTTPDATA=%s,5000' %(size)) # Data size in bytes and timeout
			yield from self.uart.cmd(data)

		yield from self.uart.cmd('AT+HTTPACTION=%s' %method) # GET, POST or HEAD
		yield from sleep(5000)
		resp = yield from self.retrieve_urc('AT+HTTPREAD', timeout=1000)

		self.uart.urc.OVERRIDE = False
		return resp

	def retrieve_urc(self, cmd, urc=None, index=0, timeout=600):
		""" URC handler wrapper """
		cmd = yield from self.uart.cmd(cmd)
		resp = yield from self.uart.urc.retrieve_response(cmd, urc, index, timeout)
		return resp

	def stop(self):
		# TODO: delete all callbacks
		#self.uart.del_line_callback('sms')
		self.uart.del_line_callback('urc')
		yield from self.at_disconnect()
		yield from self.push_powerbutton()
		yield from self.uart.stop()
		self.uart_wrapper.deinit()
		# de-assert DTR
		rtb.GSM_DTR_PIN.high()
		rtb.pwr.GSM_VBAT.release()
		
	# TODO: Add possibility to attach callbacks to SMS received etc

	# TODO: This is not needed...
	def SMS_receive(self, line):
		""" Receive SMS """
		print("Received SMS: %s" %line)
		return True

instance = GSM()
