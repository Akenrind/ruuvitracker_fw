from pyb import I2C
import rtb
from uasyncio.core import get_event_loop,sleep

class mma8652:
	bus = None
	addr = None
	fast_read = False
	fifo = False

	def __init__(self, addr=0x1d):
		self.bus = I2C(1, I2C.MASTER)
		self.addr = addr
		
	def test(self, enable):
		""" In a self-test, X, Y, and Z outputs will shift. """
		test = ord(self.bus.mem_read(1, self.addr, 0x2b, timeout=200))
		if enable:
			test |= (0x00 ^ 0x80)
		else:
			test &= (0xff ^ 0x80)
		self.bus.mem_write(test, self.addr, 0x2b, timeout=200)
		
	def reset(self):
		""" Software reset """
		reset = ord(self.bus.mem_read(1, self.addr, 0x2b, timeout=200))
		reset |= (0x00 ^ 0x40) # Set bit 6 to 1
		self.bus.mem_write(chr(reset), self.addr, 0x2b, timeout=200)

	def set_fast_read(self, enabled):
		""" Enable / disable fast read mode """
		self.fast_read = enabled

		conf = ord(self.bus.mem_read(1, self.addr, 0x2a, timeout=200))
		if self.fast_read:
			conf |= ( 1 << 0x01 )
		else:
			conf &= ~( 1 << 0x01 )

		self.bus.mem_write(conf, self.addr, 0x2a, timeout=200)

	def standby(self, enable):
		""" Put accelerometer to / wake up from standby mode """
		conf = ord(self.bus.mem_read(1, self.addr, 0x2a, timeout=200))
		if enable:
			conf &= ~( 1 << 0x01 ) # Disable active mode
		else:
			conf |= ( 1 << 0x01 )

		self.bus.mem_write(conf, self.addr, 0x2a, timeout=200)
	
	def read(self):
		""" Read sensor data """
		#r = self.bus.mem_read(1, self.addr, 0x16, timeout=200, addr_size=8)
		#print("Event: %s" %r)
		if self.fast_read:
			l = self.bus.mem_read(3, self.addr, 0x01, timeout=200, addr_size=8)
		else:
			l = self.bus.mem_read(3, self.addr, 0x01, timeout=200, addr_size=12)

		return (str(l))

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
		FF_MT_THS = 0x17
		self.bus.mem_write(sensitivity, self.addr, FF_MT_THS, timeout=200)

	def conf_mt(self):
		""" This function configures motion detection for the accelerometer """
		# TODO: Debounce counter
		FF_MT_COUNT = 0x18
		FF_MT_THS = 0x17
		FF_MT_CFG = 0x15
		FF_MT_SRC = 0x16

		# Detect motion after debounce. Detect motion in all 3d axises
		cfg = 0x11

		# Set debouce counter value
		self.bus.mem_write(0x02, self.addr, FF_MT_COUNT, timeout=200)

		# Set motion threshold. DEBUG
		self.bus.mem_write(0x08, self.addr, FF_MT_THS, timeout=200)

		# Set actual motion configuration
		self.bus.mem_write(0xf8, self.addr, FF_MT_CFG, timeout=200)

		# Active mode, odr = 1.56 Hz
		# Set Fast Read Mode for 8-bit results. GO
		conf = 0x39
		if self.fast_read:
			conf |= ( 1 << 0x01 )

		self.bus.mem_write(conf, self.addr, 0x2a, timeout=200)

	def start(self):
		reg1 = 0x2a # System control register
		reg2 = 0x2b # For self-test, reset and auto-sleep
		reg3 = 0x2c # for auto-wake config with interrupts + interrupt polarity, initted earlier
		reg4 = 0x2d # Interrupt enable register
		reg5 = 0x2e # Interrupt configuration register

		# The device ought to be in standby mode for configuration
		self.bus.mem_write(0x00, self.addr, reg1, timeout=200)

		# Set 2g full range mode
		self.bus.mem_write(0x00, self.addr, 0x0e, timeout=200)
		# Self-test is not enabled, no reset, auto-sleep not enabled, normal power mode.
		self.bus.mem_write(0x00, self.addr, reg2)

		# Set intettupt configurations
		# (Implement configuration of interrupt sources etc)
		int_enable = ord(self.bus.mem_read(1, self.addr, 0x2d, timeout=200))
		int_config = ord(self.bus.mem_read(1, self.addr, 0x2e, timeout=200))
		int_enable |= 0x05
		int_config |= 0x05

		self.bus.mem_write(chr(int_enable), self.addr, 0x2d, timeout=200)
		self.bus.mem_write(chr(int_config), self.addr, 0x2e, timeout=200)

		# Configure ff/mt
		self.conf_mt()
		
	def calibrate(self, x, y, z):
		""" Calibrate with offset registers. Must be called after boot-up """
		off_x = 0x2f
		off_y = 0x30
		off_z = 0x31

		self.bus.mem_write(x, self.addr, off_x, timeout=200)
		self.bus.mem_write(y, self.addr, off_y, timeout=200)
		self.bus.mem_write(z, self.addr, off_z, timeout=200)

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
