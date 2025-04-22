# ServiceInfoEX
# Copyright (c) 2boom 2013-18
# v.1.4.5
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
#
# 26.11.2018 add terrestrial and cable type mod by Sirius
# 01.12.2018 fix video codec mod by Sirius
# 25.12.2018 add support for gamma values mod by Sirius

from Components.Converter.Poll import Poll
from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService
from Components.config import config
from Components.Element import cached
from Tools.Directories import fileExists
import os
import socket
import time
import requests
import gettext
_ = gettext.gettext

if fileExists("/etc/issue"):
	image = ''
	for text in open("/etc/issue"):
		image += text
		if 'open' not in image:
			codec_data = {-1: 'N/A', 0: 'MPEG2', 1: 'MPEG4', 2: 'MPEG1', 3: 'MPEG4-II', 4: 'VC1', 5: 'VC1-SM', 6: 'HEVC', 7: ' '}
			gamma_data = {-1: 'N/A', 0: 'SDR', 1: 'HDR', 2: 'HDR10', 3: 'HLG', 4: ' '}
		else:
			gamma_data = {-1: 'N/A', 0: 'SDR', 1: 'HDR', 2: 'HDR10', 3: 'HLG', 4: ' '}
			codec_data = {-1: 'N/A', 0: 'MPEG2', 1: 'AVC', 2: 'H263', 3: 'VC1', 4: 'MPEG4-VC', 5: 'VC1-SM', 6: 'MPEG1', 7: 'HEVC', 8: 'VP8', 9: 'VP9', 10: 'XVID', 11: 'N/A 11', 12: 'N/A 12', 13: 'DIVX 3', 14: 'DIVX 4', 15: 'DIVX 5', 16: 'AVS', 17: 'N/A 17', 18: 'VP6', 19: 'N/A 19', 20: 'N/A 20', 21: 'SPARK'}

WIDESCREEN = [3, 4, 7, 8, 0xB, 0xC, 0xF, 0x10]


