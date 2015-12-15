from uasyncio import get_event_loop, sleep

class URC():
	""" Further parsing for URCs from the UART """
	_current_buffer = ""
	_events = {}
	OVERRIDE = False

	PARSE = {}

	def __init__(self):
		# TODO: hard-coded 'further parsing' methods
		self.PARSE['PSUTTZ'] = self.parse_time
		self.PARSE['HTTPREAD'] = self.parse_http_data

	def add_event(self, name, cb):
		if not name in self._events:
			self._events[name] = (cb)
		# Events automatically delete themselves..?
    
	def retrieve_response(self, cmd, urc="", index=0, timeout=600, interval=200):
		resp_str = ""
		timeout_iterate = int(timeout / interval)

		if not urc: # use default URC
			urc = cmd[3:] # By default, urc is [AT+]URC[?][=<sth>]
			if cmd.endswith('?'): # Command was a query or test command
				urc = urc[:-1] # Remove questionmark
			if "=" in urc: # Command was an execution command or test command
				urc = (str(urc.split("=")))[0] # Exclude parameters
			#print("DEBUG: Searching for this urc: %s" %urc)

		while timeout_iterate:
			timeout_iterate = max(0, timeout_iterate)
			timeout_iterate -= 1

			resp_str = self._current_buffer

			# Cut out commands from possible responses in case ECHO is not off...
			culled_cmd = cmd[len("AT"):]
			if resp_str.startswith(culled_cmd):
				resp_str = resp_str[len(culled_cmd):]

			if not urc in resp_str:
				yield from sleep(interval)
			else:
				resp_str = resp_str[resp_str.index(urc)+len(urc)+2:] # Remember to take off ": "
				# If not override				
				try:
					end = resp_str.index('+')
					resp_str = resp_str[:end]
				except ValueError:
					end = None
				print("%s --- %s" %(cmd, resp_str))
				self.flush()
				
				# Return 'raw data' by default (eg. http data)

				if not self.OVERRIDE: # Return data in index, not raw data
					response = resp_str.split(",") # URC indices split
					index = min(index, len(response)-1)
					#response[index] = response[index][1:-1] # Take off double quotes
					resp_str = response[index]
				return resp_str
		else:
			return ""

	def flush(self):
		self._current_buffer = ""

	def parse_events(self, line):
		# Parse further, if necessary
		if self._events:
			for e in self._events:
				if e in line:
					a = self.PARSE[e](line)
					if a:
						print("DEBUG: dispatching data: %s" %a) # Boot time
						self._events[e](a)

	# Omits EOLs
	def parse_urc(self, line): # TODO: perform ure callback here & test
		strfy = line.decode()
		for c in strfy:
			if c in r' \n\t\r': # Cull "Whitespace"
				strfy.replace(c, '')
		if strfy and not "AT+" in strfy: # Cull commands
			buf = self._current_buffer + (strfy)
			if "ERROR" in buf:
				pass
				# TODO: handle error
			if "OK" in buf and not self.OVERRIDE:
				pass
			else:
				self._current_buffer = buf
			self.parse_events(strfy)
		return True

	# TODO: clean up this MESS
		
	def parse_time(self, line):
		""" Parse Network time """
		elem = line.split(':')
		return elem[1] # TODO: Parse

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
			return data