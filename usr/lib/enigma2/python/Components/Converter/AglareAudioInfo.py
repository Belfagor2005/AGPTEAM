# -*- coding: utf-8 -*-

from enigma import iPlayableService
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Converter.Poll import Poll
import logging
import gettext
_ = gettext.gettext

# 2025.04.01 @ lululla fix


class AglareAudioInfo(Poll, Converter):
	"""Enhanced audio information converter with codec detection and language support"""

	GET_AUDIO_ICON = 0
	GET_AUDIO_CODEC = 1

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.logger = logging.getLogger("AglareAudioInfo")

		# Configuration
		self.poll_interval = 1000  # ms
		self.poll_enabled = True

		# Language settings
		self.lang_strings = ("ger", "german", "deu", "deutsch")
		self.lang_replacements = {
			"und": "",
			"unknown": _("unknown"),
			"": _("unknown")
		}

		# Audio codec definitions
		self.codecs = {
			"01_dolbydigitalplus": ("digital+", "digitalplus", "ac3+", "e-ac3"),
			"02_dolbydigital": ("ac3", "dolbydigital"),
			"03_mp3": ("mp3", "mpeg-1 layer 3"),
			"04_wma": ("wma", "windows media audio"),
			"05_flac": ("flac", "free lossless audio codec"),
			"06_he-aac": ("he-aac", "aac+", "aac plus"),
			"07_aac": ("aac", "advanced audio coding"),
			"08_lpcm": ("lpcm", "linear pcm"),
			"09_dts-hd": ("dts-hd", "dts high definition"),
			"10_dts": ("dts", "digital theater systems"),
			"11_pcm": ("pcm", "pulse-code modulation"),
			"12_mpeg": ("mpeg", "mpeg audio"),
			"13_dolbytruehd": ("truehd", "dolby truehd"),
			"14_atmos": ("atmos", "dolby atmos"),
			"15_opus": ("opus",)
		}

		# Codec variants with channel configurations
		self.codec_info = {
			"dolbydigitalplus": ("51", "20", "71"),
			"dolbydigital": ("51", "20", "71"),
			"wma": ("8", "9"),
			"aac": ("20", "51"),
			"dts": ("51", "61", "71")
		}

		# Initialize converter type
		self.type, self.interesting_events = {
			"AudioIcon": (self.GET_AUDIO_ICON, (iPlayableService.evUpdatedInfo,)),
			"AudioCodec": (self.GET_AUDIO_CODEC, (iPlayableService.evUpdatedInfo,)),
		}.get(type, (self.GET_AUDIO_CODEC, (iPlayableService.evUpdatedInfo,)))

	def getAudio(self):
		"""Get current audio track information"""
		try:
			service = self.source.service
			if not service:
				return False

			audio = service.audioTracks()
			if not audio:
				return False

			self.current_track = audio.getCurrentTrack()
			self.number_of_tracks = audio.getNumberOfTracks()

			if self.number_of_tracks > 0 and self.current_track > -1:
				self.audio_info = audio.getTrackInfo(self.current_track)
				return True

			return False
		except Exception as e:
			self.logger.error(f"Error getting audio info: {str(e)}")
			return False

	def getLanguage(self):
		"""Get and format the audio language"""
		try:
			if not hasattr(self, 'audio_info'):
				return ""

			languages = self.audio_info.getLanguage()
			if not languages:
				return ""

			# Check for German language variants
			if any(lang in languages.lower() for lang in self.lang_strings):
				return "Deutsch"

			# Clean up language string
			for word, replacement in self.lang_replacements.items():
				languages = languages.replace(word, replacement)

			return languages.strip()
		except Exception as e:
			self.logger.warning(f"Error processing language: {str(e)}")
			return ""

	def getAudioCodec(self, info):
		"""Get full audio codec description with language"""
		description_str = _("unknown")

		if self.getAudio():
			languages = self.getLanguage()
			description = self.audio_info.getDescription() or ""

			# Clean and process description
			description_parts = description.split()
			if description_parts and description_parts[0].lower() in languages.lower():
				return languages

			if description.lower() in languages.lower():
				languages = ""

			description_str = f"{description} {languages}".strip()

		return description_str

	def getAudioIcon(self, info):
		"""Get simplified audio codec name for icon display"""
		try:
			codec_name = self.getAudioCodec(info)
			# Clean the codec name for matching
			clean_name = codec_name.translate(
				str.maketrans("", "", " .()")).lower()
			return self._match_audio_codec(clean_name)
		except Exception as e:
			self.logger.error(f"Error getting audio icon: {str(e)}")
			return "unknown"

	def _match_audio_codec(self, audio_name):
		"""Match audio name to known codecs and variants"""
		for return_codec, codecs in sorted(self.codecs.items()):
			for codec in codecs:
				if codec in audio_name:
					base_codec = return_codec.split('_')[1]

					# Check for channel configurations
					if base_codec in self.codec_info:
						for variant in self.codec_info[base_codec]:
							if variant in audio_name:
								return f"{base_codec}{variant}"

					return base_codec

		return audio_name

	@cached
	def getText(self):
		"""Main method to get requested audio information"""
		try:
			service = self.source.service
			if not service:
				return _("No service")

			info = service.info()
			if not info:
				return _("No info")

			if self.type == self.GET_AUDIO_CODEC:
				return self.getAudioCodec(info)
			elif self.type == self.GET_AUDIO_ICON:
				return self.getAudioIcon(info)

		except Exception as e:
			self.logger.error(f"Error in getText: {str(e)}")

		return _("Unknown")

	text = property(getText)

	def changed(self, what):
		"""Handle change events"""
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)

	def destroy(self):
		"""Clean up resources"""
		self.poll_enabled = False
		super().destroy()


# Usage Examples:
# Basic Audio Codec Display:
"""
<widget source="session.CurrentService" render="Label" position="100,100" size="200,25" font="Regular;18">
	<convert type="AglareAudioInfo">AudioCodec</convert>
</widget>
"""
# Audio Icon Display:

"""
<widget source="session.CurrentService" render="Pixmap" position="100,130" size="30,30">
	<convert type="AglareAudioInfo">AudioIcon</convert>
	<convert type="ConditionalShowHide"/>
</widget>
"""
# Combined Audio Info Panel:

"""
<panel position="100,100" size="300,60" backgroundColor="#40000000">
	<widget source="session.CurrentService" render="Pixmap" position="10,10" size="40,40">
		<convert type="AglareAudioInfo">AudioIcon</convert>
		<convert type="ConditionalShowHide"/>
	</widget>
	<widget source="session.CurrentService" render="Label" position="60,15" size="230,30" font="Regular;16">
		<convert type="AglareAudioInfo">AudioCodec</convert>
	</widget>
</panel>
"""
