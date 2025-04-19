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
#   by base code from digiteng 2022                     #
#  Last Modified: "15:14 - 20250401"                    #
#                                                       #
#  Credits:                                             #
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
from json import load as json_load, dump as json_dump
from os import path
from threading import Lock as threading_Lock
from hashlib import md5

# Enigma2 imports
from Components.Renderer.Renderer import Renderer
from Components.VariableText import VariableText
from Components.Sources.CurrentService import CurrentService
from Components.Sources.Event import Event
from Components.Sources.EventInfo import EventInfo
from Components.Sources.ServiceEvent import ServiceEvent
from Components.config import config, ConfigSubsection, ConfigText, ConfigSelection
from enigma import eLabel, eEPGCache
import NavigationInstance
from ServiceReference import ServiceReference

# Local imports
from .Agp_Utils import POSTER_FOLDER, clean_for_tvdb, clean_filename, logger  # , noposter

# Constants
epgcache = eEPGCache.getInstance()
api_lock = threading_Lock()


"""skin configuration"""
"""
<widget source="Event" render="AglareInfoEvents" position="x,y" size="width,height"
	display_mode="full" />
"""

"""skin custom configuration"""
"""
<widget source="Event" render="AglareInfoEvents" position="x,y" size="width,height"
	display_mode="custom"
	info_format="{title} ({year}) - {rating}
{genres}
{overview}" />
"""


