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
#  from original code by @digiteng 2021                 #
#  Last Modified: "15:14 - 20250401"                    #
#                                                       #
#  Credits:                                             #
#  - Original concept by Lululla                        #
#  - Poster renderer                                    #
#  - Backdrop renderer                                  #
#  - Poster EMC renderer                                #
#  - InfoEvents renderer                                #
#  - Star rating renderer                               #
#  - Parental control renderer                          #
#  - Genre detection and renderer                       #
#                                                       #
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
from os import remove, makedirs
from os.path import exists, join, getsize, basename, splitext
from threading import Lock
from queue import LifoQueue
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import sys
from re import sub

# Enigma2 specific imports
from enigma import ePixmap, loadJPG, eTimer
from Components.Renderer.Renderer import Renderer
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.EventInfo import EventInfo
from Components.Sources.CurrentService import CurrentService
import NavigationInstance

# Local imports
from Components.Renderer.AgpDownloadThread import AgpDownloadThread
from Plugins.Extensions.Aglare.plugin import ApiKeyManager, config

from .Agp_Utils import (
	IMOVIE_FOLDER,
	clean_for_tvdb,
	logger
)


sys.stderr = open('/tmp/agplog/AgpXEMC_errors.log', 'w')
if not IMOVIE_FOLDER.endswith("/"):
	IMOVIE_FOLDER += "/"


# Constants and global variables
pdbemc = LifoQueue()
api_key_manager = ApiKeyManager()
extensions = ['.jpg']
PARENT_SOURCE = config.plugins.Aglare.xemc_poster.value


"""
# Use for emc plugin
<widget source="Service" render="AgpXEMC"
	position="1703,583"
	size="200,300"
	cornerRadius="20"
	zPosition="22"
/>
"""


try:
	lng = config.osd.language.value
	lng = lng[:-3]
except:
	lng = 'en'
	pass


