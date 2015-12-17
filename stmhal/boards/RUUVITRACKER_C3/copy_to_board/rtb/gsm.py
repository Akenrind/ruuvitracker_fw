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
	boot_time = None # Indicates whether network time has been fetched, NOT updated in real-time
	CNUM = None # Subscriber number

	CGATT = False # GPRS context attached
	CPIN = False # PIN inserted / ready
	PDP = False # GPRS PDP context
	READY = False
	
	# Sleep request and cause of sleep
	# eg. sim is locked?

	def __init__(self):
		pass

	def start(self):
		# Try without flow control first
		self.uart_wrapper = uartparser.UART_with_fileno(rtb.GSM_UART_N, 115200, read_buf_len=256)
		#self.uart_wrapper = uartparser.UART_with_fileno(rtb.GSM_UART_N, 115200, read_buf_len=256, flow=pyb.UART.RTS | pyb.UART.CTS)
		# TODO: schedule something that will reset the board to autobauding mode if it had not initialized within X seconds
		self.uart = uartparser.UARTParser(self.uart_wrapper)

		#self.uart.add_line_callback('sms', 'startswith', '+CTS', self.SMS_receive)
		#self.uart.add_line_callback('pls', 'startswith', '+', self.request)
		self.uart.add_line_callback('urc', None, None, self.uart.urc.parse_urc)
		# Special callbacks
		self.uart.urc.add_event('PSUTTZ', self.use_network_time)
		self.uart.urc.add_event('HTTPREAD', self.fetch_data)
		# The rest is automatic-ish...

		# The parsers start method is a generator so it's called like this
		get_event_loop().create_task(self.uart.start())

		# Power on
		rtb.pwr.GSM_VBAT.request()
		yield from self.push_powerbutton()
		# Assert DTR to enable module UART (we can also sample the DTR pin to see if the module is powered on)
		rtb.GSM_DTR_PIN.low()

		# Just to keep consistent API, make this a coroutine too
		yield

	def fetch_data(self, line):
		print("data: %s" %line)
		return True

	def push_powerbutton(self, push_time=2000):
		rtb.GSM_PWR_PIN.low()
		yield from sleep(push_time)
		rtb.GSM_PWR_PIN.high()

	def at_mode_init(self, boot=True):
		# Make sure autobauding autobauds
		resp = yield from self.uart.cmd("AT")
		# Echo off
		resp = yield from self.uart.cmd("ATE0")
		# Set fixed baudrate
		resp = yield from self.uart.cmd("AT+IPR=115200")
		# Network registration messages enable
		resp = yield from self.uart.cmd("AT+CREG=2")
		if boot:
			# Network time fetch for first time
			resp = yield from self.retrieve_urc("AT+CLTS=1")

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
	def set_flow_control(self, value=True):
		"""Enables/disables RTS/CTS flow control on the module and UART"""
		if value:
		    resp = yield from self.uart.cmd("AT+IFC=2,2")
		    self.uart_wrapper.init(115200, read_buf_len=256, flow=pyb.UART.RTS | pyb.UART.CTS)
		else:
		    resp = yield from self.uart.cmd("AT+IFC=0,0")
		    self.uart_wrapper.init(115200, read_buf_len=256, flow=0)

	def at_test(self):
		yield from self.uart.cmd('AT')

	def use_network_time(self, time):
		self.network_time = time
		return True

	def fetch_network_time(self, time):
		""" Use GSM network time as a timestamp """
		# Or rather not, because it says operation not allowed
		#if not time:
			# Network time has been fetched at least once, and CCLK is local time. TODO: indicate.
			#self.network_time = yield from self.retrieve_urc("AT+CCLK", "CLK") # This is local time
			#return '+' in self.network_time
		self.boot_time = time
		return True

	def at_id_init(self):
		yield from sleep(10000)
		#self.at_mode_init() No fixed baud T_T
		# Obtain subscriber number for 'client ID'
		resp = yield from self.uart.cmd('AT')
		resp = yield from self.uart.cmd('ATE0') # But no fixed bauds

		ready = yield from self.at_ready()
		if ready:
			self.READY = True
			yield from sleep(2000)
			self.CNUM = yield from self.retrieve_urc('AT+CNUM', urc="NUM", index=1, timeout=4000)
			attached = yield from self.retrieve_urc('AT+CGATT?', urc="GATT", timeout=4000)
			self.CGATT = '1' in attached
			if self.CGATT:
				yield from self.uart.cmd('AT+CGATT=0') # Detach GPRS

	def at_ready(self):
		pin = yield from self.retrieve_urc('AT+CPIN?', timeout=1000)
		if pin:
			print("%s" %(pin))
			self.CPIN = 'READY' in pin
			if 'SIM' in pin:
				print("SIM card is locked. Please use unlock it with a cell phone (recommended) or with a gsm method. (More at Github Readme)")
		return self.CPIN

	def unlock_sim_pin(self, code):
		""" Unlocks SIM. Do NOT use this function unless you are absolutely out of equipment (cell phones) """
		if code:
			yield from self.retrieve_urc('AT+CPIN=%s' %code)
			yield from sleep(2000)
			yield from self.retrieve_urc('AT+CLCK="SC",0,"%s"' %code)
			yield from sleep(2000)

	def at_connect(self, PROXY_IP, USERNAME, PASSWORD):
		""" Connects to GPRS proxy server. Connection may only be carried out if CPIN is ready """
		if self.READY:
			yield from sleep(7000)
			yield from self.uart.cmd('AT')

			yield from self.uart.cmd("AT+CIPSHUT")
			yield from self.uart.cmd('AT+CIPSTATUS')

			yield from sleep(1000) # 'Flow control.'
			yield from self.uart.cmd('AT+CGDCONT=1,"IP","%s"' %(PROXY_IP))
			yield from sleep(1000)
			yield from self.uart.cmd('AT+CIPMUX=0') # Set up single connection mode
			yield from sleep(1000)
	
			# Attach GPRS
			yield from self.uart.cmd("AT+CGATT=1")
			yield from sleep(1000)

			yield from self.uart.cmd('AT+CSTT="%s", "%s", "%s"' %(PROXY_IP, USERNAME, PASSWORD))
			yield from sleep(1000)		
			yield from self.uart.cmd('AT+CIICR')
			# Bringing up the wireless takes a while
			yield from sleep(10000)
			# If you can't connect, no signal, or your card does not support GPRS...
			# TODO: Enable URC and see if you can get local IP. return true
			yield from self.uart.cmd('AT+CIFSR') # Local IP get, might be mandatory
	
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

	def retrieve_urc(self, cmd, urc="", index=0, timeout=600):
		""" URC handler wrapper """
		command = cmd
		cmd = yield from self.uart.cmd(cmd)
		resp = yield from self.uart.urc.retrieve_response(command, urc, index, timeout)
		if not resp:
			print("No URC obtained in time.")
		return resp

	def restart_uart(self):
		self.uart.del_line_callback('urc')
		yield from self.uart.stop()
		self.uart_wrapper.deinit()
		yield from sleep(1000)
		self.uart_wrapper = uartparser.UART_with_fileno(rtb.GSM_UART_N, 115200, read_buf_len=256)
		self.uart = uartparser.UARTParser(self.uart_wrapper)

	def stop(self):
		# TODO: delete all callbacks
		#self.uart.del_line_callback('sms')
		self.uart.del_line_callback('urc')
		self.uart.del_line_callback('pls')
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
