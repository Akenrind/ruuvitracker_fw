from pyb import I2C
import rtb
from uasyncio.core import get_event_loop,sleep
# TODO: There's a memory leak somewhere?

class mma8652:
	bus = None
	addr = None
	fast_read = False
	fifo = False

	def __init__(self, addr=0x1d):
		self.bus = I2C(1, I2C.MASTER)
		self.addr = addr

	# TODO: Remember: the device ought to be in standby mode for configuration
		
	def test(self, enable):
		""" In a self-test, X, Y, and Z outputs will shift. """
		# *standby?*
		test = ord(self.bus.mem_read(1, self.addr, 0x2b, timeout=200))
		if enable:
			test |= (0x00 ^ 0x80)
		else:
			test &= (0xff ^ 0x80)
		self.bus.mem_write(chr(test), self.addr, 0x2b, timeout=200)
		
	def reset(self):
		""" Software reset """
		self.standby(True)
		reset = ord(self.bus.mem_read(1, self.addr, 0x2b, timeout=200))
		reset |= (0x00 ^ 0x40)
		self.bus.mem_write(chr(reset), self.addr, 0x2b, timeout=200)
		self.standby(False)

	def set_fast_read(self, enabled):
		""" Enable / disable fast read mode """
		self.fast_read = enabled
		self.standby(True)

		conf = ord(self.bus.mem_read(1, self.addr, 0x2a, timeout=200))

		if self.fast_read:
			conf |= ( 1 << 0x01 )
		else:
			conf &= ~( 1 << 0x01 )

		self.bus.mem_write(chr(conf), self.addr, 0x2a, timeout=200)
		self.standby(False)

	def standby(self, enable):
		""" Put accelerometer to / wake up from standby mode """
		conf = ord(self.bus.mem_read(1, self.addr, 0x2a, timeout=200))
		if enable:
			conf &= ~( 1 << 0x01 ) # Disable active mode
		else:
			conf |= ( 1 << 0x01 )

		self.bus.mem_write(chr(conf), self.addr, 0x2a, timeout=200)
	
	def read(self):
		""" Read sensor data """
		#r = self.bus.mem_read(1, self.addr, 0x16, timeout=200, addr_size=8)
		#print("Event: %s" %r)
		if self.fast_read:
			#xyz = self.bus.mem_read(3, self.addr, 0x01, timeout=500, addr_size=8)
			x = self.bus.mem_read(1, self.addr, 0x01, timeout=500, addr_size=8)
			y = self.bus.mem_read(1, self.addr, 0x02, timeout=500, addr_size=8) # auto
			z = self.bus.mem_read(1, self.addr, 0x03, timeout=500, addr_size=8) # auto
		else:
			#xyz = self.bus.mem_read(3, self.addr, 0x01, timeout=500, addr_size=12)
			x = self.bus.mem_read(1, self.addr, 0x01, timeout=500, addr_size=12)
			y = self.bus.mem_read(1, self.addr, 0x02, timeout=500, addr_size=12)
			z = self.bus.mem_read(1, self.addr, 0x03, timeout=500, addr_size=12)

		return "ax: %s, ay: %s, az: %s" % (x, y, z)
		#print(xyz)
		#return xyz

	#def stream(self):
	#	a = self.read()
	#	return a

	def set_fifo(self, enabled):
		""" Enable/disable Fast Read Mode """
		self.fifo = enabled

		conf = ord(self.bus.mem_read(1, self.addr, 0x09, timeout=200))
		if enabled:
			conf |= (0x00 ^ 0x40)
		else:
			conf &= (0xff ^ 0x40)
		self.bus.mem_write(conf, self.addr, 0x09, timeout=200)

	def set_sensitivity(self, sensitivity):
		self.bus.mem_write(sensitivity, self.addr, 0x17, timeout=200)

	def conf_mt(self):
		""" This function configures motion detection for the accelerometer """
		# TODO: Debounce counter
		#FF_MT_COUNT = 0x18
		#FF_MT_THS = 0x17
		#FF_MT_CFG = 0x15
		#FF_MT_SRC = 0x16

		# Detect motion after debounce. Detect motion in all 3d axises
		cfg = 0x11

		# Set debouce counter value
		self.bus.mem_write(0x02, self.addr, 0x18, timeout=200)

		# Set motion threshold
		#self.bus.mem_write(0x00, self.addr, FF_MT_THS, timeout=400)

		# Set actual motion configuration
		self.bus.mem_write(0xf8, self.addr, 0x15, timeout=400)

		# Active mode, odr = 1.56 Hz
		# Set Fast Read Mode for 8-bit results. GO
		conf = 0x39
		if self.fast_read:
			conf |= ( 1 << 0x01 )

		self.bus.mem_write(conf, self.addr, 0x2a, timeout=200)

	def start(self):
		#reg1 = 0x2a # System control register
		#reg2 = 0x2b # For self-test, reset and auto-sleep
		#reg3 = 0x2c # for auto-wake config with interrupts + interrupt polarity, initted earlier
		#reg4 = 0x2d # Interrupt enable register
		#reg5 = 0x2e # Interrupt configuration register

		# The device ought to be in standby mode for configuration
		# self.bus.mem_write(0x00, self.addr, reg1, timeout=200)
		#self.standby(True)

		# Set 2g full range mode
		self.bus.mem_write(0x00, self.addr, 0x0e, timeout=200)
		# Self-test is not enabled, no reset, auto-sleep not enabled, normal power mode.
		self.bus.mem_write(0x00, self.addr, 0x2b)

		# Set intettupt configurations
		# (Implement configuration of interrupt sources etc)
		int_enable = ord(self.bus.mem_read(1, self.addr, 0x2d, timeout=200))
		int_config = ord(self.bus.mem_read(1, self.addr, 0x2e, timeout=200))
		int_enable |= 0x05
		int_config |= 0x05

		self.bus.mem_write(chr(int_enable), self.addr, 0x2d, timeout=200)
		self.bus.mem_write(chr(int_config), self.addr, 0x2e, timeout=200)

		# After this, call configure ff/mt
		#self.standby(False) # active mode is enabled above?
		
	def calibrate(self, x, y, z):
		""" Calibrate with offset registers. Must be called after boot-up """
		#off_x = 0x2f
		#off_y = 0x30
		#off_z = 0x31

		self.bus.mem_write(x, self.addr, 0x2f, timeout=200)
		self.bus.mem_write(y, self.addr, 0x30, timeout=200)
		self.bus.mem_write(z, self.addr, 0x31, timeout=200)

	def interrupt_polarity(self, high=True, pushpull=True):
		"""This configures the interrupt polarity, for the onboard it must be active-high and push-pull"""
		config = ord(self.bus.mem_read(1, self.addr, 0x2c, timeout=200))
		if high:
		    config |= 0x2
		else:
		    config &= 0xfd # (0xff ^ 0x2)
		if pushpull:
		    config &= 0xfe # (0xff ^ 0x1)
		else:
		    config |= 0x1

		self.bus.mem_write(chr(config), self.addr, 0x2c, timeout=200)

onboard = mma8652()
# Set interrupt output active-high push-pull
onboard.interrupt_polarity(True, True)
