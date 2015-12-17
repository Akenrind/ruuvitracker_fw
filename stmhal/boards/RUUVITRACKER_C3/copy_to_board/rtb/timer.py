import rtb

class RTTimer:
	started = False

	micros = None
	ticks = 0
	_start_micros = None
	_current_micros = None

	def __init__(self):
		""" This timer will overflow in ~17 minutes """
		self.micros = pyb.Timer(2, prescaler=83, period=0x3fffffff)

	def stop(self): # Reset all
		self.started = False
		self.ticks = 0
		yield
	
	def start(self):
		self.micros.counter(0)
		self.started = True
		self.ticks = 0
		self._start_micros = self.micros.counter() # GO!
		yield

	def update(self):
		self.ticks += (self.micros.counter() - self._start_micros)
		self._start_micros = self.ticks
		yield
		
	def get_ticks(self):
		if self.started:
			yield from self.update()
		return self.ticks