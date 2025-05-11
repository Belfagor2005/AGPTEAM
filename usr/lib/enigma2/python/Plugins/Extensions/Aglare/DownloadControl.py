#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
"""
#########################################################
#														#
#  AGP - Advanced Graphics Renderer						#
#  Version: 3.5.0										#
#  Created by Lululla (https://github.com/Belfagor2005) #
#  License: CC BY-NC-SA 4.0								#
#  https://creativecommons.org/licenses/by-nc-sa/4.0	#
#  from original code by @digiteng 2021					#
#  Last Modified: "15:14 - 20250401"					#
#														#
#  Credits:												#
#  - Original concept by Lululla						#
#  - Poster renderer									#
#  - Backdrop renderer									#
#  - Poster EMC renderer								#
#  - InfoEvents renderer								#
#  - Star rating renderer								#
#  - Parental control renderer							#
#  - Genre detection and renderer						#
#														#
#  - Advanced download management system				#
#  - Atomic file operations								#
#  - Thread-safe resource locking						#
#  - TMDB API integration								#
#  - TVDB API integration								#
#  - OMDB API integration								#
#  - FANART API integration								#
#  - IMDB API integration								#
#  - ELCINEMA API integration							#
#  - GOOGLE API integration								#
#  - PROGRAMMETV integration							#
#  - MOLOTOV API integration							#
#  - Advanced caching system							#
#  - Fully configurable via AGP Setup Plugin			#
#														#
#  Usage of this code without proper attribution		#
#  is strictly prohibited.								#
#  For modifications and redistribution,				#
#  please maintain this credit header.					#
#########################################################
"""
__author__ = "Lululla"
__copyright__ = "AGP Team"

poster_auto_db = None
backdrop_auto_db = None


def startPosterAutoDB():
	from Components.Renderer.AglarePosterX import PosterAutoDB
	from Components.Renderer.Agp_Utils import logger
	global poster_auto_db

	if poster_auto_db:
		if poster_auto_db.is_alive():
			poster_auto_db._stop_event.set()
			poster_auto_db.join(timeout=1)
		poster_auto_db = None

	poster_auto_db = PosterAutoDB()
	poster_auto_db.start()

	poster_auto_db.force_immediate_download()
	logger.debug("startPosterAutoDB Download Starting!")


def startBackdropAutoDB():
	from Components.Renderer.AglareBackdropX import BackdropAutoDB
	from Components.Renderer.Agp_Utils import logger
	global backdrop_auto_db
	if backdrop_auto_db:
		if backdrop_auto_db.is_alive():
			backdrop_auto_db._stop_event.set()
			backdrop_auto_db.join(timeout=1)
		backdrop_auto_db = None

	backdrop_auto_db = BackdropAutoDB()
	backdrop_auto_db.start()
	logger.debug("startBackdropAutoDB Download Starting!")
