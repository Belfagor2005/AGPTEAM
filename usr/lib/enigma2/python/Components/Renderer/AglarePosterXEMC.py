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
from Components.config import config
from os import utime, makedirs
from os.path import exists, join, getsize
from re import findall, IGNORECASE
from time import sleep, time
from queue import LifoQueue
from threading import Thread
from datetime import datetime

# Enigma2/Dreambox specific imports
from enigma import ePixmap, loadJPG, eEPGCache, eTimer
from Components.Renderer.Renderer import Renderer
from Components.Sources.CurrentService import CurrentService
from Components.Sources.ServiceEvent import ServiceEvent

# Local imports
from Components.Renderer.AgpDownloadThread import AgpDownloadThread
from .Agp_Utils import IMOVIE_FOLDER, clean_for_tvdb, logger  # , noposter

# Constants and global variables
epgcache = eEPGCache.getInstance()
pdbemc = LifoQueue()
extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

"""
# Use for emc plugin
<widget source="Servicet" render="AglarePosterXEMC"
	position="100,100"
	size="185,278"
	cornerRadius="20"
	zPosition="95"
	path="/path/to/custom_folder"   <!-- Optional -->
	service.tmdb="true"             <!-- Enable TMDB -->
	service.tvdb="false"            <!-- Disable TVDB -->
	service.imdb="false"            <!-- Disable IMDB -->
	service.fanart="false"          <!-- Disable Fanart -->
	service.google="false"          <!-- Disable Google -->
/>
"""


try:
	lng = config.osd.language.value
	lng = lng[:-3]
except:
	lng = 'en'
	pass


