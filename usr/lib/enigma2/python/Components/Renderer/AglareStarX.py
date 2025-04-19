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
#  - TMDB API integration                               #
#  - TVDB API integration                               #
#  - OMDB API integration                               #
#  - Advanced caching system                            #
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
from hashlib import md5
from os.path import join, exists
# Enigma2 imports
from enigma import eSlider, eEPGCache
from Components.Renderer.Renderer import Renderer
from Components.Sources.CurrentService import CurrentService
from Components.Sources.Event import Event
from Components.Sources.EventInfo import EventInfo
from Components.Sources.ServiceEvent import ServiceEvent
from Components.VariableValue import VariableValue
from Components.config import config

import NavigationInstance
from ServiceReference import ServiceReference

# Local imports
from .Agp_Utils import POSTER_FOLDER, clean_for_tvdb, clean_filename, logger

# Constants
epgcache = eEPGCache.getInstance()
epgcache.load()


"""skin configuration"""
"""
<widget source="Event" render="AglareStarX" position="x,y" size="width,height"
	rating_source="imdb" display_mode="stars5" />
"""
"""
<widget source="Event" render="AglareStarX" position="x,y" size="width,height"
	rating_source="tmdb" display_mode="stars10" />
"""


class AglareStarX(VariableValue, Renderer):
	"""Renderer for displaying star ratings from TMDB/IMDB data"""
	GUI_WIDGET = eSlider

	def __init__(self):
		super().__init__()
		VariableValue.__init__(self)
		self.__start = 0
		self.__end = 100
		self.canal = [None] * 6
		self.quick_cache = {}
		if len(self.quick_cache) > 50:
			self.quick_cache.clear()
		self.rating_source = config.plugins.AglareStarX.rating_source.value
		self.display_mode = config.plugins.AglareStarX.display_mode.value
		logger.info("AglareStarX Renderer initialized")

	def applySkin(self, desktop, parent):
		"""Handle skin attributes"""
		attribs = []
		for attrib, value in self.skinAttributes:
			if attrib == "rating_source":
				self.rating_source = str(value)
			elif attrib == "display_mode":
				self.display_mode = str(value)
			attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def changed(self, what):
		"""Handle content changes"""
		if not self.instance:
			return

		if what[0] == self.CHANGED_CLEAR:
			(self.range, self.value) = ((0, 1), 0)
			return

		try:
			service = None
			if isinstance(self.source, ServiceEvent):
				service = self.source.getCurrentService()
			elif isinstance(self.source, CurrentService):
				service = self.source.getCurrentServiceRef()
			elif isinstance(self.source, EventInfo):
				service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
			elif isinstance(self.source, Event):
				self._fill_from_event()
				self._update_rating()
				return

			if service:
				self._fill_from_service(service)
				self._update_rating()

		except Exception as e:
			logger.error(f"Changed error: {str(e)}")
			(self.range, self.value) = ((0, 1), 0)

	def _fill_from_event(self):
		"""Extract event info from current event"""
		event = self.source.event
		self.canal[1] = event.getBeginTime()
		event_name = event.getEventName().replace('\xc2\x86', '').replace('\xc2\x87', '')
		self.canal[2] = event_name
		self.canal[3] = event.getExtendedDescription()
		self.canal[4] = event.getShortDescription()
		self.canal[5] = event_name

	def _fill_from_service(self, service):
		"""Extract event info from service reference"""
		service_str = service.toString()
		events = epgcache.lookupEvent(['IBDCTESX', (service_str, 0, -1, -1)])
		if not events:
			(self.range, self.value) = ((0, 1), 0)
			return

		service_name = ServiceReference(service).getServiceName().replace('\xc2\x86', '').replace('\xc2\x87', '')
		self.canal = [None] * 6
		self.canal[0] = service_name
		event = events[0]  # Get current event
		self.canal[1] = event[1]  # Begin time
		self.canal[2] = event[4]  # Event name
		self.canal[3] = event[5]  # Extended description
		self.canal[4] = event[6]  # Short description
		self.canal[5] = event[4]  # Event name (again)

	def _update_rating(self):
		"""Update rating display based on current event"""
		if not self.canal[5] or not isinstance(self.canal[5], str):
			logger.warning("Invalid title in canal[5]")
			(self.range, self.value) = ((0, 1), 0)
			return

		clean_title = clean_for_tvdb(self.canal[5])  # if self.canal[5] else None
		title_hash = md5(clean_title.encode('utf-8')).hexdigest()

		# Check quick cache first
		if title_hash in self.quick_cache:
			self._display_rating(self.quick_cache[title_hash])
			return

		# Check in persistent cache
		info_file = join(POSTER_FOLDER, f"{clean_filename(clean_title)}.json")
		if exists(info_file):
			try:
				with open(info_file, 'r') as f:
					info_data = json.load(f)
					rating = self._extract_rating(info_data)
					self.quick_cache[title_hash] = rating
					self._display_rating(rating)
					return
			except Exception as e:
				logger.error(f"Error loading rating file: {str(e)}")

		# No cached rating available
		(self.range, self.value) = ((0, 1), 0)

	def _extract_rating(self, info_data):
		"""Extract rating from TMDB/OMDB data based on configuration"""
		if self.rating_source == "tmdb":
			rating = info_data.get('vote_average', 0)
			if rating:
				return min(int(float(rating) * 10), 100)  # Convert 0-10 scale to 0-100
		elif self.rating_source == "imdb":
			rating = info_data.get('imdbRating', 0)
			if rating and rating != 'N/A':
				return min(int(float(rating) * 10), 100)  # Convert 0-10 scale to 0-100

		return 0  # Default if no rating found

	def _display_rating(self, rating):
		"""Update the slider with the rating value"""
		if self.display_mode == "percentage":
			(self.range, self.value) = ((0, 100), rating)
		elif self.display_mode == "stars5":
			# Convert to 5-star scale (0-100 becomes 0-5 stars)
			stars = min(5, max(0, round(rating / 20)))
			(self.range, self.value) = ((0, 5), stars)
		elif self.display_mode == "stars10":
			# Convert to 10-star scale (0-100 becomes 0-10 stars)
			stars = min(10, max(0, round(rating / 10)))
			(self.range, self.value) = ((0, 10), stars)
		else:  # Default to percentage
			(self.range, self.value) = ((0, 100), rating)

		self.instance.show()

	def postWidgetCreate(self, instance):
		"""Initialize the slider widget"""
		instance.setRange(self.__start, self.__end)

	def setRange(self, range):
		"""Set the slider range"""
		(self.__start, self.__end) = range
		if self.instance:
			self.instance.setRange(self.__start, self.__end)

	def getRange(self):
		"""Get the current slider range"""
		return (self.__start, self.__end)


def setupConfig():
	"""Initialize configuration options"""
	from Components.config import ConfigSubsection, ConfigSelection
	config.plugins.AglareStarX = ConfigSubsection()
	config.plugins.AglareStarX.rating_source = ConfigSelection(
		choices=[("tmdb", "TMDB Rating"), ("imdb", "IMDB Rating")],
		default="tmdb"
	)
	config.plugins.AglareStarX.display_mode = ConfigSelection(
		choices=[
			("percentage", "Percentage (0-100)"),
			("stars5", "5-Star Rating"),
			("stars10", "10-Star Rating")
		],
		default="percentage"
	)


# Initialize configuration
try:
	setupConfig()
except Exception as e:
	logger.error(f"Config setup error: {str(e)}")
