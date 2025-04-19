# -*- coding: utf-8 -*-

# This plugin is free software, you are allowed to
# modify it (if you keep the license),
# but you are not allowed to distribute/publish
# it without source code (this version and your modifications).
# This means you also have to distribute
# source code of your modifications.
#
#
# #########################
# NetSpeedInfo for VU+
# Coded by markusw (c) 2013
# www.vuplus-support.org
# 20250401 @ lululla fix
# #########################
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Converter.Poll import Poll

# Eg. use example
"""
<widget
	backgroundColor="background"
	font="Regular; 22"
	foregroundColor="white"
	halign="left"
	position="522,1019"
	render="Label"
	size="114,50"
	source="session.CurrentService"
	transparent="1"
	zPosition="99"
	text="88"
	valign="center">
	<convert type="AglareNetSpeedInfo">RC_MB</convert>
</widget>
"""

# Configuration dictionary for monitoring types
CONFIG_OPTIONS = {
	"RCL": 0,             # Receive Lan in Megabit/s
	"TML": 1,             # Transmit Lan in Megabit/s
	"RCW": 2,             # Receive Wlan in Megabit/s
	"TMW": 3,             # Transmit Wlan in Megabit/s
	"RCLT": 4,            # Receive Lan-total since last reboot in Megabytes
	"TMLT": 5,            # Transmit Lan-total since last reboot in Megabytes
	"RCWT": 6,            # Receive Wlan-total since last reboot in Megabytes
	"TMWT": 7,            # Transmit Wlan-total since last reboot in Megabytes
	"RCL_MB": 8,          # Receive Lan in Megabyte/s
	"TML_MB": 9,          # Transmit Lan in Megabyte/s
	"RCW_MB": 10,         # Receive Wlan in Megabyte/s
	"TMW_MB": 11,         # Transmit Wlan in Megabyte/s
	"RC": 12,             # Receive Lan or Wlan in Megabit/s (prioritize Lan)
	"TM": 13,             # Transmit Lan or Wlan in Megabit/s (prioritize Lan)
	"RCT": 14,            # Receive Lan or Wlan total since last reboot (prioritize Lan)
	"TMT": 15,            # Transmit Lan or Wlan total since last reboot (prioritize Lan)
	"RC_MB": 16,          # Receive Lan or Wlan in Megabyte/s (prioritize Lan)
	"TM_MB": 17,          # Transmit Lan or Wlan in Megabyte/s (prioritize Lan)
	"NET_TYP": 18,        # Lan, Wlan, or Lan+Wlan
	"ERR_RCL": 19,        # Errors in Lan Receive
	"ERR_TML": 20,        # Errors in Lan Transmit
	"DRO_RCL": 21,        # Drops in Lan Receive
	"DRO_TML": 22,        # Drops in Lan Transmit
	"ERR_RCW": 23,        # Errors in Wlan Receive
	"ERR_TMW": 24,        # Errors in Wlan Transmit
	"DRO_RCW": 25,        # Drops in Wlan Receive
	"DRO_TMW": 26         # Drops in Wlan Transmit
}