class AgpXEMC(Renderer):

	GUI_WIDGET = ePixmap

	def __init__(self):
		super().__init__()
		if not config.plugins.Aglare.xemc_poster.value:
			logger.debug("Movie renderer disabled in configuration")
			return
		self.path = IMOVIE_FOLDER
		# self.timer = eTimer()
		# self.timer.callback.append(self.waitPoster)
		self._poster_timer = eTimer()
		self._poster_timer.callback.append(self._retryPoster)
		logger.info("AGP Movie Renderer initialized")
		clear_all_log()

	def applySkin(self, desktop, parent):
		if not config.plugins.Aglare.xemc_poster.value:
			return

		super().applySkin(desktop, parent)
		attribs = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "path":
				self.path = str(value)
			attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def changed(self, what):
		if not self.instance or not config.plugins.Aglare.xemc_poster.value:
			return

		try:
			source = self.source
			service_ref = None
			movie_path = None

			# Dynamic EMC source detection
			if hasattr(source, '__class__'):
				class_name = source.__class__.__name__

				# Handle EMCServiceEvent
				if class_name == "EMCServiceEvent":
					service_ref = getattr(source, 'service', None)
					if service_ref:
						movie_path = service_ref.getPath()

				# Handle EMCCurrentService
				elif class_name == "EMCCurrentService":
					current_service = getattr(source, 'getCurrentService', lambda: None)()
					if current_service:
						movie_path = current_service.getPath()

			# Fallback to standard sources
			if not movie_path:
				if isinstance(source, ServiceEvent):
					service_ref = source.getCurrentService()
					movie_path = service_ref.getPath() if service_ref else None

				elif isinstance(source, CurrentService):
					service_ref = source.getCurrentServiceRef()
					movie_path = service_ref.getPath() if service_ref else None

				elif isinstance(source, EventInfo):
					service_ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
					movie_path = service_ref.getPath() if service_ref else None

			# Process valid movie paths
			if movie_path and _is_video_file(movie_path):
				self._process_movie_path(movie_path)
			else:
				self.instance.hide()

		except Exception as e:
			logger.error(f"Render Error: {str(e)}")
			self.instance.hide()

	def _process_movie_path(self, movie_path):
		clean_title = self._sanitize_title(basename(movie_path))
		poster_path = join(self.path, f"{clean_title}.jpg")

		if _validate_poster(poster_path):
			self.waitPoster(poster_path)
		else:
			search_title = basename(movie_path).rsplit('.', 1)[0]
			self._queue_for_download(search_title, clean_title, poster_path)

	def _sanitize_title(self, filename):
		name = filename.rsplit('.', 1)[0]
		logger.info(f"_sanitize_title poster name: {name}")
		cleaned = sub(
			r'\.(?=\D)|\(\d{4}\)|\d{4}|[._](?:720|1080)[pi]|\b(?:HD|DVD|BRRip)\b',
			' ',
			name
		)
		cleaned = clean_for_tvdb(cleaned)
		logger.info(f"_sanitize_title poster cleaned name: {cleaned}")
		return cleaned.strip()

	def _queue_for_download(self, title, movie_path, poster_path):
		logger.info("EMC put: clean_title='%s' movie_path='%s' poster_path='%s'", title, movie_path, poster_path)
		pdbemc.put((title, movie_path, poster_path))
		if not AgpDBemc.is_alive():
			AgpDBemc.start()

		self.waitPoster(poster_path)

	def display_poster(self, poster_path=None):
		"""Display the poster image"""
		if not self.instance:
			logger.error("Instance is None in display_poster")
			return

		if poster_path:
			logger.info(f"Displaying poster from path: {poster_path}")

			if _validate_poster(poster_path):
				logger.info(f"Poster validated, loading image from {poster_path}")
				self.instance.setPixmap(loadJPG(poster_path))
				self.instance.setScale(1)
				self.instance.show()

				self.instance.invalidate()
				self.instance.show()
			else:
				logger.error(f"Poster file is invalid: {poster_path}")
				self.instance.hide()

	def waitPoster(self, poster_path=None):
		"""Asynchronous wait using eTimer to avoid blocking UI"""
		if not self.instance or not poster_path:
			return

		if not exists(poster_path):
			self.instance.hide()

		self.poster_path = poster_path
		self.retry_count = 0
		if self._poster_timer.isActive():
			self._poster_timer.stop()
		self._poster_timer.start(100, True)

	def _retryPoster(self):
		if _validate_poster(self.poster_path):
			logger.debug("Poster found, displaying")
			self.display_poster(self.poster_path)
			return

		self.retry_count += 1
		if self.retry_count < 5:
			delay = 100 + self.retry_count * 200  # ritardo crescente
			self._poster_timer.start(delay, True)
		else:
			logger.warning("Poster not found after retries: %s", self.poster_path)


