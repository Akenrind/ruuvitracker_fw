from uasyncio import get_event_loop, sleep

class URC():
	""" Further parsing for URCs from the UART """
	_current_buffer = ""
	_events = {}
	OVERRIDE = False

	PARSE = {}

	def __init__(self):
		# TODO: redundant hard-coded 'further parsing' methods
		self.PARSE['PSUTTZ'] = self.parse_time
		self.PARSE['HTTPREAD'] = self.parse_http_data
    
	def retrieve_response(self, cmd, urc=None, index=0, timeout=600, interval=200):
		resp_str = ""
		timeout_iterate = int(timeout / interval)

		if not urc:
			urc = cmd[3:] # By default, urc is [AT+]URC[?][=<sth>]
			if cmd.endswith('?'): # Command was a query or test command
				urc = urc[:-1] # Remove questionmark
			if "=" in urc: # Command was an execution command or test command
				urc = (urc.split("="))[0] # Exclude parameters

		if type(cmd) == type(b''): # Do not process commandTimeouts etc.
			while timeout_iterate:
				timeout_iterate = max(0, timeout_iterate-interval)
				resp_str = str(self._current_buffer)

				# Cut out commands from possible responses in case ECHO is not off...
				culled_cmd = str(cmd[len("AT"):])

				if culled_cmd[len(culled_cmd)-1] == "'":
					culled_cmd = culled_cmd[:-1]

				if resp_str.startswith(culled_cmd):
					resp_str = resp_str[len(culled_cmd):]

				if not urc in resp_str:
					yield from sleep(interval)
				else:
					resp_str = resp_str[resp_str.index[urc]+len(urc)+1:] # Remember to take off ":"
					print("[URC]: %s -- %s" %(urc, resp_str))
					self.flush()
					timeout_iterate = 0

		if not OVERRIDE: # Return data in index, not raw data
			response = resp_str.split(",") # URC indices split
			return response[index]

		else:
			# Parse further, if necessary
			for e in self._events:
				if e in response:
					a = self.PARSE[e](response)
					if a:
						response = a()
						del self._events[key]
		return response # Return 'raw data' (eg. http data)

	def flush(self):
		self._current_buffer = ""

	# Omits EOLs
	def parse_urc(self, line): # TODO: perform ure callback here & test
		strfy = str(line)
		for c in strfy:
			if c in r' \n\t\r': # Cull "Whitespace"
				strfy.replace(c, '')
		if not (not strfy or strfy is "b''" or "AT+" in strfy): # Cull commands
			buf = self._current_buffer + (strfy)
			if "OK" in buf or "ERROR" in buf and not self.OVERRIDE:
				pass
			else:
				self._current_buffer = buf
			self.parse_urc_table(line)
		return True

	# TODO: clean up this MESS
		
	def parse_time(self, line):
		""" Parse Network time """
		elem = str(line).split('"')

		for j in elem:
			if( len(str(j)) >= 15 and len(str(j)) < 21 ): # Timestamp length
				time = str(j) # TODO: parse
				return time

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

	# TODO: Clean up, this is redundant...
	def parse_number(self, line):
		""" Finds phone number """
		# Remove quotes and split, with "," being the delimiter
		elements = str(line).replace('"', '').split(',')

		for i in elements:
			num = [str(s) for s in i.split() if s.isdigit() ]

			if(len(str(num)) > 9 and len(str(num)) <= 17):
				return str(num[0])