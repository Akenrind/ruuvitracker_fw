from uasyncio import get_event_loop, sleep

class URC():
	""" Further parsing for URCs from the UART """
	_current_buffer = ""
	_events = []
	OVERRIDE = False

	PARSE = {}

	def __init__(self):
		# TODO: redundant hard-coded 'further parsing' methods
		self.PARSE['PSUTTZ'] = self.parse_time
		self.PARSE['HTTPREAD'] = self.parse_http_data
    
	def retrieve_response(self, cmd, urc="", index=0, timeout=600, interval=200):
		resp_str = ""
		timeout_iterate = int(timeout / interval)
		#if type(cmd) == type(b''): # Why?
		#	cmd = cmd.decode()

		if not urc: # use default URC
			urc = cmd[3:] # By default, urc is [AT+]URC[?][=<sth>]
			if cmd.endswith('?'): # Command was a query or test command
				urc = urc[:-1] # Remove questionmark
			if "=" in urc: # Command was an execution command or test command
				urc = (str(urc.split("=")))[0] # Exclude parameters

			print("Searching for this urc: %s" %urc)

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
				try:
					end = resp_str.index('+')
					resp_str = resp_str[:end]
				except ValueError:
					print("No string ;_;")
				print("%s --- %s" %(cmd, resp_str))
				self.flush()
				
				if not self.OVERRIDE: # Return data in index, not raw data
					response = resp_str.split(",") # URC indices split
					index = min(index, len(response)-1)
					return response[index]

				else:
					response = resp_str
					# Parse further, if necessary
					for e in self._events:
						if e in resp_str:
							a = self.PARSE[e](response)
							if a:
								response = a()
								_events.remove(e)
					return response # Return 'raw data' (eg. http data)
		else:
			return ""

	def flush(self):
		self._current_buffer = ""

	# Omits EOLs
	def parse_urc(self, line): # TODO: perform ure callback here & test
		strfy = line.decode()
		print(strfy)
		for c in strfy:
			if c in r' \n\t\r': # Cull "Whitespace"
				strfy.replace(c, '')
		if strfy and not "AT+" in strfy: # Cull commands
			buf = self._current_buffer + (strfy)
			if "ERROR" in buf:
				pass
				# handle error
			if "OK" in buf and not self.OVERRIDE: #or "ERROR" in buf and not self.OVERRIDE:
				pass
			else:
				self._current_buffer = buf
			#self.parse_urc_table(line)
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