class AglareServiceInfoEX(Poll, Converter, object):
	apid = 0
	vpid = 1
	sid = 2
	onid = 3
	tsid = 4
	prcpid = 5
	pmtpid = 6
	txtpid = 7
	caids = 8
	xres = 9
	yres = 10
	gamma = 11
	atype = 12
	vtype = 13
	avtype = 14
	fps = 15
	tbps = 16
	vsize = 17
	ttype = 18
	format = 19
	XRES = 20
	YRES = 21
	IS_WIDESCREEN = 22
	HAS_TELETEXT = 23
	IS_MULTICHANNEL = 24
	IS_CRYPTED = 25
	SUBSERVICES_AVAILABLE = 26
	AUDIOTRACKS_AVAILABLE = 27
	SUBTITLES_AVAILABLE = 28
	EDITMODE = 29
	FRAMERATE = 30
	IS_FTA = 31
	HAS_HBBTV = 32
	IS_SATELLITE = 33
	IS_CABLE = 34
	IS_TERRESTRIAL = 35
	IS_STREAMTV = 36
	IS_SATELLITE_S = 37
	IS_SATELLITE_S2 = 38
	IS_CABLE_C = 39
	IS_CABLE_C2 = 40
	IS_TERRESTRIAL_T = 41
	IS_TERRESTRIAL_T2 = 42
	volume = 43
	volumedata = 44
	Resolution = 45
	AudioCodec = 46
	VideoCodec = 47
	IPLOCAL = 48
	HDRINFO = 49
	IS_IPTV = 50
	STREAM_FORMAT = 51
	BUFFER_STATUS = 52
	LATENCY = 53
	AUDIO_DETAILS = 54
	HDR_TYPE = 55
	SIGNAL_DB = 56
	PROVIDER_NAME = 57
	ENCRYPTION_TYPE = 58
	SUBTITLE_INFO = 59
	MEDIA_INFO = 60  # New merged item for Resolution, VideoCodec, and AudioCodec
	VSIZE_INFO = 61  # New item for vsize, video codec, and audio codec

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		if type == "apid":
			self.type = self.apid
		elif type == "vpid":
			self.type = self.vpid
		elif type == "sid":
			self.type = self.sid
		elif type == "onid":
			self.type = self.onid
		elif type == "tsid":
			self.type = self.tsid
		elif type == "prcpid":
			self.type = self.prcpid
		elif type == "caids":
			self.type = self.caids
		elif type == "pmtpid":
			self.type = self.pmtpid
		elif type == "txtpid":
			self.type = self.txtpid
		elif type == "tsid":
			self.type = self.tsid
		elif type == "xres":
			self.type = self.xres
		elif type == "yres":
			self.type = self.yres
		elif type == "gamma":
			self.type = self.gamma
		elif type == "atype":
			self.type = self.atype
		elif type == "vtype":
			self.type = self.vtype
		elif type == "avtype":
			self.type = self.avtype
		elif type == "fps":
			self.type = self.fps
		elif type == "tbps":
			self.type = self.tbps
		elif type == "vsize":
			self.type = self.vsize
		elif type == "ttype":
			self.type = self.ttype
		elif type == "VideoWidth":
			self.type = self.XRES
		elif type == "VideoHeight":
			self.type = self.YRES
		elif type == "IsWidescreen":
			self.type = self.IS_WIDESCREEN
		elif type == "HasTelext":
			self.type = self.HAS_TELETEXT
		elif type == "IsMultichannel":
			self.type = self.IS_MULTICHANNEL
		elif type == "IsCrypted":
			self.type = self.IS_CRYPTED
		elif type == "IsFta":
			self.type = self.IS_FTA
		elif type == "HasHBBTV":
			self.type = self.HAS_HBBTV
		elif type == "SubservicesAvailable":
			self.type = self.SUBSERVICES_AVAILABLE
		elif type == "AudioTracksAvailable":
			self.type = self.AUDIOTRACKS_AVAILABLE
		elif type == "SubtitlesAvailable":
			self.type = self.SUBTITLES_AVAILABLE
		elif type == "Editmode":
			self.type = self.EDITMODE
		elif type == "Framerate":
			self.type = self.FRAMERATE
		elif type == "IsSatellite":
			self.type = self.IS_SATELLITE
		elif type == "IsSatelliteS":
			self.type = self.IS_SATELLITE_S
		elif type == "IsSatelliteS2":
			self.type = self.IS_SATELLITE_S2
		elif type == "IsCable":
			self.type = self.IS_CABLE
		elif type == "IsCableC":
			self.type = self.IS_CABLE_C
		elif type == "IsCableC2":
			self.type = self.IS_CABLE_C2
		elif type == "IsTerrestrial":
			self.type = self.IS_TERRESTRIAL
		elif type == "IsTerrestrialT":
			self.type = self.IS_TERRESTRIAL_T
		elif type == "IsTerrestrialT2":
			self.type = self.IS_TERRESTRIAL_T2
		elif type == "IsStreamTV":
			self.type = self.IS_STREAMTV
		elif type == "IsVolume":
			self.type = self.volume
		elif type == "IsVolumeData":
			self.type = self.volumedata
		elif type == "Resolution":
			self.type = self.Resolution
		elif type == "AudioCodec":
			self.type = self.AudioCodec
		elif type == "VideoCodec":
			self.type = self.VideoCodec
		elif type == "Iplocal":
			self.type = self.IPLOCAL
		elif "HDRInfo" in type:
			self.type = self.HDRINFO
		elif type == "IsIPTV":
			self.type = self.IS_IPTV
		elif type == "StreamFormat":
			self.type = self.STREAM_FORMAT
		elif type == "BufferStatus":
			self.type = self.BUFFER_STATUS
		elif type == "Latency":
			self.type = self.LATENCY
		elif type == "AudioDetails":
			self.type = self.AUDIO_DETAILS
		elif type == "HDRType":
			self.type = self.HDR_TYPE
		elif type == "SignalDB":
			self.type = self.SIGNAL_DB
		elif type == "ProviderName":
			self.type = self.PROVIDER_NAME
		elif type == "EncryptionType":
			self.type = self.ENCRYPTION_TYPE
		elif type == "SubtitleInfo":
			self.type = self.SUBTITLE_INFO
		elif type == "MediaInfo":
			self.type = self.MEDIA_INFO
		elif type == "VsizeInfo":
			self.type = self.VSIZE_INFO
		else:
			self.type = self.format
			self.sfmt = type[:]
		self.poll_interval = 1000
		self.poll_enabled = True

	def getServiceInfoString2(self, info, what, convert=lambda x: "%d" % x):
		v = info.getInfo(what)
		if v == -3:
			t_objs = info.getInfoObject(what)
			if t_objs and (len(t_objs) > 0):
				ret_val = ""
				for t_obj in t_objs:
					ret_val += "%.4X " % t_obj
				return ret_val[:-1]
			else:
				return ""
		return convert(v)

	def getServiceInfoString(self, info, what, convert=lambda x: "%d" % x):
		v = info.getInfo(what)
		if v == -1:
			return "N/A"
		if v == -2:
			return info.getInfoString(what)
		return convert(v)

	@cached
	def getText(self):
		self.stream = {'apid': "N/A", 'vpid': "N/A", 'sid': "N/A", 'onid': "N/A", 'tsid': "N/A", 'prcpid': "N/A", 'caids': "FTA", 'pmtpid': "N/A", 'txtpid': "N/A", 'xres': " ", 'yres': " ", 'gamma': " ", 'atype': " ", 'vtype': " ", 'avtype': " ", 'fps': " ", 'tbps': " ", 'vsize': " "}
		streaminfo = ""
		array_caids = []
		service = self.source.service
		info = service and service.info()
		if not info:
			return ""
		gamma_map = {0: "SDR", 1: "HDR", 2: "HDR10", 3: "HLG"}
		if self.getServiceInfoString(info, iServiceInformation.sAudioPID) != "N/A":
			self.stream['apid'] = "%0.4X" % int(self.getServiceInfoString(info, iServiceInformation.sAudioPID))
		if self.getServiceInfoString(info, iServiceInformation.sVideoPID) != "N/A":
			self.stream['vpid'] = "%0.4X" % int(self.getServiceInfoString(info, iServiceInformation.sVideoPID))
		if self.getServiceInfoString(info, iServiceInformation.sSID) != "N/A":
			self.stream['sid'] = "%0.4X" % int(self.getServiceInfoString(info, iServiceInformation.sSID))
		if self.getServiceInfoString(info, iServiceInformation.sONID) != "N/A":
			self.stream['onid'] = "%0.4X" % int(self.getServiceInfoString(info, iServiceInformation.sONID))
		if self.getServiceInfoString(info, iServiceInformation.sTSID) != "N/A":
			self.stream['tsid'] = "%0.4X" % int(self.getServiceInfoString(info, iServiceInformation.sTSID))
		if self.getServiceInfoString(info, iServiceInformation.sPCRPID) != "N/A":
			self.stream['prcpid'] = "%0.4X" % int(self.getServiceInfoString(info, iServiceInformation.sPCRPID))
		if self.getServiceInfoString(info, iServiceInformation.sPMTPID) != "N/A":
			self.stream['pmtpid'] = self.getServiceInfoString(info, iServiceInformation.sPMTPID)
		if self.getServiceInfoString(info, iServiceInformation.sTXTPID) != "N/A":
			self.stream['txtpid'] = self.getServiceInfoString(info, iServiceInformation.sTXTPID)
		caidinfo = self.getServiceInfoString2(info, iServiceInformation.sCAIDs)
		for caid in caidinfo.split():
			array_caids.append(caid)
		self.stream['caids'] = ' '.join(str(x) for x in set(array_caids))
		if self.getServiceInfoString(info, iServiceInformation.sVideoHeight) != "N/A":
			self.stream['yres'] = self.getServiceInfoString(info, iServiceInformation.sVideoHeight) + ("i", "p", "")[info.getInfo(iServiceInformation.sProgressive)]
		if self.getServiceInfoString(info, iServiceInformation.sVideoWidth) != "N/A":
			self.stream['xres'] = self.getServiceInfoString(info, iServiceInformation.sVideoWidth)
		try:
			self.stream['gamma'] = gamma_data[info.getInfo(iServiceInformation.sGamma)]
		except:
			pass
		audio = service.audioTracks()
		if audio:
			if audio.getCurrentTrack() > -1:
				self.stream['atype'] = str(audio.getTrackInfo(audio.getCurrentTrack()).getDescription()).replace(",", "")
		self.stream['vtype'] = codec_data[info.getInfo(iServiceInformation.sVideoType)]
		self.stream['avtype'] = self.stream['vtype'] + '/' + self.stream['atype']
		if self.getServiceInfoString(info, iServiceInformation.sFrameRate, lambda x: "%d" % ((x + 500) / 1000)) != "N/A":
			self.stream['fps'] = self.getServiceInfoString(info, iServiceInformation.sFrameRate, lambda x: "%d" % ((x + 500) / 1000))
		if self.getServiceInfoString(info, iServiceInformation.sTransferBPS, lambda x: "%d kB/s" % (x / 1024)) != "N/A":
			self.stream['tbps'] = self.getServiceInfoString(info, iServiceInformation.sTransferBPS, lambda x: "%d kB/s" % (x / 1024))
		self.tpdata = info.getInfoObject(iServiceInformation.sTransponderData)
		if self.tpdata:
			self.stream['ttype'] = self.tpdata.get('tuner_type', '')
			if self.stream['ttype'] == 'DVB-S' and service.streamed() is None:
				if self.tpdata.get('system', 0) == 1:
					self.stream['ttype'] = 'DVB-S2'
			elif self.stream['ttype'] == 'DVB-C' and service.streamed() is None:
				if self.tpdata.get('system', 0) == 1:
					self.stream['ttype'] = 'DVB-C2'
			elif self.stream['ttype'] == 'DVB-T' and service.streamed() is None:
				if self.tpdata.get('system', 0) == 1:
					self.stream['ttype'] = 'DVB-T2'
		else:
			self.stream['ttype'] = 'IPTV'
		if self.type == self.apid:
			streaminfo = self.stream['apid']
		elif self.type == self.vpid:
			streaminfo = self.stream['vpid']
		elif self.type == self.sid:
			streaminfo = self.stream['sid']
		elif self.type == self.IS_IPTV:
			return "Yes" if service.streamed() is not None else "No"
		elif self.type == self.STREAM_FORMAT:
			url = info.getInfoString(iServiceInformation.sServiceref)
			if url.startswith("http"):
				if "m3u8" in url:
					return "HLS"
				elif "rtsp" in url:
					return "RTSP"
				elif "dash" in url:
					return "MPEG-DASH"
			return "Unknown"
		elif self.type == self.BUFFER_STATUS:
			return f"{info.getInfo(iServiceInformation.sBufferFill)}%"
		elif self.type == self.LATENCY:
			start = time.time()
			try:
				requests.get("http://example.com", timeout=2)
			except:
				return "Timeout"
			return f"{round((time.time() - start) * 1000, 2)} ms"
		elif self.type == self.AUDIO_DETAILS:
			audio = service.audioTracks()
			if audio:
				track = audio.getTrackInfo(audio.getCurrentTrack())
				return f"{track.getDescription()} ({track.getLanguage()})"
			return "N/A"
		elif self.type == self.HDR_TYPE:
			gamma = info.getInfo(iServiceInformation.sGamma)
			return ["SDR", "HDR", "HDR10", "HLG"].get(gamma, "Unknown")
		elif self.type == self.SIGNAL_DB:
			return f"{info.getInfo(iServiceInformation.sSNRdB)} dB"
		elif self.type == self.PROVIDER_NAME:
			return info.getInfoString(iServiceInformation.sProvider)
		elif self.type == self.ENCRYPTION_TYPE:
			caidinfo = info.getInfoObject(iServiceInformation.sCAIDs)
			encryption_map = {0x2600: "Biss", 0xe00: "PowerVU", 0xb00: "Conax", 0x4aee: "BulCrypt", 0x100: "Seca", 0x500: "Viaccess", 0x600: "Irdeto", 0x900: "NDS", 0x1800: "Nagra"}
			return encryption_map.get(caidinfo[0], "Unknown") if caidinfo else "FTA"
		elif self.type == self.SUBTITLE_INFO:
			subtitle = service and service.subtitle()
			subtitlelist = subtitle and subtitle.getSubtitleList()
			return f"{len(subtitlelist)} available" if subtitlelist else "None"
		elif self.type == self.MEDIA_INFO:
			width = info.getInfo(iServiceInformation.sVideoWidth)
			height = info.getInfo(iServiceInformation.sVideoHeight)
			progressive = "p" if info.getInfo(iServiceInformation.sProgressive) == 1 else "i"
			resolution = f"{width}x{height}{progressive}"

			fps_raw = info.getInfo(iServiceInformation.sFrameRate)
			fps = round(fps_raw / 1000, 2) if fps_raw > 0 else "N/A"

			video_codec = codec_data.get(info.getInfo(iServiceInformation.sVideoType), "Unknown")

			audio = service.audioTracks()
			audio_codec = "Unknown"
			audio_language = ""
			if audio and audio.getCurrentTrack() > -1:
				track = audio.getTrackInfo(audio.getCurrentTrack())
				audio_codec = track.getDescription()
				audio_language = track.getLanguage()

			gamma_value = info.getInfo(iServiceInformation.sGamma)
			gamma = gamma_map.get(gamma_value, "Unknown")

			return f"{resolution} {fps}fps | {video_codec} | {audio_codec} ({audio_language}) | {gamma}"
		elif self.type == self.VSIZE_INFO:
			width = info.getInfo(iServiceInformation.sVideoWidth)
			height = info.getInfo(iServiceInformation.sVideoHeight)
			progressive = "p" if info.getInfo(iServiceInformation.sProgressive) == 1 else "i"
			vsize = f"{width}x{height}{progressive}"

			fps_raw = info.getInfo(iServiceInformation.sFrameRate)
			fps = round(fps_raw / 1000, 2) if fps_raw > 0 else "N/A"

			gamma_value = info.getInfo(iServiceInformation.sGamma)
			gamma = gamma_map.get(gamma_value, "Unknown")

			video_codec = codec_data.get(info.getInfo(iServiceInformation.sVideoType), "Unknown")

			audio = service.audioTracks()
			audio_codec = "Unknown"
			audio_language = ""
			if audio and audio.getCurrentTrack() > -1:
				track = audio.getTrackInfo(audio.getCurrentTrack())
				audio_codec = track.getDescription()
				audio_language = track.getLanguage()

			return f"{vsize} | {fps}fps | {gamma} | {video_codec} | {audio_codec} {audio_language}"
		elif self.type == self.onid:
			streaminfo = self.stream['onid']
		elif self.type == self.tsid:
			streaminfo = self.stream['tsid']
		elif self.type == self.prcpid:
			streaminfo = self.stream['prcpid']
		elif self.type == self.caids:
			streaminfo = self.stream['caids']
		elif self.type == self.pmtpid:
			streaminfo = self.stream['pmtpid']
		elif self.type == self.txtpid:
			streaminfo = self.stream['txtpid']
		elif self.type == self.tsid:
			streaminfo = self.stream['tsid']
		elif self.type == self.xres:
			streaminfo = self.stream['xres']
		elif self.type == self.yres:
			streaminfo = self.stream['yres']
		elif self.type == self.gamma:
			streaminfo = self.stream['gamma']
		elif self.type == self.atype:
			streaminfo = self.stream['atype']
		elif self.type == self.vtype:
			streaminfo = self.stream['vtype']
		elif self.type == self.avtype:
			streaminfo = self.stream['avtype']
		elif self.type == self.fps:
			streaminfo = self.stream['fps']
		elif self.type == self.tbps:
			streaminfo = self.stream['tbps']
		elif self.type == self.ttype:
			streaminfo = self.stream['ttype']
		elif self.type == self.volume:
			streaminfo = _('Vol: %s') % config.audio.volume.value
		elif self.type == self.volumedata:
			streaminfo = '%s' % config.audio.volume.value
		elif self.type == self.vsize:
			streaminfo = self.stream['xres'] + 'x' + self.stream['yres'] + '|' + self.stream['fps'] + '|' + self.stream['gamma']
		elif self.type == self.Resolution:
			streaminfo = self.stream['xres'] + 'x' + self.stream['yres'] + self.stream['fps']
		elif self.type == self.AudioCodec:
			return self.createAudioCodec()
		elif self.type == self.VideoCodec:
			return self.createVideoCodec(info)
		if self.type == self.IPLOCAL:
			gw = os.popen("ip -4 route show default").read().split()
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			s.connect((gw[2], 0))
			ipaddr = s.getsockname()[0]
			return "IP : %s" % ipaddr
		elif (self.type == self.HDRINFO):
			return self.hdr(info)
		elif self.type == self.format:
			tmp = self.sfmt[:]
			for param in tmp.split():
				if param != '':
					if param[0] != '%':
						streaminfo += param
					else:
						streaminfo += ' ' + self.stream[param.strip('%')] + '  '
		return streaminfo
	text = property(getText)

	def createVideoCodec(self, info):
		return codec_data.get(info.getInfo(iServiceInformation.sVideoType), "N/A")

	def createAudioCodec(self):
		service = self.source.service
		audio = service.audioTracks()
		if audio:
			try:
				ct = audio.getCurrentTrack()
				i = audio.getTrackInfo(ct)
				languages = i.getLanguage()
				if _("rus") in languages or _("Russian") in languages or _("ru") in languages:
					languages = _("rus")
				elif _("org") in languages:
					languages = _("Original")
				description = i.getDescription()
				return description + "  " + languages
			except:
				return _("unknown")

	def hdr(self, info):
		gamma = info.getInfo(iServiceInformation.sGamma)
		if gamma == 0:
			return "SDR"
		elif gamma == 1:
			return "HDR"
		elif gamma == 2:
			return "HDR10"
		elif gamma == 3:
			return "HLG"
		else:
			return ""

	@cached
	def getValue(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return -1
		if self.type == self.XRES:
			return info.getInfo(iServiceInformation.sVideoWidth)
		if self.type == self.YRES:
			return info.getInfo(iServiceInformation.sVideoHeight)
		if self.type == self.FRAMERATE:
			return info.getInfo(iServiceInformation.sFrameRate)
		return -1
	value = property(getValue)

	@cached
	def getBoolean(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return False
		self.tpdata = info.getInfoObject(iServiceInformation.sTransponderData)
		if self.tpdata:
			type = self.tpdata.get('tuner_type', '')
		else:
			type = 'IP-TV'
		if self.type == self.HAS_TELETEXT:
			tpid = info.getInfo(iServiceInformation.sTXTPID)
			return tpid != -1
		elif self.type == self.IS_MULTICHANNEL:
			audio = service.audioTracks()
			if audio:
				n = audio.getNumberOfTracks()
				idx = 0
				while idx < n:
					i = audio.getTrackInfo(idx)
					description = i.getDescription()
					if "AC3" in description or "AC-3" in description or "DTS" in description:
						return True
					idx += 1
			return False
		elif self.type == self.IS_CRYPTED:
			return info.getInfo(iServiceInformation.sIsCrypted) == 1
		elif self.type == self.IS_FTA:
			return info.getInfo(iServiceInformation.sIsCrypted) == 0
		elif self.type == self.IS_WIDESCREEN:
			return info.getInfo(iServiceInformation.sAspect) in WIDESCREEN
		elif self.type == self.SUBSERVICES_AVAILABLE:
			subservices = service.subServices()
			return subservices and subservices.getNumberOfSubservices() > 0
		elif self.type == self.HAS_HBBTV:
			try:
				return info.getInfoString(iServiceInformation.sHBBTVUrl) != ""
			except:
				pass
		elif self.type == self.AUDIOTRACKS_AVAILABLE:
			audio = service.audioTracks()
			return audio and audio.getNumberOfTracks() > 1
		elif self.type == self.SUBTITLES_AVAILABLE:
			subtitle = service and service.subtitle()
			subtitlelist = subtitle and subtitle.getSubtitleList()
			if subtitlelist:
				return len(subtitlelist) > 0
			return False
		elif self.type == self.EDITMODE:
			return hasattr(self.source, "editmode") and not not self.source.editmode
		elif self.type == self.IS_SATELLITE:
			if type == 'DVB-S':
				return True
		elif self.type == self.IS_CABLE:
			if type == 'DVB-C':
				return True
		elif self.type == self.IS_TERRESTRIAL:
			if type == 'DVB-T':
				return True
		elif self.type == self.IS_STREAMTV:
			if service.streamed() is not None:
				return True
		elif self.type == self.IS_SATELLITE_S:
			if type == 'DVB-S' and service.streamed() is None:
				if self.tpdata.get('system', 0) == 0:
					return True
		elif self.type == self.IS_SATELLITE_S2:
			if type == 'DVB-S' and service.streamed() is None:
				if self.tpdata.get('system', 0) == 1:
					return True
		elif self.type == self.IS_CABLE_C:
			if type == 'DVB-C' and service.streamed() is None:
				if self.tpdata.get('system', 0) == 0:
					return True
		elif self.type == self.IS_CABLE_C2:
			if type == 'DVB-C' and service.streamed() is None:
				if self.tpdata.get('system', 0) == 1:
					return True
		elif self.type == self.IS_TERRESTRIAL_T:
			if type == 'DVB-T' and service.streamed() is None:
				if self.tpdata.get('system', 0) == 0:
					return True
		elif self.type == self.IS_TERRESTRIAL_T2:
			if type == 'DVB-T' and service.streamed() is None:
				if self.tpdata.get('system', 0) == 1:
					return True
		return False
	boolean = property(getBoolean)

	def changed(self, what):
		if what[0] == self.CHANGED_SPECIFIC:
			if what[1] == iPlayableService.evVideoSizeChanged or what[1] == iPlayableService.evUpdatedInfo:
				Converter.changed(self, what)
		elif what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)
		elif what[0] == self.CHANGED_POLL:
			self.downstream_elements.changed(what)
