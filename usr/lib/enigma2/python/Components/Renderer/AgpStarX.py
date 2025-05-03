#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
"""
#########################################################
#                                                       #
#  AGP - Advanced Graphics Renderer                     #
#  Version: 3.5.0                                       #
#  Created by Lululla (https://github.com/Belfagor2005) #
#  License: CC BY-NC-SA 4.0                             #
#  https://creativecommons.org/licenses/by-nc-sa/4.0    #
#                                                       #
#  Last Modified: "15:14 - 20250401"                    #
#                                                       #
#  Credits:                                             #
#   by base code from digiteng 2022                     #
#  - Original concept by Lululla                        #
#  - Advanced download management system                #
#  - Atomic file operations                             #
#  - Thread-safe resource locking                       #
#  - TMDB API integration                               #
#  - TVDB API integration                               #
#  - OMDB API integration                               #
#  - FANART API integration                             #
#  - IMDB API integration                               #
#  - ELCINEMA API integration                           #
#  - GOOGLE API integration                             #
#  - PROGRAMMETV integration                            #
#  - MOLOTOV API integration                            #
#  - Advanced caching system                            #
#  - Fully configurable via AGP Setup Plugin            #
#                                                       #
#  Usage of this code without proper attribution        #
#  is strictly prohibited.                              #
#  For modifications and redistribution,                #
#  please maintain this credit header.                  #
#########################################################
"""
__author__ = "Lululla"
__copyright__ = "AGP Team"

# Standard library imports
import json
from functools import lru_cache
from os import remove
from os.path import exists  # , join
from threading import Lock, Thread, Timer
from urllib.error import HTTPError
from urllib.request import urlopen

# Enigma2 imports
from Components.Renderer.Renderer import Renderer
from Components.VariableValue import VariableValue
from enigma import eEPGCache, eSlider

# Local imports
from Plugins.Extensions.Aglare.plugin import ApiKeyManager, agp_use_cache, config
from .Agp_Utils import POSTER_FOLDER, clean_for_tvdb, logger
from .Agp_lib import quoteEventName

# Constants
api_key_manager = ApiKeyManager()
epgcache = eEPGCache.getInstance()
epgcache.load()


try:
	lng = config.osd.language.value
	lng = lng[:-3]
except:
	lng = 'en'
	pass


"""skin configuration

<widget source="ServiceEvent" render="AgpStarX"
	position="1011,50"
	size="316,27"
	pixmap="skin_default/starsbar_empty.png"
	alphatest="blend"
	transparent="1"
	zPosition="20"/>

<widget source="ServiceEvent" render="AgpStarX"
	position="1011,50"
	size="316,27"
	pixmap="skin_default/starsbar_filled.png"
	alphatest="blend"
	transparent="1"
	zPosition="22"/>

"""