class PosterDBEMC(AgpDownloadThread):
	"""Handles PosterDBEMC downloading and database management"""
	def __init__(self, providers=None):
		super().__init__()
		self.executor = ThreadPoolExecutor(max_workers=2)
		self.queued = set()
		self.lock = Lock()
		# self.api = ApiKeyManager()
		self.api = api_key_manager
		self.providers = api_key_manager.get_active_providers()
		self.provider_engines = self.build_providers()

	def run(self):
		"""Main processing loop - handles incoming channel requests"""
		while True:
			item = pdbemc.get()
			self.executor.submit(self._process_item, item)
			pdbemc.task_done()

	def build_providers(self):
		"""Initialize enabled provider search engines with priority"""
		provider_mapping = {
			"tmdb": (self.search_tmdb, 0),
			"omdb": (self.search_omdb, 1),
			"google": (self.search_google, 2)
		}
		return [
			(name, func, prio) for name, (func, prio) in provider_mapping.items()
			if self.providers.get(name, False)
		]

	def _get_providers(self):
		"""Provider priority list for movies"""
		provider_config = {
			"tmdb": (self.search_tmdb, 0),
			"omdb": (self.search_omdb, 1),
			"google": (self.search_google, 2)
		}
		return [
			(name, func)
			for name, (func, prio) in sorted(
				provider_config.items(),
				key=lambda item: item[1][1]
			)
			if self.api.is_provider_active(name)
		]

	def _process_item(self, item):
		search_title, clean_title, poster_path = item
		with self.lock:
			if search_title in self.queued:
				return
			self.queued.add(search_title)

		try:
			if self._check_existing(poster_path):
				return

			logger.info("Starting download: %s", search_title)
			# Sort by priority (lower number = higher priority)
			sorted_providers = sorted(
				self.provider_engines,
				key=lambda x: x[2]  # sort by prio
			)

			for provider_name, provider_func, _ in sorted_providers:
				try:
					api_key = api_key_manager.get_api_key(provider_name)
					if not api_key:
						logger.warning("Missing API key for %s", provider_name)
						continue

					logger.info("EMC processing: search_title='%s' clean_title='%s'", search_title, clean_title)

					result = provider_func(
						dwn_poster=poster_path,
						title=search_title,
						shortdesc=None,
						fulldesc=None,
						channel=clean_title,
						api_key=api_key
					)
					if result and self.check_valid_poster(poster_path):
						logger.info("Download successful with %s", provider_name)
						break

				except Exception as e:
					logger.error("Error from %s: %s", provider_name, str(e))

		finally:
			with self.lock:
				self.queued.discard(search_title)

	def check_valid_poster(self, path):
		"""Verify poster is valid JPEG and >1KB"""
		try:
			if not exists(path):
				return False

			if getsize(path) < 1024:
				remove(path)
				return False

			with open(path, 'rb') as f:
				header = f.read(2)
				if header != b'\xFF\xD8':  # JPEG magic number
					remove(path)
					return False
			return True
		except Exception as e:
			logger.error(f"Poster validation error: {str(e)}")
			return False

	def _check_existing(self, path):
		if exists(path) and getsize(path) > 1024:
			return True
		return False

	def _log_debug(self, message):
		self._write_log("DEBUG", message)

	def _log_error(self, message):
		self._write_log("ERROR", message)

	def _write_log(self, level, message):
		"""Centralized logging method"""
		try:
			log_dir = "/tmp/agplog"
			if not exists(log_dir):
				makedirs(log_dir)
			with open(self.log_file, "a") as w:
				w.write(f"{datetime.now()} {level}: {message}\n")
		except Exception as e:
			print(f"Logging error: {e}")


def _validate_poster(poster_path):
	"""Check if the poster file is valid (exists and has a valid size)"""
	return exists(poster_path) and getsize(poster_path) > 100


def _is_video_file(path):
	return path and splitext(path)[1].lower() in (
		'.mkv', '.avi', '.mp4', '.ts', '.mov', '.iso', '.m2ts', '.flv', '.webm'
	)


def clear_all_log():
	log_files = [
		"/tmp/agplog/PosterDBEMC_errors.log",
		"/tmp/agplog/PosterDBEMC.log",
		"/tmp/agplog/PosterDBEMC.log"
	]
	for files in log_files:
		try:
			if exists(files):
				remove(files)
				logger.warning(f"Removed cache: {files}")
		except Exception as e:
			logger.error(f"log_files cleanup failed: {e}")


"""
# if config.plugins.Aglare.xemc_poster.value:
	# AgpDBemc = PosterDBEMC()
	# AgpDBemc.daemon = True
	# AgpDBemc.start()
	# logger.info("PosterDBEMC thread started")
"""

# Start thread poster
db_lock = Lock()
AgpDBemc = None
if config.plugins.Aglare.xemc_poster.value:
	if any(api_key_manager.get_active_providers().values()):
		logger.debug("Starting PosterDB with active providers")
		with db_lock:
			if AgpDBemc is None or not AgpDBemc.is_alive():
				AgpDBemc = PosterDBEMC()
				AgpDBemc.daemon = True
				AgpDBemc.start()
				logger.debug(f"PosterDBEMC started with PID: {AgpDBemc.ident}")
else:
	logger.debug("PosterDBEMC not started - no active providers")
