from Components.Converter.Converter import Converter
from Components.Element import cached


class AglareRouteInfo(Converter, object):
	Info = 0
	Lan = 1
	Wifi = 2
	Modem = 3

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = getattr(self, type, self.Info)  # Ottimizza l'assegnazione del tipo

		# Pre-carica il contenuto del file /proc/net/route per ottimizzare l'accesso
		self.routes = self.load_routes()

	def load_routes(self):
		routes = []
		try:
			with open('/proc/net/route') as f:
				routes = f.readlines()
		except Exception as e:
			print(f"Error loading route file: {e}")
		return routes

	@cached
	def getBoolean(self):
		for line in self.routes:
			fields = line.split()
			if self.type == self.Lan and fields[0] == 'eth0' and fields[3] == '0003':
				return True
			elif self.type == self.Wifi and fields[0] in ['wlan0', 'ra0'] and fields[3] == '0003':
				return True
			elif self.type == self.Modem and fields[0] == 'ppp0' and fields[3] == '0003':
				return True
		return False

	boolean = property(getBoolean)

	@cached
	def getText(self):
		for line in self.routes:
			fields = line.split()
			if self.type == self.Info:
				if fields[0] == 'eth0' and fields[3] == '0003':
					return 'lan'
				elif fields[0] in ['wlan0', 'ra0'] and fields[3] == '0003':
					return 'wifi'
				elif fields[0] == 'ppp0' and fields[3] == '0003':
					return '3g'
		return 'no connection'

	text = property(getText)

	def changed(self, what):
		Converter.changed(self, what)


"""
<screen name="RouteInfoScreen" position="center,center" size="1280,720" title="Network Information">
	<!-- Widget per visualizzare lo stato della connessione LAN -->
	<widget name="lanStatus" source="ServiceEvent" render="Label" position="50,100" size="1180,50" font="Bold; 26" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="green" valign="center">
		<convert type="AglareRouteInfo">Lan</convert>
	</widget>

	<!-- Widget per visualizzare lo stato della connessione Wi-Fi -->
	<widget name="wifiStatus" source="ServiceEvent" render="Label" position="50,160" size="1180,50" font="Bold; 26" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="yellow" valign="center">
		<convert type="AglareRouteInfo">Wifi</convert>
	</widget>

	<!-- Widget per visualizzare lo stato della connessione Modem -->
	<widget name="modemStatus" source="ServiceEvent" render="Label" position="50,220" size="1180,50" font="Bold; 26" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="blue" valign="center">
		<convert type="AglareRouteInfo">Modem</convert>
	</widget>

	<!-- Widget per visualizzare informazioni generali sulla connessione -->
	<widget name="networkInfo" source="ServiceEvent" render="Label" position="50,280" size="1180,50" font="Bold; 26" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="red" valign="center">
		<convert type="AglareRouteInfo">Info</convert>
	</widget>

	<!-- Aggiunta di un widget che mostra "No Connection" quando non c'è rete -->
	<widget name="noConnection" source="ServiceEvent" render="Label" position="50,340" size="1180,50" font="Bold; 26" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="gray" valign="center">
		<convert type="AglareRouteInfo">Info</convert>
		<conditions>
			<condition value="no connection">No Connection</condition>
		</conditions>
	</widget>
</screen>
"""
