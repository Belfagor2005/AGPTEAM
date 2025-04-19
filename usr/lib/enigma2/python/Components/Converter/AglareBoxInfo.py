# -*- coding: utf-8 -*-

# ArBoxInfo
# Copyright (c) Tikhon 2019
# v.1.0
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
# update from #lululla 20250401

import os
import re
import logging
from subprocess import Popen, PIPE
from datetime import timedelta
from Components.Converter.Poll import Poll
from Components.Converter.Converter import Converter
from Components.config import config
from Components.Element import cached
from Tools.Directories import fileExists


class AglareBoxInfo(Poll, Converter):
	"""Enhanced system information converter for Enigma2"""

	# Info types
	BOX_TYPE = 0
	CPU_INFO = 1
	HDD_TEMP = 2
	TEMP_INFO = 3
	FAN_INFO = 4
	UPTIME_INFO = 5
	CPU_LOAD = 6
	CPU_SPEED = 7
	SKIN_INFO = 8
	TIMEZONE_OFFSET = 9
	TIMEZONE_NAME = 10
	TIMEZONE_FULL = 11
	TIMEZONE_AREA = 12

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.logger = logging.getLogger("AglareBoxInfo")

		# Configuration
		self.poll_interval = 2000  # 2 seconds
		self.poll_enabled = True
		self.temp_unit = "°C"

		# Type mapping
		self.type_mapping = {
			'Boxtype': self.BOX_TYPE,
			'CpuInfo': self.CPU_INFO,
			'HddTemp': self.HDD_TEMP,
			'TempInfo': self.TEMP_INFO,
			'FanInfo': self.FAN_INFO,
			'Upinfo': self.UPTIME_INFO,
			'CpuLoad': self.CPU_LOAD,
			'CpuSpeed': self.CPU_SPEED,
			'SkinInfo': self.SKIN_INFO,
			'TimeInfo': self.TIMEZONE_OFFSET,
			'TimeInfo2': self.TIMEZONE_NAME,
			'TimeInfo3': self.TIMEZONE_FULL,
			'TimeInfo4': self.TIMEZONE_AREA
		}

		try:
			self.type = self.type_mapping[type]
		except KeyError:
			self.type = self.BOX_TYPE
			self.logger.warning(f"Unknown type '{type}', defaulting to Boxtype")

	def execute_command(self, command):
		"""Safely execute shell command and return output"""
		try:
			with Popen(command, shell=True, stdout=PIPE, stderr=PIPE) as process:
				output, error = process.communicate()
				if process.returncode == 0:
					return output.decode('utf-8').strip()
				self.logger.debug(f"Command failed: {command}, Error: {error.decode('utf-8')}")
		except Exception as e:
			self.logger.warning(f"Command execution error: {str(e)}")
		return None

	def get_distro_info(self):
		"""Get distribution information from various sources"""
		distro_info = ""

		# Check common issue file locations
		issue_files = [
			'/etc/issue',
			'/etc/issue.net',
			'/etc/os-release',
			'/etc/openvision/distro'
		]

		for file in issue_files:
			if os.path.isfile(file):
				try:
					with open(file, 'r') as f:
						content = f.read()
						# Clean up the content
						distro_info = content.split('\n')[0]
						distro_info = re.sub(r'\\[a-zA-Z]', '', distro_info)  # Remove escape sequences
						distro_info = re.sub(r'Welcome to ', '', distro_info, flags=re.IGNORECASE)
						distro_info = distro_info.strip()
						if distro_info:
							return distro_info
				except Exception as e:
					self.logger.debug(f"Error reading {file}: {str(e)}")

		return "Unknown"

	@cached
	def getText(self):
		"""Main method to get requested information"""
		try:
			if self.type == self.BOX_TYPE:
				return self._get_box_info()
			elif self.type == self.CPU_INFO:
				return self._get_cpu_info()
			elif self.type == self.HDD_TEMP:
				return self._get_hdd_temp()
			elif self.type == self.TEMP_INFO:
				return self._get_temp_info()
			elif self.type == self.FAN_INFO:
				return self._get_fan_info()
			elif self.type == self.UPTIME_INFO:
				return self._get_uptime_info()
			elif self.type == self.CPU_LOAD:
				return self._get_cpu_load()
			elif self.type == self.CPU_SPEED:
				return self._get_cpu_speed()
			elif self.type == self.SKIN_INFO:
				return self._get_skin_info()
			elif self.type in (self.TIMEZONE_OFFSET, self.TIMEZONE_NAME,
							   self.TIMEZONE_FULL, self.TIMEZONE_AREA):
				return self._get_timezone_info()
		except Exception as e:
			self.logger.error(f"Error in getText: {str(e)}")
			return "N/A"

	def _get_box_info(self):
		"""Get box model and software information"""
		try:
			# Try to get box info from SystemInfo first
			from Components.SystemInfo import BoxInfo
			brand = BoxInfo.getItem("displaybrand", "Unknown")
			model = BoxInfo.getItem("displaymodel", "Unknown")

			# Special case for Maxytec
			if brand.startswith('Maxytec'):
				brand = 'Novaler'

			box_info = f"{brand} {model}"
		except ImportError:
			# Fallback to hostname
			box_info = os.popen("head -n 1 /etc/hostname").read().split()[0] or "Unknown"

		# Get software info
		software_info = self.get_distro_info()

		return f"{box_info} : {software_info}"

	def _get_cpu_info(self):
		"""Get detailed CPU information"""
		cpu_info = {
			'model': "Unknown",
			'speed': "0",
			'cores': 0,
			'vendor': "Unknown"
		}

		if os.path.isfile('/proc/cpuinfo'):
			with open('/proc/cpuinfo', 'r') as f:
				for line in f:
					line = line.strip()
					if not line:
						continue

					key, sep, value = line.partition(':')
					key = key.strip()
					value = value.strip()

					if key == 'model name' or key == 'Processor':
						cpu_info['model'] = value.replace('Processor', '').strip()
					elif key == 'cpu MHz':
						cpu_info['speed'] = value
					elif key == 'system type':
						cpu_info['model'] = value.split()[0]
					elif key == 'cpu type':
						cpu_info['model'] = value
					elif key == 'vendor_id':
						cpu_info['vendor'] = value
					elif line.startswith('processor'):
						cpu_info['cores'] += 1

		# Special handling for ARM devices
		if cpu_info['model'].startswith('ARM') and os.path.isfile('/proc/stb/info/chipset'):
			try:
				with open('/proc/stb/info/chipset', 'r') as f:
					chipset = f.readline().strip()
					# Clean up chipset name
					chipset = chipset.replace('hi3798mv200', 'Hi3798MV200')
					chipset = re.sub(r'bcm|brcm', 'BCM', chipset, flags=re.IGNORECASE)
					chipset = chipset.replace('7444', 'BCM7444').replace('7278', 'BCM7278')
				cpu_info['model'] = f"{chipset} ({cpu_info['model']})"
			except Exception as e:
				self.logger.debug(f"Error reading chipset info: {str(e)}")

		# Try alternative methods to get CPU speed
		if cpu_info['speed'] == "0":
			try:
				# Try sysfs first
				with open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq', 'r') as f:
					cpu_info['speed'] = str(int(f.read()) / 1000)
			except:
				try:
					# Try device tree
					import binascii
					with open('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency', 'rb') as f:
						clock = int(binascii.hexlify(f.read()), 16)
						cpu_info['speed'] = str(clock / 1000000)
				except:
					cpu_info['speed'] = "-"

		# Format output
		cores_text = "cores" if cpu_info['cores'] > 1 else "core"
		return f"{cpu_info['model']}, {cpu_info['speed']} MHz ({cpu_info['cores']} {cores_text})"

	def _get_hdd_temp(self):
		"""Get HDD temperature"""
		if not os.path.exists('/dev/sda'):
			return "HDD: Not detected"

		# Try hddtemp first
		temp = self.execute_command('hddtemp -n -q /dev/sda')
		if temp and temp.isdigit():
			return f"HDD: Temp: {temp}{self.temp_unit}"

		# Try smartctl as fallback
		temp = self.execute_command('smartctl -A /dev/sda | grep Temperature_Celsius')
		if temp:
			match = re.search(r'\d+', temp)
			if match:
				return f"HDD: Temp: {match.group()}{self.temp_unit}"

		return "HDD: Temp: N/A"

	def _get_temp_info(self):
		"""Get system temperature from various sources"""
		temp_sources = [
			('/proc/stb/sensors/temp0/value', '/proc/stb/sensors/temp0/unit'),
			('/proc/stb/fp/temp_sensor_avs', None),
			('/proc/stb/fp/temp_sensor', None),
			('/sys/devices/virtual/thermal/thermal_zone0/temp', None),
			('/proc/hisi/msp/pm_cpu', r'temperature = (\d+) degree')
		]

		for source, unit_source in temp_sources:
			if os.path.exists(source):
				try:
					with open(source, 'r') as f:
						content = f.read()
						if unit_source:
							# Read unit from separate file
							with open(unit_source, 'r') as uf:
								unit = uf.read().strip()
						elif source == '/sys/devices/virtual/thermal/thermal_zone0/temp':
							# Special handling for thermal zone (value is in millidegrees)
							temp = str(int(content) // 1000)
							unit = "C"
						elif source == '/proc/hisi/msp/pm_cpu':
							# Special handling for hisi format
							match = re.search(r'temperature = (\d+) degree', content)
							if match:
								temp = match.group(1)
								unit = "C"
							else:
								continue
						else:
							# Default case
							temp = content.strip()
							unit = "C"

						return f"{temp}{self.temp_unit}{unit}"
				except Exception as e:
					self.logger.debug(f"Error reading temperature from {source}: {str(e)}")
					continue

		return f"N/A{self.temp_unit}"

	def _get_fan_info(self):
		"""Get fan speed information"""
		fan_sources = [
			'/proc/stb/fp/fan_speed',
			'/proc/stb/fp/fan_pwm',
			'/sys/class/hwmon/hwmon0/fan1_input'
		]

		for source in fan_sources:
			if os.path.exists(source):
				try:
					with open(source, 'r') as f:
						speed = f.read().strip()
						return f"Fan: {speed} RPM"
				except Exception as e:
					self.logger.debug(f"Error reading fan speed from {source}: {str(e)}")
					continue

		return "Fan: N/A"

	def _get_uptime_info(self):
		"""Get system uptime information"""
		try:
			with open('/proc/uptime', 'r') as f:
				uptime_seconds = float(f.readline().split()[0])

			uptime = timedelta(seconds=uptime_seconds)
			days = uptime.days
			hours = uptime.seconds // 3600
			minutes = (uptime.seconds % 3600) // 60

			parts = []
			if days > 0:
				parts.append(f"{days} {'day' if days == 1 else 'days'}")
			if hours > 0:
				parts.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
			if minutes > 0 or not parts:
				parts.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")

			return "Uptime: " + " ".join(parts)
		except Exception as e:
			self.logger.warning(f"Error getting uptime: {str(e)}")
			return "Uptime: N/A"

	def _get_cpu_load(self):
		"""Get current CPU load average"""
		try:
			with open('/proc/loadavg', 'r') as f:
				load = f.readline().split()[0]
			return f"CPU Load: {load}"
		except Exception as e:
			self.logger.warning(f"Error getting CPU load: {str(e)}")
			return "CPU Load: N/A"

	def _get_cpu_speed(self):
		"""Get current CPU speed"""
		try:
			# Try sysfs first
			if os.path.exists('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq'):
				with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq', 'r') as f:
					speed = int(f.read()) / 1000
				return f"CPU Speed: {speed:.0f} MHz"

			# Fallback to cpuinfo
			if os.path.exists('/proc/cpuinfo'):
				with open('/proc/cpuinfo', 'r') as f:
					for line in f:
						if 'cpu MHz' in line:
							speed = float(line.split(':')[1].strip())
							return f"CPU Speed: {speed:.0f} MHz"

			# Try device tree as last resort
			if os.path.exists('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency'):
				import binascii
				with open('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency', 'rb') as f:
					speed = int(binascii.hexlify(f.read()), 16) / 1000000
				return f"CPU Speed: {speed:.0f} MHz"

			return "CPU Speed: N/A"
		except Exception as e:
			self.logger.warning(f"Error getting CPU speed: {str(e)}")
			return "CPU Speed: N/A"

	def _get_skin_info(self):
		"""Get current skin information"""
		settings_file = '/etc/enigma2/settings'
		if not fileExists(settings_file):
			return "Skin: N/A"

		try:
			with open(settings_file, 'r') as f:
				for line in f:
					if line.startswith('config.skin.primary_skin='):
						skin = line.split('=')[1].strip()
						skin = skin.replace('/skin.xml', '')
						return f"Skin: {skin}"
			return "Skin: Default"
		except Exception as e:
			self.logger.warning(f"Error reading skin info: {str(e)}")
			return "Skin: N/A"

	def _get_timezone_info(self):
		"""Get timezone information"""
		try:
			tz_value = config.timezone.val.value
			tz_area = config.timezone.area.value

			if self.type == self.TIMEZONE_OFFSET:
				if not tz_value.startswith('(GMT)'):
					return tz_value[4:7]
				return "+0"
			elif self.type == self.TIMEZONE_NAME:
				if not tz_value.startswith('(GMT)'):
					return f"Timezone: {tz_value[:10]}"
				return "Timezone: GMT+00:00"
			elif self.type == self.TIMEZONE_FULL:
				if not tz_value.startswith('(GMT)'):
					return f"Timezone: {tz_value[:20]}"
				return "+0"
			elif self.type == self.TIMEZONE_AREA:
				if not tz_area.startswith('(GMT)'):
					return f"Area: {tz_area[:12]}"
				return "+0"
		except Exception as e:
			self.logger.warning(f"Error getting timezone info: {str(e)}")
			return "N/A"

	text = property(getText)

	def destroy(self):
		"""Clean up resources"""
		self.poll_enabled = False
		super().destroy()