class AgpStarX(VariableValue, Renderer):

	GUI_WIDGET = eSlider

	def __init__(self):
		Renderer.__init__(self)
		VariableValue.__init__(self)
		self.__start = 0
		self.__end = 100
		self.text = ""
		self.current_request = None
		self.lock = Lock()
		self._setup_caching()
		self.last_channel = None
		self.rating_source = config.plugins.Aglare.rating_source.value
		logger.info("AgpStarX Renderer initialized")

	def changed(self, what):
		"""Handle content changes"""
		if what[0] == self.CHANGED_CLEAR:
			(self.range, self.value) = ((0, 1), 0)
			return

		if not self.rating_source:
			(self.range, self.value) = ((0, 1), 0)
			return

		if what[0] != self.CHANGED_CLEAR:
			logger.info('AgpStarX event B what[0] != self.CHANGED_CLEAR')
			if self.instance:
				self.instance.hide()

		self.infos()

	def infos(self):
		if not hasattr(self.source, 'event') or not self.source.event:
			return

		if not self.rating_source:
			return

		try:
			current_event = self.source.event
			if not current_event:
				return

			current_channel = current_event.getEventName()
			if current_channel == self.last_channel:
				return

			self.last_channel = current_channel
			self.pstcanal = clean_for_tvdb(current_channel)

			if self.current_request:
				self.current_request = None

			self.current_request = Thread(target=self.safe_download_info)
			self.current_request.start()

		except Exception as e:
			logger.error(f"AgpStarX Infos error: {str(e)}")

	def _setup_caching(self):
		"""Dynamic caching configuration"""
		if agp_use_cache.value:
			self.cached_download = lru_cache(maxsize=100)(self._safe_download_impl)
		else:
			self.cached_download = self._safe_download_impl

	def safe_download_info(self):
		try:
			with self.lock:
				if not hasattr(self, 'pstcanal') or not self.pstcanal or len(self.pstcanal) < 3:
					return

				info_file = f"{POSTER_FOLDER}/{self.pstcanal}.json"

				# Attempting to read from existing file
				if exists(info_file):
					try:
						with open(info_file, "r") as f:
							data = json.load(f)
						self.process_data(data)
						return
					except Exception as e:
						logger.warning(f"File corrotto, elimino: {info_file} {e}")
						remove(info_file)

				# Download API
				self.api_key = api_key_manager.get_api_key('tmdb')
				if not self.api_key or len(self.pstcanal) < 3:
					return None

				try:
					clean_query = quoteEventName(self.pstcanal.strip())
					url = f"https://api.themoviedb.org/3/search/multi?api_key={self.api_key}&query={clean_query}"

					with urlopen(url, timeout=10) as response:
						if response.status != 200:
							return
						url_data = json.load(response)

					# Cascade Validation
					results = url_data.get('results', [])
					valid_results = [r for r in results if r.get('media_type') in ['movie', 'tv']]

					if not valid_results:
						return

					# Content type control (exclude TV shows)
					best_result = valid_results[0]
					content_type = best_result['media_type']
					content_id = best_result['id']
					details_url = f"https://api.themoviedb.org/3/{content_type}/{content_id}?api_key={self.api_key}"

					with urlopen(details_url, timeout=15) as details_response:
						if details_response.status != 200:
							return
						movie_data = json.load(details_response)

					# Save data
					with open(info_file, "w") as f:
						json.dump(movie_data, f, indent=2)
						# logger.debug(f"AgpStarX Data saved in: {info_file}")

					self.process_data(movie_data)

				except HTTPError as e:
					if e.code == 404:
						logger.debug("AgpStarX Resource not found")
					return
				except Exception as e:
					logger.error(f"AgpStarX Error while downloading: {str(e)}")

		except Exception as e:
			logger.error(f"AgpStarX Critical error: {str(e)}", exc_info=True)

	def _safe_download_impl(self, channel_hash: str):
		"""Basic download implementation with correct parameters"""
		try:
			with self.lock:
				channel_name = self.pstcanal

				self.api_key = api_key_manager.get_api_key('tmdb')
				if not self.api_key or len(self.pstcanal) < 3:
					return None

				clean_query = quoteEventName(channel_name)
				search_url = f"https://api.themoviedb.org/3/search/multi?api_key={self.api_key}&query={clean_query}"

				with urlopen(search_url, timeout=10) as res:
					if res.status != 200:
						return None
					search_data = json.load(res)

				# Processing results
				valid_results = [r for r in search_data.get('results', []) if r.get('media_type') in ['movie', 'tv']]

				if not valid_results:
					return None

				best_result = valid_results[0]
				content_type = best_result['media_type']
				content_id = best_result['id']

				# Request details
				details_url = f"https://api.themoviedb.org/3/{content_type}/{content_id}?api_key={self.api_key}"
				with urlopen(details_url, timeout=15) as detail_res:
					return json.load(detail_res)

		except HTTPError as e:
			if e.code == 404:
				logger.debug("Resource not found")
			return None
		except Exception as e:
			logger.error(f"Error download: {str(e)}")
			return None

	def process_data(self, data):
		try:
			# Delay UI update by 100ms to avoid flickering
			Timer(0.10, self._delayed_ui_update, [data]).start()
		except Exception as e:
			logger.error(f"AgpStarX Process data error: {str(e)}")

	def _delayed_ui_update(self, data):
		try:
			"""
			# Checking for instance existence
			if not self.instance or not hasattr(self.instance, 'show'):
				return
			"""

			if not self.instance:
				return

			# Channel consistency check
			current_event = self.source.event
			if not current_event or current_event.getEventName() != self.last_channel:
				return

			# Data processing and UI update
			rating = data.get('vote_average', 0)
			rtng = min(int(rating * 10), 100) if rating else 0
			with self.lock:
				self.range = (0, 100)
				self.value = rtng
				self.instance.show()

		except Exception as e:
			logger.debug(f"AgpStarX UI update skipped: {str(e)}")

	def postWidgetCreate(self, instance):
		instance.setRange(self.__start, self.__end)

	def setRange(self, range):
		(self.__start, self.__end) = range
		if self.instance is not None:
			self.instance.setRange(self.__start, self.__end)

	def getRange(self):
		return self.__start, self.__end
