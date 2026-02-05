# -*- coding: utf-8 -*-
# ArBoxInfo
# Copyright (c) Tikhon 2019
# v.1.1
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
import subprocess
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
    GstreamerVersion = 14
    KernelVersion = 15
    OpenSslVersion = 16

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
            "PythonVersion": self.PythonVersion,
            "GstreamerVersion": self.GstreamerVersion,
            "KernelVersion": self.KernelVersion,
            "OpenSslVersion": self.OpenSslVersion
        }

        if type in type_map:
            self.type = type_map[type]
        else:
            raise ValueError("Invalid converter type: %s" % type)

    def imageinfo(self):
        """Find the package status file for image information"""
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

    def get_gstreamer_version(self):
        """Get GStreamer version information"""
        try:
            # Try to get version from gst-launch
            if fileExists('/usr/bin/gst-launch-1.0'):
                output = popen('/usr/bin/gst-launch-1.0 --version').read().strip()
                if output:
                    return output.split()[-1] if 'gst-launch' in output else output

            # Try alternative locations
            for cmd in ['/usr/bin/gst-launch', 'gst-launch-1.0', 'gst-launch']:
                try:
                    output = subprocess.check_output([cmd, '--version'], stderr=subprocess.STDOUT).decode().strip()
                    if output:
                        return output.split()[-1] if 'gst-launch' in output else output
                except (OSError, subprocess.CalledProcessError):
                    continue

            return _("Not available")
        except Exception as e:
            print("Error getting GStreamer version:", str(e))
            return _("Error")

    def get_kernel_version(self):
        """Get kernel version information"""
        try:
            if isfile("/proc/version"):
                with open("/proc/version", "r") as f:
                    return f.read().split()[2]  # Kernel version is typically the third field
            return _("Not available")
        except Exception as e:
            print("Error getting kernel version:", str(e))
            return _("Error")

    def get_openssl_version(self):
        """Get OpenSSL version information"""
        try:
            # Try to get version from openssl binary
            if fileExists('/usr/bin/openssl'):
                output = popen('/usr/bin/openssl version').read().strip()
                if output:
                    return output.split()[1]  # Usually returns "OpenSSL 1.x.x"

            # Try alternative locations
            for cmd in ['/usr/bin/openssl', 'openssl']:
                try:
                    output = subprocess.check_output([cmd, 'version'], stderr=subprocess.STDOUT).decode().strip()
                    if output:
                        return output.split()[1]
                except (OSError, subprocess.CalledProcessError):
                    continue

            # Try Python ssl module as fallback
            try:
                import ssl
                return ssl.OPENSSL_VERSION.split()[1]
            except ImportError:
                pass

            return _("Not available")
        except Exception as e:
            print("Error getting OpenSSL version:", str(e))
            return _("Error")

    @cached
    def getText(self):
        if self.type == self.Boxtype:
            box = software = ""

            # Get Enigma version
            enigma = ""
            if isfile("/proc/version"):
                try:
                    with open("/proc/version", "r") as f:
                        enigma = f.read().split()[2]
                        print("Enigma version:", str(enigma))
                except Exception as e:
                    print("Error reading /proc/version:", str(e))

            # Get box brand and model
            try:
                from Components.SystemInfo import BoxInfo
                DISPLAYBRAND = BoxInfo.getItem("displaybrand")
                if DISPLAYBRAND.startswith("Maxytec"):
                    DISPLAYBRAND = "Novaler"
                DISPLAYMODEL = BoxInfo.getItem("displaymodel")
                box = DISPLAYBRAND + " " + DISPLAYMODEL
            except ImportError:
                try:
                    box = popen("head -n 1 /etc/hostname").read().split()[0]
                except Exception:
                    box = _("Unknown")

            # Detect distro info
            if isfile("/etc/issue"):
                try:
                    with open("/etc/issue", "r") as f:
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
                except Exception as e:
                    print("Error reading /etc/issue:", str(e))
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

                software = "%s " % software.strip()

            # Check vtiversion override
            if isfile("/etc/vtiversion.info"):
                software = ""
                try:
                    with open("/etc/vtiversion.info", "r") as f:
                        for line in f:
                            parts = line.split()
                            if len(parts) >= 2:
                                software += parts[0].split("-")[0] + " " + parts[-1].replace("\n", "")
                    software = " : %s " % software.strip()
                except Exception as e:
                    print("Error reading /etc/vtiversion.info:", str(e))
                    pass

            # Force Pure2 , Egami"
            try:
                from Components.SystemInfo import BoxInfo
                distro = (BoxInfo.getItem("displaydistro") or "").upper()

                if distro == "PURE2":
                    v = BoxInfo.getItem("imgversion") or ""
                    b = BoxInfo.getItem("imagedevbuild") or ""
                    software = " : %s %s-%s" % (distro, v, b)

                elif distro == "EGAMI":
                    v = BoxInfo.getItem("imgversion") or BoxInfo.getItem("imageversion") or ""
                    software = "Egami %s" % v

                elif distro == "OPENBH":
                    v = BoxInfo.getItem("imgversion") or BoxInfo.getItem("imageversion") or ""
                    b = BoxInfo.getItem("imagebuild") or BoxInfo.getItem("imgrevision") or ""
                    software = "%s %s-%s" % (distro, v, b)

            except Exception:
                pass
            return "%s : %s" % (box, software)

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
                try:
                    with open('/proc/cpuinfo', 'r') as f:
                        for line in f:
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
                        try:
                            with open('/proc/stb/info/chipset', 'r') as f:
                                chipset = f.readline().strip().lower()
                                chipset = chipset.replace('hi3798mv200', 'Hi3798MV200')
                                chipset = chipset.replace('bcm', 'BCM').replace('brcm', 'BCM')
                                chipset = chipset.replace('7444', 'BCM7444').replace('7278', 'BCM7278')
                                info = '%s (%s)' % (chipset, info)
                        except Exception:
                            pass
                    if not cpu_speed:
                        try:
                            with open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq', 'r') as f:
                                cpu_speed = int(f.read()) / 1000
                        except Exception:
                            try:
                                import binascii
                                with open('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency', 'rb') as f:
                                    clockfrequency = f.read()
                                cpu_speed = "%s" % str(int(binascii.hexlify(clockfrequency), 16) / 1000000)
                            except Exception:
                                cpu_speed = '-'
                    if cpu_info == '':
                        return _('%s, %s MHz (%d %s)') % (info, cpu_speed, cpu_count, cpu_count > 1 and cores or core)
                except Exception as e:
                    print("Error reading CPU info:", str(e))
                    return _('Error')
            else:
                return _('No info')

        elif self.type == self.HddTemp:
            textvalue = 'No info'
            info = 'N/A'
            try:
                out_line = popen('hddtemp -n -q /dev/sda').readline()
                info = 'HDD: Temp:' + out_line[:2] + str('\xc2\xb0') + 'C'
                textvalue = info
            except Exception:
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
                            content = f.read()
                            match = search(r"temperature = (\d+) degree", content)
                            if match:
                                info = "%s%sC" % (match.group(1), "\xc2\xb0")
                    except Exception:
                        pass
            except Exception as e:
                print("Error reading temperature:", str(e))
                info = "N/A"

            return info

        elif self.type == self.FanInfo:
            info = 'N/A'
            try:
                if exists('/proc/stb/fp/fan_speed'):
                    with open('/proc/stb/fp/fan_speed', 'r') as f:
                        info = f.read().strip('\n')
                elif exists('/proc/stb/fp/fan_pwm'):
                    with open('/proc/stb/fp/fan_pwm', 'r') as f:
                        info = f.read().strip('\n')
            except Exception as e:
                print("Error reading fan info:", str(e))
                info = 'N/A'
            if self.type is self.FanInfo:
                info = 'Fan: ' + info
            return info

        elif self.type == self.Upinfo:
            try:
                with open('/proc/uptime', 'r') as file:
                    uptime_info = file.read().split()
            except Exception as e:
                print("Error reading uptime:", str(e))
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
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        line = [x.strip() for x in line.strip().split(':')]
                        if line[0] == 'cpu MHz':
                            info = '%1.0f' % float(line[1])
                if not info:
                    try:
                        with open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq', 'r') as f:
                            info = int(f.read()) / 1000
                    except Exception:
                        try:
                            import binascii
                            with open('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency', 'rb') as f:
                                clock_data = f.read()
                            info = int(int(binascii.hexlify(clock_data), 16) / 100000000) * 100
                        except Exception:
                            info = '-'
                return 'CPU Speed: %s MHz' % info
            except Exception as e:
                print("Error reading CPU speed:", str(e))
                return ''

        elif self.type == self.SkinInfo:
            if fileExists('/etc/enigma2/settings'):
                try:
                    with open('/etc/enigma2/settings', 'r') as f:
                        for line in f:
                            if 'config.skin.primary_skin' in line:
                                return (_('Skin: ')) + line.replace('/skin.xml', ' ').split('=')[1]
                except Exception as e:
                    print("Error reading skin info:", str(e))
                    return _("Error")
            return _("Not available")

        elif self.type == self.TimeInfo:
            try:
                if not config.timezone.val.value.startswith('(GMT)'):
                    return config.timezone.val.value[4:7]
                else:
                    return '+0'
            except Exception:
                return '+0'

        elif self.type == self.TimeInfo2:
            try:
                if not config.timezone.val.value.startswith('(GMT)'):
                    return (_('Timezone: ')) + config.timezone.val.value[0:10]
                else:
                    return (_('Timezone: ')) + 'GMT+00:00'
            except Exception:
                return (_('Timezone: ')) + 'GMT+00:00'

        elif self.type == self.TimeInfo3:
            try:
                if not config.timezone.val.value.startswith('(GMT)'):
                    return (_('Timezone:')) + config.timezone.val.value[0:20]
                else:
                    return '+0'
            except Exception:
                return '+0'

        elif self.type == self.TimeInfo4:
            try:
                if not config.timezone.area.value.startswith('(GMT)'):
                    return (_('Part~of~the~light:')) + config.timezone.area.value[0:12]
                else:
                    return '+0'
            except Exception:
                return '+0'

        elif self.type == self.GstreamerVersion:
            return _("GStreamer: %s") % self.get_gstreamer_version()

        elif self.type == self.KernelVersion:
            return _("Kernel: %s") % self.get_kernel_version()

        elif self.type == self.OpenSslVersion:
            return _("OpenSSL: %s") % self.get_openssl_version()

    text = property(getText)
