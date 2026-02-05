from Components.Converter.Converter import Converter
from Components.Element import cached
import NavigationInstance
from enigma import iPlayableService
import urllib


class AglareStreamInfo(Converter):
    STREAMURL = 0
    STREAMTYPE = 1

    def __init__(self, type):
        Converter.__init__(self, type)
        self.type = self._get_type(type)

    def _get_type(self, type):
        """Determine the stream type based on the passed type."""
        if 'StreamUrl' in type:
            return self.STREAMURL
        elif 'StreamType' in type:
            return self.STREAMTYPE
        return None

    def _is_stream_service(self, refstr):
        """Check if the service is a stream service."""
        return refstr and ('%3a//' in refstr or '://' in refstr)

    def streamtype(self):
        playref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
        if playref:
            refstr = playref.toString()
            if self._is_stream_service(refstr):
                if refstr.startswith('1:0:'):
                    if any(
                        x in refstr for x in (
                            '0.0.0.0:',
                            '127.0.0.1:',
                            'localhost:')):
                        return 'Stream Relay'
                    elif '%3a' in refstr:
                        return 'GStreamer'
                elif refstr.startswith('4097:0:'):
                    return 'MediaPlayer'
                elif refstr.startswith('5001:0:'):
                    return 'GstPlayer'
                elif refstr.startswith('5002:0:'):
                    return 'ExtePlayer3'
                else:
                    # Generic stream type for other stream references
                    return 'Unknown'
        return ''

    def streamurl(self):
        playref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
        if not playref:
            return 'No URL available'

        refstr = self._parse_refstr(playref.toString())
        if not refstr:
            return 'No URL available'

        try:
            # Decodifica eventuale URL-encoding
            decoded = urllib.unquote(refstr)

            # Cerca l'inizio dell'URL
            http_index = decoded.find('http://')
            https_index = decoded.find('https://')

            if http_index == -1 and https_index == -1:
                return 'Invalid stream URL format'

            start = http_index if http_index != -1 else https_index
            url = decoded[start:]

            # Taglia eventuali residui Enigma2
            url = url.split('/1:0:')[0]

            # Rimuove schema
            if url.startswith('http://'):
                url = url[len('http://'):]
            elif url.startswith('https://'):
                url = url[len('https://'):]

            # Rimuove credenziali se presenti
            if '@' in url:
                url = url.split('@')[-1]

            return url

        except Exception:
            return 'Invalid stream URL format'

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
        if what[0] != self.CHANGED_SPECIFIC or what[1] in (
                iPlayableService.evStart,):
            Converter.changed(self, what)