class AglarePosterXEMC(Renderer):

	GUI_WIDGET = ePixmap

	def __init__(self):
		super().__init__()
		self.path = IMOVIE_FOLDER
		self.extensions = extensions
		self.canal = [None] * 6
		self.pstrNm = None
		self.oldCanal = None
		self.logdbg = None
		self.pstcanal = None
		self.timer = eTimer()
		self.timer.callback.append(self.showPoster)

	def applySkin(self, desktop, parent):
		attribs = []

		self.providers = {
			"tmdb": True,       # The Movie Database
			"tvdb": False,      # The TV Database
			"imdb": False,      # Internet Movie Database
			"fanart": False,    # Fanart.tv
			"google": False     # Google Images
		}

		for (attrib, value) in self.skinAttributes:
			if attrib == "path":
				self.path = str(value)

			if attrib.startswith("service."):
				provider = attrib.split(".")[1]
				if provider in self.providers:
					self.providers[provider] = value.lower() == "true"

			attribs.append((attrib, value))

		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def changed(self, what):
		if not self.instance:
			return

		# Skip unnecessary updates
		if what[0] not in (self.CHANGED_DEFAULT, self.CHANGED_ALL, self.CHANGED_SPECIFIC, self.CHANGED_CLEAR):
			if self.instance:
				self.instance.hide()
			return
		"""
		if what[0] == self.CHANGED_CLEAR:
			if self.instance:
				self.instance.hide()
			return
		"""

		# source = self.source
		# source_type = type(source)
		# servicetype = None
		# service = None
		try:
			event = None
			if isinstance(self.source, ServiceEvent):
				event = self.source.event
				self.canal[0] = None
				self.canal[1] = event.getBeginTime() if event else None
				event_name = event.getEventName().replace("\xc2\x86", "").replace("\xc2\x87", "") if event else ""
				self.canal[2] = event_name
				self.canal[3] = event.getExtendedDescription() if event else ""
				self.canal[4] = event.getShortDescription() if event else ""
				image_path = self.source.service.getPath().split(".ts")[0]
			elif isinstance(self.source, CurrentService):
				image_path = self.source.getCurrentServiceReference().getPath().split(".ts")[0]
			else:
				self.instance.hide()
				return

			self.canal[5] = None
			for ext in self.extensions:
				full_path = image_path + ext
				if checkPosterExistence(full_path):
					self.canal[5] = full_path
					break

		except Exception as e:
			logger.error("Error (service processing): %s", str(e))
			self.instance.hide()
			return

		poster_path = None

		try:
			if self.canal[5]:
				match = findall(r".*? - (.*?) - (.*?)\.(jpg|jpeg|png)$", self.canal[5], IGNORECASE)
				if match and len(match[0]) > 1:
					self.canal[0] = match[0][0].strip()
					if not self.canal[2]:
						self.canal[2] = match[0][1].strip()

				self._log_debug("Service: {} - {} => {}".format(self.canal[0], self.canal[2], self.canal[5]))

			if len(self.canal) > 5 and self.canal[5]:
				self.pstcanal = clean_for_tvdb(self.canal[5])
				poster_path = self.generatePosterPath()

			if poster_path:
				if self.pstrNm == poster_path:
					logger.info(f"Poster already loaded: {poster_path}")
					return

				self.pstrNm = poster_path
				utime(self.pstrNm, (time(), time()))
				self.instance.hide()
				self.timer.start(500, True)
				return
			else:
				if self.canal[0] and self.canal[2]:
					canal = self.canal[:]
					pdbemc.put(canal)
					self.runPosterThread()

		except Exception as e:
			logger.error(f"Error in poster display: {e}")
			if self.instance:
				self.instance.hide()
			return

	def generatePosterPath(self):
		"""Generate poster path from current channel data, checking for multiple image extensions"""
		if isinstance(self.pstcanal, str) and self.pstcanal.strip():  # Ensure self.pstcanal is a valid string
			# Check if the poster has already been loaded
			if hasattr(self, '_loaded_posters') and self.pstcanal in self._loaded_posters:
				logger.info(f"Poster already loaded: {self._loaded_posters[self.pstcanal]}")  # Log if poster is already loaded
				return self._loaded_posters[self.pstcanal]  # Return the already loaded poster path
			# Try to search for the poster
			for ext in self.extensions:
				candidate = join(self.path, self.pstcanal + ext)
				logger.info(f"Checking poster path: {candidate}")  # Log the path being checked
				if checkPosterExistence(candidate):
					logger.info(f"Found poster at: {candidate}")  # Log the found poster path
					# Cache the found poster path
					if not hasattr(self, '_loaded_posters'):
						self._loaded_posters = {}
					self._loaded_posters[self.pstcanal] = candidate  # Cache the loaded poster path
					return candidate
			logger.info(f"Poster not found for {self.pstcanal}")
		else:
			logger.error(f"Invalid self.pstcanal value: {self.pstcanal}")
		return None

	def runPosterThread(self):
		"""Start poster download thread"""
		Thread(target=self.waitPoster, daemon=True).start()

	def showPoster(self):
		"""Display the poster image"""
		if self.instance:
			self.instance.hide()
		if not self.pstrNm or not checkPosterExistence(self.pstrNm):
			self.instance.hide()
			logger.info("showPoster hide instance")
			return

		self.instance.hide()
		self.instance.setPixmap(loadJPG(self.pstrNm))
		self.instance.setScale(1)
		self.instance.show()

	def waitPoster(self):
		"""Wait for poster download to complete"""
		if self.instance:
			self.instance.hide()
		self.pstrNm = self.generatePosterPath()
		if not hasattr(self, 'pstrNm') or self.pstrNm is None:
			logger.info("pstrNm not initialized in waitPoster")
			return
		logger.info(f"Poster found: {self.pstrNm}")

		if not self.pstrNm:
			self._log_debug("[ERROR: waitPoster] Poster path is None")
			return

		loop = 180  # Maximum number of attempts
		found = False
		logger.info(f"[WAIT] Checking for poster: {self.pstrNm}")
		while loop > 0:
			if self.pstrNm and checkPosterExistence(self.pstrNm):
				found = True
				break
			logger.info(f"[WAIT] Attempting to find poster... (remaining tries: {loop})")  # Add more logging
			sleep(0.5)
			loop -= 1

		if found:
			logger.info(f"Poster found: {self.pstrNm}")
			self.timer.start(10, True)
		else:
			logger.error("[ERROR] Poster not found after multiple attempts.")

	def _log_debug(self, message):
		"""Log debug message to file"""
		try:
			with open("/tmp/agplog/AgpPosterXEMC.log", "a") as w:
				w.write(f"{datetime.now()}: {message}\n")
		except Exception as e:
			logger.error(f"Logging error: {e}")

	def _log_error(self, message):
		"""Log error message to file"""
		try:
			with open("/tmp/agplog/AgpPosterXEMC_errors.log", "a") as f:
				f.write(f"{datetime.now()}: ERROR: {message}\n")
		except Exception as e:
			logger.error(f"Error logging error: {e}")


