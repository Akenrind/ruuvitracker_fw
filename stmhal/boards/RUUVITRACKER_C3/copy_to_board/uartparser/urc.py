# TODO: clean this mess up...
from uasyncio import get_event_loop, sleep

class URC():
	""" Further parsing for URCs received from UART """
	_current_buffer = ""
	_events = {}
	_override = False # Override with raw mode

	URC_TABLE = {}

	def __init__(self):
		""" Hard coded URC events. """
		# TODO: redundant
		self.URC_TABLE['+CGATT'] = self.parse_index
		self.URC_TABLE['+CNUM'] = self.parse_number
		self.URC_TABLE['+CGATT'] = self.parse_index
		self.URC_TABLE['+CPIN'] = self.parse_ok
		self.URC_TABLE['PSUTTZ'] = self.parse_time
		self.URC_TABLE['+HTTPREAD'] = self.parse_http_data

	def add_event(self, eventid, method):
		if not eventid in self._events:
			self._events[eventid] = (method)

	def remove_event(self, eventid):
		if eventid in self._events:
			del (self._events[eventid])
    
	def retrieve_response(self, cmd, urc, timeout):
		resp_str = ""
		timeout_iterate = int(timeout / 200)

		if type(cmd) == type(b''): # Not commandTimeouts etc.
			while timeout_iterate:
				timeout_iterate = max(0, timeout_iterate-200)
				resp_str = str(self._current_buffer)

				# Cut out commands from possible responses
				culled_cmd = str(cmd[len("AT"):])

				if culled_cmd[len(culled_cmd)-1] == "'":
					culled_cmd = culled_cmd[:-1]

				if resp_str.startswith(culled_cmd):
					resp_str = resp_str[len(culled_cmd):]

				if not urc in resp_str:
					yield from sleep(200)
				else:
					resp_str = resp_str[resp_str.index[urc]+len(urc):]
					print("[URC]: %s -- %s" %(urc, resp_str))
					self.flush()
					timeout_iterate = 0
		return resp_str.split(",")

	def parse_urc_table(self, line):
		for key in self.URC_TABLE:
			if key in line:
				a = self.URC_TABLE[key](line)
				if a:
					a() # Auto-delete callback after calling
					del self.URC_TABLE[key]

	def flush(self):
		self._current_buffer = ""

	def print_line(self, line):
		print(line)
		yield

	def save_line(self, line):
		get = True
		strfy = str(line)
		for c in strfy:
			if c in r' \n\t\r': # Cull "Whitespace"
				strfy.replace(c, '')
		if not (not strfy or strfy is "b''" or "AT+" in strfy): # Cull commands
			buf = self._current_buffer + (strfy)
			if "OK" in buf or "ERROR" in buf and not self._override:
				pass
			else:
				self._current_buffer = buf
			self.parse_urc_table(line)
			
		return True

	# TODO: these aren't necessary if we hardcode AT response index...

	def parse_http_data(self, string):
		elements = string.replace("'","|").split("|")

		data = ""

		for i in elements:
			if i.startswith("{"): # Data starts here
				print(i)
				data = i
		if data: # Needs to be converted
			for c in data:
				if c in r'\n\t\r{}':
					data.replace(c, '')
			print("Obtained http data: %s\n" %data)

	def parse_number(self, line):
		""" Finds phone number """
		# Remove quotes and split, with "," being the delimiter
		elements = str(line).replace('"', '').split(',')

		for i in elements:
			num = [str(s) for s in i.split() if s.isdigit() ]

			if(len(str(num)) > 9 and len(str(num)) <= 17):
				print("[URC]: Phone number found: ", str(num[0]))
				if '+CNUM' in self._events:
					self._events['+CNUM'](str(num[0]))
					return str(num[0])
				# Delete callback from premises and only add it again if ID is not present

	def parse_index(self, line):
		""" Checks whether response is 0 or 1 """
		# TODO
		one = str(line).replace('"','')
		print(one)

	def parse_ok(self, line):
		""" When we want response to be other than error """
		one = str(line).replace('"','')
		print(one)

	def parse_time(self, line):
		""" Parse Network time """
		if not self._time:
			elem = str(line).split('"')

			for j in elem:
				if( len(str(j)) >= 15 and len(str(j)) < 21 ): # Timestamp length
					if 'PSUTTZ' in _events:
						a = _events['PSUTTZ'](str(j)) # Dispatch event
						a()