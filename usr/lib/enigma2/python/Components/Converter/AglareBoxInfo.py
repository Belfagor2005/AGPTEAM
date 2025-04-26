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

from Components.Converter.Poll import Poll
from Components.Converter.Converter import Converter
from Components.config import config
from Components.Element import cached
from Tools.Directories import fileExists
from os.path import isfile, exists
from os import popen
from re import search
import gettext
_ = gettext.gettext


class AglareBoxInfo(Poll, Converter, object):
	"""Enhanced system information converter for Enigma2"""
	Boxtype = 0
	CpuInfo = 1
	HddTemp = 2
	TempInfo = 3
	FanInfo = 4
	Upinfo = 5
	CpuLoad = 6
	CpuSpeed = 7
	SkinInfo = 8
	TimeInfo = 9
	TimeInfo2 = 10
	TimeInfo3 = 11
	TimeInfo4 = 12
	PythonVersion = 13

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.poll_interval = 2000
		self.poll_enabled = True

		type_map = {
			"Boxtype": self.Boxtype,
			"CpuInfo": self.CpuInfo,
			"HddTemp": self.HddTemp,
			"TempInfo": self.TempInfo,
			"FanInfo": self.FanInfo,
			"Upinfo": self.Upinfo,
			"CpuLoad": self.CpuLoad,
			"CpuSpeed": self.CpuSpeed,
			"SkinInfo": self.SkinInfo,
			"TimeInfo": self.TimeInfo,
			"TimeInfo2": self.TimeInfo2,
			"TimeInfo3": self.TimeInfo3,
			"TimeInfo4": self.TimeInfo4,
			"PythonVersion": self.PythonVersion
		}

		if type in type_map:
			self.type = type_map[type]
		else:
			raise ValueError("Invalid converter type: %s" % type)

	def imageinfo(self):
		imageinfo = ''
		if isfile('/usr/lib/opkg/status'):
			imageinfo = '/usr/lib/opkg/status'
		elif isfile('/usr/lib/ipkg/status'):
			imageinfo = '/usr/lib/ipkg/status'
		elif isfile('/var/lib/opkg/status'):
			imageinfo = '/var/lib/opkg/status'
		elif isfile('/var/opkg/status'):
			imageinfo = '/var/opkg/status'
		return imageinfo

	@cached
	def getText(self):
		if self.type == self.Boxtype:
			box = software = ""

			# Get Enigma version
			if isfile("/proc/version"):
				with open("/proc/version") as f:
					enigma = f.read().split()[2]
					print('enigma version:', enigma)

			# Get box brand and model
			try:
				from Components.SystemInfo import BoxInfo
				DISPLAYBRAND = BoxInfo.getItem("displaybrand")
				if DISPLAYBRAND.startswith("Maxytec"):
					DISPLAYBRAND = "Novaler"
				DISPLAYMODEL = BoxInfo.getItem("displaymodel")
				box = DISPLAYBRAND + " " + DISPLAYMODEL
			except ImportError:
				box = popen("head -n 1 /etc/hostname").read().split()[0]

			# Detect distro info
			if isfile("/etc/issue"):
				try:
					with open("/etc/issue") as f:
						for line in f:
							clean_line = line.capitalize()
							for r in [
								"Open vision enigma2 image for", "More information : https://openvision.tech",
								"%d, %t - (%s %r %m)", "release", "Welcome to openatv", "Welcome to teamblue",
								"Welcome to openbh", "Welcome to openvix", "Welcome to openhdf",
								"Welcome to opendroid", "Welcome to openspa", r"\n", r"\l", r"\\"
							]:
								clean_line = clean_line.replace(r, "")
							software += clean_line.strip().capitalize()[:-1]
				except Exception:
					software = ""

				# Get specific distro version details
				distro_mappings = {
					"Egami": ("displaydistro", "imgversion", "imagedevbuild", " - R "),
					"Openbh": ("displaydistro", "imgversion", "imagebuild", " "),
					"Openvix": ("displaydistro", "imgversion", "imagebuild", " "),
					"Openhdf": ("displaydistro", "imgversion", "imagebuild", " r"),
					"Pure2": ("displaydistro", "imgversion", "imagedevbuild", " - R "),
					"Openatv": ("displaydistro", "imgversion", "", ""),
				}

				for key, (distro, ver, build, sep) in distro_mappings.items():
					if software.startswith(key):
						try:
							from Components.SystemInfo import BoxInfo
							d = BoxInfo.getItem(distro)
							v = BoxInfo.getItem(ver)
							b = BoxInfo.getItem(build) if build else ""
							software = d.upper() + " " + v + sep + b
						except ImportError:
							pass

				software = " : %s " % software.strip()

			# Check vtiversion override
			if isfile("/etc/vtiversion.info"):
				software = ""
				try:
					with open("/etc/vtiversion.info") as f:
						for line in f:
							parts = line.split()
							if len(parts) >= 2:
								software += parts[0].split("-")[0] + " " + parts[-1].replace("\n", "")
					software = " : %s " % software.strip()
				except Exception:
					pass

			return "%s%s" % (box, software)

		elif self.type == self.PythonVersion:
			pythonversion = ''
			try:
				from Screens.About import about
				pythonversion = 'Python' + ' ' + about.getPythonVersionString()
			except (ImportError, AttributeError):
				from sys import version_info
				pythonversion = 'Python' + ' ' + '%s.%s.%s' % (version_info.major, version_info.minor, version_info.micro)
			return '%s' % (pythonversion)

		elif self.type == self.CpuInfo:
			cpu_count = 0
			info = cpu_speed = cpu_info = core = ''
			core = _('core')
			cores = _('cores')
			if isfile('/proc/cpuinfo'):
				for line in open('/proc/cpuinfo'):
					if 'system type' in line:
						info = line.split(':')[-1].split()[0].strip().strip('\n')
					elif 'cpu MHz' in line:
						cpu_speed = line.split(':')[-1].strip().strip('\n')
					elif 'cpu type' in line:
						info = line.split(':')[-1].strip().strip('\n')
					elif 'model name' in line or 'Processor' in line:
						info = line.split(':')[-1].strip().strip('\n').replace('Processor ', '')
					elif line.startswith('processor'):
						cpu_count += 1
				if info.startswith('ARM') and isfile('/proc/stb/info/chipset'):
					for line in open('/proc/cpuinfo'):
						if 'model name' in line or 'Processor' in line:
							info = line.split(':')[-1].split()[0].strip().strip('\n')
							info = '%s (%s)' % (open('/proc/stb/info/chipset').readline().strip().lower().replace('hi3798mv200', 'Hi3798MV200').replace('bcm', 'BCM').replace('brcm', 'BCM').replace('7444', 'BCM7444').replace('7278', 'BCM7278'), info)
				if not cpu_speed:
					try:
						cpu_speed = int(open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq').read()) / 1000
					except:
						try:
							import binascii
							f = open('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency', 'rb')
							clockfrequency = f.read()
							f.close()
							cpu_speed = "%s" % str(int(binascii.hexlify(clockfrequency), 16) / 1000000)
						except:
							cpu_speed = '-'
				if cpu_info == '':
					return _('%s, %s MHz (%d %s)') % (info, cpu_speed, cpu_count, cpu_count > 1 and cores or core)
			else:
				return _('No info')

		elif self.type == self.HddTemp:
			textvalue = 'No info'
			info = 'N/A'
			try:
				out_line = popen('hddtemp -n -q /dev/sda').readline()
				info = 'HDD: Temp:' + out_line[:2] + str('\xc2\xb0') + 'C'
				textvalue = info
			except:
				pass
			return textvalue

		elif self.type == self.TempInfo:
			info = "N/A"
			try:
				if exists("/proc/stb/sensors/temp0/value") and exists("/proc/stb/sensors/temp0/unit"):
					with open("/proc/stb/sensors/temp0/value") as f_val, open("/proc/stb/sensors/temp0/unit") as f_unit:
						value = f_val.read().strip()
						unit = f_unit.read().strip()
						info = "%s%s%s" % (value, "\xc2\xb0", unit)
				elif exists("/proc/stb/fp/temp_sensor_avs"):
					with open("/proc/stb/fp/temp_sensor_avs") as f:
						info = "%s%sC" % (f.read().strip(), "\xc2\xb0")
				elif exists("/proc/stb/fp/temp_sensor"):
					with open("/proc/stb/fp/temp_sensor") as f:
						info = "%s%sC" % (f.read().strip(), "\xc2\xb0")
				elif exists("/sys/devices/virtual/thermal/thermal_zone0/temp"):
					with open("/sys/devices/virtual/thermal/thermal_zone0/temp") as f:
						temp = f.read().strip()
						info = "%s%sC" % (temp[:2], "\xc2\xb0")
				elif exists("/proc/hisi/msp/pm_cpu"):
					try:
						with open("/proc/hisi/msp/pm_cpu") as f:
							match = search(r"temperature = (\d+) degree", f.read())
							if match:
								info = "%s%sC" % (match.group(1), "\xc2\xb0")
					except Exception:
						pass
			except Exception:
				info = "N/A"

			return info

		elif self.type == self.FanInfo:
			info = 'N/A'
			try:
				if exists('/proc/stb/fp/fan_speed'):
					info = open('/proc/stb/fp/fan_speed').read().strip('\n')
				elif exists('/proc/stb/fp/fan_pwm'):
					info = open('/proc/stb/fp/fan_pwm').read().strip('\n')
			except:
				info = 'N/A'
			if self.type is self.FanInfo:
				info = 'Fan: ' + info
			return info

		elif self.type == self.Upinfo:
			try:
				with open('/proc/uptime', 'r') as file:
					uptime_info = file.read().split()
			except:
				return ' '
				uptime_info = None
			if uptime_info is not None:
				total_seconds = float(uptime_info[0])
				MINUTE = 60
				HOUR = MINUTE * 60
				DAY = HOUR * 24
				days = int(total_seconds / DAY)
				hours = int((total_seconds % DAY) / HOUR)
				minutes = int((total_seconds % HOUR) / MINUTE)
				# seconds = int(total_seconds % MINUTE)
				uptime = ''
				if days > 0:
					uptime += str(days) + ' ' + (days == 1 and 'day' or 'days') + ' '
				if len(uptime) > 0 or hours > 0:
					uptime += str(hours) + ' ' + (hours == 1 and 'hour' or 'hours') + ' '
				if len(uptime) > 0 or minutes > 0:
					uptime += str(minutes) + ' ' + (minutes == 1 and 'minute' or 'minutes')
				return 'Time in work: %s' % uptime

		elif self.type == self.CpuLoad:
			info = ""
			load = ""
			try:
				if exists("/proc/loadavg"):
					with open("/proc/loadavg", "r") as ls:
						load = ls.readline(4)
			except Exception as e:
				print("Failed to read /proc/loadavg: " + str(e))
			info = load.replace("\n", "").replace(" ", "")
			return _("CPU Load: %s") % info

		elif self.type == self.CpuSpeed:
			info = 0
			try:
				for line in open('/proc/cpuinfo').readlines():
					line = [x.strip() for x in line.strip().split(':')]
					if line[0] == 'cpu MHz':
						info = '%1.0f' % float(line[1])
				if not info:
					try:
						info = int(open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq').read()) / 1000
					except:
						try:
							import binascii
							info = int(int(binascii.hexlify(open('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency', 'rb').read()), 16) / 100000000) * 100
						except:
							info = '-'
				return 'CPU Speed: %s MHz' % info
			except:
				return ''

		elif self.type == self.SkinInfo:
			if fileExists('/etc/enigma2/settings'):
				try:
					for line in open('/etc/enigma2/settings'):
						if 'config.skin.primary_skin' in line:
							return (_('Skin: ')) + line.replace('/skin.xml', ' ').split('=')[1]
				except:
					return

		elif self.type == self.TimeInfo:
			if not config.timezone.val.value.startswith('(GMT)'):
				return config.timezone.val.value[4:7]
			else:
				return '+0'

		elif self.type == self.TimeInfo2:
			if not config.timezone.val.value.startswith('(GMT)'):
				return (_('Timezone: ')) + config.timezone.val.value[0:10]
			else:
				return (_('Timezone: ')) + 'GMT+00:00'

		elif self.type == self.TimeInfo3:
			if not config.timezone.val.value.startswith('(GMT)'):
				return (_('Timezone:')) + config.timezone.val.value[0:20]
			else:
				return '+0'

		elif self.type == self.TimeInfo4:
			if not config.timezone.area.value.startswith('(GMT)'):
				return (_('Part~of~the~light:')) + config.timezone.area.value[0:12]
			else:
				return '+0'

	text = property(getText)