class PosterDBEMC(AgpDownloadThread):
	"""Handles poster downloading and database management"""
	def __init__(self, providers=None):
		super().__init__()
		self.extensions = extensions
		self.logdbg = None
		self.pstcanal = None
		self.service_pattern = compile(r'^#SERVICE (\d+):([^:]+:[^:]+:[^:]+:[^:]+:[^:]+:[^:]+)')
		self.log_file = "/tmp/agplog/PosterDBEMC.log"
		if not exists("/tmp/agplog"):
			makedirs("/tmp/agplog")

		default_providers = {
			"tmdb": True,       # The Movie Database
			"tvdb": False,      # The TV Database
			"imdb": False,      # Internet Movie Database
			"fanart": False,    # Fanart.tv
			"google": False     # Google Images
		}
		self.providers = {**default_providers, **(providers or {})}
		self.provider_engines = self.build_providers()

	def build_providers(self):
		"""Initialize enabled provider search engines"""
		mapping = {
			"tmdb": ("TMDB", self.search_tmdb),
			"tvdb": ("TVDB", self.search_tvdb),
			"fanart": ("Fanart", self.search_fanart),
			"imdb": ("IMDB", self.search_imdb),
			"google": ("Google", self.search_google)
		}
		return [engine for key, engine in mapping.items() if self.providers.get(key)]

	def run(self):
		"""Main processing loop - handles incoming channel requests"""
		while True:
			canal = pdbemc.get()
			self.process_canal(canal)
			pdbemc.task_done()

	def process_canal(self, canal):
		"""Process channel data and download posters"""
		try:
			self.pstcanal = clean_for_tvdb(canal[5])
			if not self.pstcanal:
				print(f"Invalid channel name: {canal[0]}")
				return

			if not any(self.providers.values()):
				self._log_debug("No provider is enabled for poster download")
				return

			poster_path = join(IMOVIE_FOLDER, f"{self.pstcanal}.jpg")
			if checkPosterExistence(self.pstcanal):
				utime(poster_path, (time(), time()))
				return

			for ext in self.extensions:
				poster_path = join(IMOVIE_FOLDER, self.pstcanal + ext)
				if checkPosterExistence(poster_path):
					utime(poster_path, (time(), time()))  # Avoid re-download
					self._log_debug(f"Poster already exists: {poster_path}")
					return

			for provider_name, provider_func in self.provider_engines:
				try:
					result = provider_func(poster_path, self.pstcanal, canal[4], canal[3], canal[0])
					if not result or len(result) != 2:
						self._log_debug(f"{provider_name} failed to return a valid result for {self.pstcanal}")
						continue

					success, log = result
					self._log_debug(f"{provider_name}: {log}")

					if success:
						break  # Exit after first successful poster
				except Exception as e:
					self._log_error(f"Error with engine {provider_name} ({self.pstcanal}): {str(e)}")

		except Exception as e:
			self._log_error(f"Processing error ({self.pstcanal}): {e}")

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


def checkPosterExistence(poster_path):
	return exists(poster_path)


def is_valid_poster(poster_path):
	"""Check if the poster file is valid (exists and has a valid size)"""
	return exists(poster_path) and getsize(poster_path) > 100


# Start the thread
threadDBemc = PosterDBEMC()
threadDBemc.daemon = True
threadDBemc.start()
