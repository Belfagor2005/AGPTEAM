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
from os.path import join, exists
from re import sub
from json import load as json_load

# Enigma2 imports
from Components.Renderer.Renderer import Renderer
from Components.config import config
from enigma import ePixmap, loadPNG


# Local imports
from .Agp_Utils import clean_for_tvdb, get_valid_storage_path, logger  # , noposter

# Constants
GENRE_PIC_PATH = f'/usr/share/enigma2/{config.skin.primary_skin.value.replace("/skin.xml", "")}/genre_pic/'


class AglareGenreX(Renderer):
	"""Advanced genre icon renderer with AGP ecosystem integration"""

	GUI_WIDGET = ePixmap

	# Genre mapping compatible with EPG levels
	GENRE_MAP = {
		1: {
			'default': 'general',
			1: 'action', 2: 'thriller', 3: 'drama', 4: 'movie',
			16: 'animation', 35: 'comedy'
		},
		5: {'default': 'kids', 1: 'cartoon'},
		12: {'default': 'adventure'},
		14: {'default': 'fantasy'}
	}

	def __init__(self):
		Renderer.__init__(self)
		self.genre_cache = {}  # title_hash -> genre_name
		self.storage_path = get_valid_storage_path()  # Reuse from PosterX

	def changed(self, what):
		"""Handle EPG changes"""
		if not hasattr(self, 'instance') or not self.instance:
			return

		if what[0] not in (self.CHANGED_DEFAULT, self.CHANGED_ALL, self.CHANGED_SPECIFIC, self.CHANGED_CLEAR):
			if self.instance:
				self.instance.hide()
			return

		self._update_genre_icon()

	def _update_genre_icon(self):
		"""Main icon update logic"""
		event = self.source.event
		if not event:
			return

		try:
			# Get normalized title (reusing PosterX functions)
			title = event.getEventName()
			clean_title = clean_for_tvdb(title) if title else None
			title_hash = hash(title) if title else 0

			# Try cache first
			cached_genre = self.genre_cache.get(title_hash)
			if cached_genre:
				self._load_genre_icon(cached_genre)
				return

			# Check JSON metadata (compatible with PosterX storage)
			genre = self._get_genre_from_metadata(clean_title) if clean_title else None

			# Fallback to EPG data
			if not genre:
				genre = self._get_genre_from_epg(event)

			if genre:
				self.genre_cache[title_hash] = genre
				self._load_genre_icon(genre)
			else:
				self.instance.hide()

		except Exception as e:
			logger.error(f"GenreX error: {str(e)}")
			self.instance.hide()

	def _get_genre_from_metadata(self, clean_title):
		"""Check for genre in PosterX-generated JSON"""
		meta_file = join(self.storage_path, f"{clean_title}.json")
		if exists(meta_file):
			try:
				with open(meta_file, 'r') as f:
					return json_load(f).get('genres', '').split(',')[0].strip().lower()
			except:
				logger.warning(f"Couldn't read genre from {meta_file}")
		return None

	def _get_genre_from_epg(self, event):
		"""Extract genre from EPG data"""
		gData = event.getGenreData()
		if not gData:
			return None

		level1 = gData.getLevel1()
		level2 = gData.getLevel2()

		genre_map = self.GENRE_MAP.get(level1, {})
		return genre_map.get(level2, genre_map.get('default'))

	def _load_genre_icon(self, genre_name):
		"""Load and display genre PNG"""
		if not genre_name:
			self.instance.hide()
			return

		safe_name = sub(r"[^a-z0-9]+", "_", genre_name.lower()).strip("_")
		icon_path = f"{GENRE_PIC_PATH}{safe_name}.png"

		if exists(icon_path):
			self.instance.setPixmap(loadPNG(icon_path))
			self.instance.setScale(1)
			self.instance.show()
		else:
			logger.debug(f"No icon for genre: {genre_name}")
			self.instance.hide()


# Skin configuration example
"""
<widget render="AglareGenreX"
	source="session.Event_Now"
	position="54,315"
	size="300,438"
	zPosition="22"
	transparent="1" />
"""