class AglareInfoEvents(Renderer, VariableText):
	"""Enhanced renderer for displaying detailed event information from TMDB"""

	GUI_WIDGET = eLabel

	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.text = ""
		self.canal = [None] * 6
		self.quick_cache = {}
		if len(self.quick_cache) > 50:
			self.quick_cache.clear()
		self.last_service = None
		self.display_mode = config.plugins.AglareInfoEvents.display_mode.value
		self.info_format = config.plugins.AglareInfoEvents.info_format.value
		logger.info("AglareInfoEvents Renderer initialized")

	def applySkin(self, desktop, parent):
		"""Handle skin attributes"""
		attribs = []
		for attrib, value in self.skinAttributes:
			if attrib == "display_mode":
				self.display_mode = str(value)
			elif attrib == "info_format":
				self.info_format = str(value)
			attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def changed(self, what):
		"""Handle content changes"""
		if not hasattr(self, 'instance') or not self.instance:
			return

		if what[0] not in (self.CHANGED_DEFAULT, self.CHANGED_ALL, self.CHANGED_SPECIFIC, self.CHANGED_CLEAR):
			if self.instance:
				self.instance.hide()
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
				self._update_info()
				return

			if service:
				self._fill_from_service(service)
				self._update_info()

		except Exception as e:
			logger.error(f"Changed error: {str(e)}")
			self.text = ""

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
			self.text = ""
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

	def _update_info(self):
		"""Update info text based on current event"""
		if not self.canal[5] or not isinstance(self.canal[5], str):
			logger.warning("Invalid title in canal[5]")
			self.text = ""
			return

		clean_title = clean_for_tvdb(self.canal[5]) if self.canal[5] else None
		title_hash = md5(clean_title.encode('utf-8')).hexdigest()

		# Check quick cache first
		if title_hash in self.quick_cache:
			self._display_info(self.quick_cache[title_hash])
			return

		# Check in persistent cache
		info_file = path.join(POSTER_FOLDER, f"{clean_filename(clean_title)}.json")
		if path.exists(info_file):
			try:
				with open(info_file, 'r') as f:
					info_data = json_load(f)
					self.quick_cache[title_hash] = self._process_tmdb_data(info_data)
					self._display_info(self.quick_cache[title_hash])
					return
			except Exception as e:
				logger.error(f"Error loading info file: {str(e)}")

		# No cached info available
		self.text = ""

	def _process_tmdb_data(self, tmdb_data):
		"""Convert raw TMDB data into display-friendly format"""
		processed = {
			'title': tmdb_data.get('title') or tmdb_data.get('original_title', 'N/A'),
			'original_title': tmdb_data.get('original_title', 'N/A'),
			'year': tmdb_data.get('release_date', '')[:4] if tmdb_data.get('release_date') else 'N/A',
			'rating': str(tmdb_data.get('vote_average', 'N/A')) + '/10',
			'votes': str(tmdb_data.get('vote_count', 'N/A')),
			'popularity': str(round(tmdb_data.get('popularity', 0), 1)),
			'overview': tmdb_data.get('overview', 'N/A'),
			'media_type': tmdb_data.get('media_type', 'movie').capitalize(),
			'language': tmdb_data.get('original_language', 'N/A').upper(),
			'adult': 'Yes' if tmdb_data.get('adult') else 'No',
			'genres': self._get_genres(tmdb_data.get('genre_ids', [])),
			'backdrop_url': f"https://image.tmdb.org/t/p/original{tmdb_data.get('backdrop_path', '')}" if tmdb_data.get('backdrop_path') else 'N/A',
			'poster_url': f"https://image.tmdb.org/t/p/w500{tmdb_data.get('poster_path', '')}" if tmdb_data.get('poster_path') else 'N/A'
		}

		# Add additional processed fields
		processed['short_info'] = f"{processed['title']} ({processed['year']}) - {processed['rating']}"
		processed['full_info'] = (
			f"{processed['title']} ({processed['year']})\n"
			f"Original: {processed['original_title']}\n"
			f"Rating: {processed['rating']} ({processed['votes']} votes)\n"
			f"Type: {processed['media_type']}\n"
			f"Genres: {processed['genres']}\n\n"
			f"{processed['overview']}"
		)

		return processed

	def _get_genres(self, genre_ids):
		"""Convert genre IDs to names"""
		genre_map = {
			18: "Drama", 36: "History", 10749: "Romance",
			28: "Action", 12: "Adventure", 16: "Animation",
			35: "Comedy", 80: "Crime", 99: "Documentary",
			10751: "Family", 14: "Fantasy", 27: "Horror",
			10402: "Music", 9648: "Mystery", 10752: "War",
			37: "Western", 53: "Thriller", 10770: "TV Movie"
		}
		return ", ".join([genre_map.get(gid, "") for gid in genre_ids if gid in genre_map])

	def _display_info(self, info_data):
		"""Format and display the information according to settings"""
		try:
			if self.display_mode == "short":
				self.text = info_data.get('short_info', 'N/A')
			elif self.display_mode == "full":
				self.text = info_data.get('full_info', 'N/A')
			elif self.display_mode == "custom":
				try:
					self.text = self.info_format.format(**info_data)
				except KeyError as e:
					logger.warning(f"Missing key in format: {str(e)}")
					self.text = info_data.get('short_info', 'N/A')
			else:
				self.text = info_data.get('short_info', 'N/A')

		except Exception as e:
			logger.error(f"Error displaying info: {str(e)}")
			self.text = ""

	def _save_info(self, title, info_data):
		"""Save information to cache"""
		try:
			clean_title = clean_for_tvdb(title)
			title_hash = md5(clean_title.encode('utf-8')).hexdigest()
			info_file = path.join(POSTER_FOLDER, f"{clean_filename(clean_title)}.json")

			with open(info_file, 'w') as f:
				json_dump(info_data, f)

			self.quick_cache[title_hash] = self._process_tmdb_data(info_data)
			logger.info(f"Saved info for: {clean_title}")

		except Exception as e:
			logger.error(f"Error saving info: {str(e)}")


def setupConfig():
	"""Initialize configuration options"""
	config.plugins.AglareInfoEvents = ConfigSubsection()
	config.plugins.AglareInfoEvents.display_mode = ConfigSelection(
		choices=[("short", "Short info"), ("full", "Full info"), ("custom", "Custom format")],
		default="short"
	)
	config.plugins.AglareInfoEvents.info_format = ConfigText(
		default="{title} ({year})\nRating: {rating}\nGenres: {genres}\n\n{overview}",
		fixed_size=False
	)


# Initialize configuration
try:
	setupConfig()
except Exception as e:
	logger.error(f"Config setup error: {str(e)}")
