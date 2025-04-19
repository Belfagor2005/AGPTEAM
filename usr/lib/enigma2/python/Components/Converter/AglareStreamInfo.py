from Components.Converter.Converter import Converter
from Components.Element import cached
import NavigationInstance
from enigma import iPlayableService


class AglareStreamInfo(Converter):
	STREAMURL = 0
	STREAMTYPE = 1

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = self._get_type(type)

	def _get_type(self, type):
		"""Determina il tipo di stream in base al tipo passato."""
		if 'StreamUrl' in type:
			return self.STREAMURL
		elif 'StreamType' in type:
			return self.STREAMTYPE
		return None

	def _parse_refstr(self, refstr):
		"""Funzione di parsing per estrarre i dati utili dal refstr."""
		if '%3a' in refstr:
			strtype = refstr.replace('%3a', ':')
			return strtype
		return ''

	def streamtype(self):
		playref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
		if playref:
			refstr = self._parse_refstr(playref.toString())
			if refstr:
				if refstr.startswith('1:0:'):
					if any(x in refstr for x in ('0.0.0.0:', '127.0.0.1:', 'localhost:')):
						return 'Stream Relay'
					elif '%3a' in refstr:
						return 'GStreamer'
				elif refstr.startswith('4097:0:'):
					return 'MediaPlayer'
				elif refstr.startswith('5001:0:'):
					return 'GstPlayer'
				elif refstr.startswith('5002:0:'):
					return 'ExtePlayer3'
		return 'Unknown'

	def streamurl(self):
		playref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
		if playref:
			refstr = self._parse_refstr(playref.toString())
			if refstr:
				try:
					strurl = refstr.split(':')
					streamurl = strurl[10].replace('%3a', ':').replace('http://', '').replace('https://', '').split('/1:0:')[0]
					streamurl = streamurl.split('@')[-1]
					return streamurl
				except IndexError:
					return 'Invalid stream URL format'
		return 'No URL available'

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if info:
			if self.type == self.STREAMURL:
				return str(self.streamurl())
			elif self.type == self.STREAMTYPE:
				return str(self.streamtype())
		return 'No information available'

	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
			Converter.changed(self, what)