class AglareNetSpeedInfo(Poll, Converter, object):
	def __init__(self, type, update_interval=1000):
		# Initialize Poll and Converter
		Poll.__init__(self)
		Converter.__init__(self, type)

		self.poll_interval = update_interval
		self.poll_enabled = True
		self.type = CONFIG_OPTIONS.get(type, 0)

		# Initialize all network-related attributes
		self.resetNetworkStats()

	def resetNetworkStats(self):
		"""Reset all network stats to initial values."""
		self.lanreceive = 0
		self.lantransmit = 0
		self.wlanreceive = 0
		self.wlantransmit = 0
		self.lanreceivetotal = 0
		self.lantransmittotal = 0
		self.wlanreceivetotal = 0
		self.wlantransmittotal = 0
		self.nettyp = "NONE"
		self.error_lanreceive = 0
		self.error_lantransmit = 0
		self.error_wlanreceive = 0
		self.error_wlantransmit = 0
		self.drop_lanreceive = 0
		self.drop_lantransmit = 0
		self.drop_wlanreceive = 0
		self.drop_wlantransmit = 0

	@cached
	def getText(self):
		"""Return the current network speed information based on the selected type."""
		return self.updateNetSpeedInfoStatus()

	text = property(getText)

	def updateNetSpeedInfoStatus(self):
		"""Update network speed information and return the corresponding value."""
		flaglan = flagwlan = 0
		try:
			with open("/proc/net/dev") as bwm:
				bw = bwm.readline()  # Skip first line (headers)
				bw = bwm.readline()  # Start reading the next line
				while bw:
					bw = bwm.readline().strip()
					# Normalize space and handle network interfaces
					bw = " ".join(bw.split())
					if "eth" in bw:  # Check for Ethernet interface (LAN)
						flaglan = 1
						sp = bw.split(":")
						stats = sp[1].split()
						self.processInterfaceData(stats, "lan")
					elif "ra" in bw or "wlan" in bw or "wifi" in bw:  # Check for Wifi interface (WLAN)
						flagwlan = 1
						sp = bw.split(":")
						stats = sp[1].split()
						self.processInterfaceData(stats, "wlan")
		except Exception as e:
			print(f"Error reading network stats: {e}")

		# Update flags based on available interfaces
		if flaglan:
			self.nettyp = "LAN" if not flagwlan else "LAN+WLAN"
			self.receive = self.lanreceive
			self.transmit = self.lantransmit
		elif flagwlan:
			self.nettyp = "WLAN"
			self.receive = self.wlanreceive
			self.transmit = self.wlantransmit

		# Return appropriate data based on selected type
		return self.formatOutput()

	def processInterfaceData(self, stats, interface_type):
		"""Process stats for a given network interface (LAN/WLAN)."""
		receive = int(stats[0]) / 1024  # Convert to kilobytes
		transmit = int(stats[8]) / 1024  # Convert to kilobytes

		if interface_type == "lan":
			self.lanreceive = receive
			self.lantransmit = transmit
			self.lanreceivetotal = receive
			self.lantransmittotal = transmit
		elif interface_type == "wlan":
			self.wlanreceive = receive
			self.wlantransmit = transmit
			self.wlanreceivetotal = receive
			self.wlantransmittotal = transmit

	def formatOutput(self):
		"""Format the output based on selected network type."""
		if self.type == CONFIG_OPTIONS["RCL"]:
			return f"{self.lanreceive:.2f}"
		elif self.type == CONFIG_OPTIONS["TML"]:
			return f"{self.lantransmit:.2f}"
		elif self.type == CONFIG_OPTIONS["RCW"]:
			return f"{self.wlanreceive:.2f}"
		elif self.type == CONFIG_OPTIONS["TMW"]:
			return f"{self.wlantransmit:.2f}"
		elif self.type == CONFIG_OPTIONS["RCLT"]:
			return f"{self.lanreceivetotal:.0f}"
		elif self.type == CONFIG_OPTIONS["TMLT"]:
			return f"{self.lantransmittotal:.0f}"
		elif self.type == CONFIG_OPTIONS["RCWT"]:
			return f"{self.wlanreceivetotal:.0f}"
		elif self.type == CONFIG_OPTIONS["TMWT"]:
			return f"{self.wlantransmittotal:.0f}"
		elif self.type == CONFIG_OPTIONS["RCL_MB"]:
			return f"{self.lanreceive:.2f} MB"
		elif self.type == CONFIG_OPTIONS["TML_MB"]:
			return f"{self.lantransmit:.2f} MB"
		elif self.type == CONFIG_OPTIONS["RCW_MB"]:
			return f"{self.wlanreceive:.2f} MB"
		elif self.type == CONFIG_OPTIONS["TMW_MB"]:
			return f"{self.wlantransmit:.2f} MB"
		elif self.type == CONFIG_OPTIONS["RC"]:
			return f"{max(self.lanreceive, self.wlanreceive):.2f}"
		elif self.type == CONFIG_OPTIONS["TM"]:
			return f"{max(self.lantransmit, self.wlantransmit):.2f}"
		elif self.type == CONFIG_OPTIONS["RCT"]:
			return f"{max(self.lanreceivetotal, self.wlanreceivetotal):.0f}"
		elif self.type == CONFIG_OPTIONS["TMT"]:
			return f"{max(self.lantransmittotal, self.wlantransmittotal):.0f}"
		elif self.type == CONFIG_OPTIONS["RC_MB"]:
			return f"{max(self.lanreceive, self.wlanreceive):.2f} MB"
		elif self.type == CONFIG_OPTIONS["TM_MB"]:
			return f"{max(self.lantransmit, self.wlantransmit):.2f} MB"
		elif self.type == CONFIG_OPTIONS["NET_TYP"]:
			return self.nettyp
		elif self.type == CONFIG_OPTIONS["ERR_RCL"]:
			return f"{self.error_lanreceive}"
		elif self.type == CONFIG_OPTIONS["ERR_TML"]:
			return f"{self.error_lantransmit}"
		elif self.type == CONFIG_OPTIONS["DRO_RCL"]:
			return f"{self.drop_lanreceive}"
		elif self.type == CONFIG_OPTIONS["DRO_TML"]:
			return f"{self.drop_lantransmit}"
		elif self.type == CONFIG_OPTIONS["ERR_RCW"]:
			return f"{self.error_wlanreceive}"
		elif self.type == CONFIG_OPTIONS["ERR_TMW"]:
			return f"{self.error_wlantransmit}"
		elif self.type == CONFIG_OPTIONS["DRO_RCW"]:
			return f"{self.drop_wlanreceive}"
		elif self.type == CONFIG_OPTIONS["DRO_TMW"]:
			return f"{self.drop_wlantransmit}"

		return "N/A"

	def changed(self, what):
		"""Handle changes in poll data."""
		if what[0] == self.CHANGED_POLL:
			Converter.changed(self, what)
