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
from Components.config import config
from os import utime
from os.path import exists, join
from re import findall
from time import sleep, time
from queue import LifoQueue
from threading import Thread
from datetime import datetime

# Enigma2/Dreambox specific imports
from Components.Renderer.Renderer import Renderer
from enigma import ePixmap, eTimer, loadJPG, eEPGCache
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.CurrentService import CurrentService

# Local imports
from .Agp_Utils import IMOVIE_FOLDER, clean_for_tvdb  # , noposter
from Components.Renderer.AgpDownloadThread import AgpDownloadThread

# Constants and global variables
epgcache = eEPGCache.getInstance()
pdbemc = LifoQueue()


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


class PosterDBEMC(AgpDownloadThread):
	"""Handles poster downloading and database management"""
	def __init__(self, providers=None):
		super().__init__()
		self.logdbg = None
		self.pstcanal = None
		self.service_pattern = compile(r'^#SERVICE (\d+):([^:]+:[^:]+:[^:]+:[^:]+:[^:]+:[^:]+)')
		default_providers = {
			"tmdb": True,
			"tvdb": False,
			"imdb": False,
			"fanart": False,
			"google": False
		}
		self.providers = {**default_providers, **(providers or {})}

	def run(self):
		"""Main processing loop"""
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

			poster_path = join(IMOVIE_FOLDER, f"{self.pstcanal}.jpg")  # fix: dwn_poster era usato ma non definito

			if exists(poster_path):
				utime(poster_path, (time(), time()))
				return

			# Create the list of enabled providers
			providers = []
			if self.providers.get("tmdb"):
				providers.append(("TMDB", self.search_tmdb))
			if self.providers.get("tvdb"):
				providers.append(("TVDB", self.search_tvdb))
			if self.providers.get("fanart"):
				providers.append(("Fanart", self.search_fanart))
			if self.providers.get("imdb"):
				providers.append(("IMDB", self.search_imdb))
			if self.providers.get("google"):
				providers.append(("Google", self.search_google))

			for provider_name, provider_func in providers:
				try:
					result = provider_func(poster_path, self.pstcanal, canal[4], canal[3], canal[0])
					if not result or len(result) != 2:
						continue

					success, log = result
					self._log_debug(f"{provider_name}: {log}")  # fix: log anche se fallisce

					if success:
						break
				except Exception as e:
					self._log_error(f"Error with engine {provider_name}: {str(e)}")
					continue

		except Exception as e:
			self._log_error(f"Processing error: {e}")

	def _log_debug(self, message):
		"""Log debug message to file"""
		try:
			with open("/tmp/agplog/AgpPosterXEMC.log", "a") as w:
				w.write(f"{datetime.now()}: {message}\n")
		except Exception as e:
			print(f"Logging error: {e}")

	def _log_error(self, message):
		"""Log error message to file"""
		try:
			with open("/tmp/agplog/AgpPosterXEMC_errors.log", "a") as f:
				f.write(f"{datetime.now()}: ERROR: {message}\n")
		except Exception as e:
			print(f"Error logging error: {e}")


class AglarePosterXEMC(Renderer):

	GUI_WIDGET = ePixmap

	def __init__(self):
		super().__init__()
		self.path = IMOVIE_FOLDER
		self.canal = [None] * 6
		self.logdbg = None
		self.pstcanal = None
		self.timer = eTimer()
		self.timer.callback.append(self.showPoster)

	def applySkin(self, desktop, parent):
		attribs = []

		self.providers = {
			"tmdb": True,
			"tvdb": False,
			"imdb": False,
			"fanart": False,
			"google": False
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
		# self.posterdb = PosterAutoDB(providers=self.providers)
		return Renderer.applySkin(self, desktop, parent)

	def changed(self, what):
		if not self.instance:
			return
		if what[0] == self.CHANGED_CLEAR:
			self.instance.hide()
			return
		self.canal = [None, None, None, None, None, None]
		try:
			if isinstance(self.source, ServiceEvent):
				self.canal[0] = None
				self.canal[1] = self.source.event.getBeginTime()
				event_name = self.source.event.getEventName().replace('\xc2\x86', '').replace('\xc2\x87', '')
				self.canal[2] = event_name
				self.canal[3] = self.source.event.getExtendedDescription()
				self.canal[4] = self.source.event.getShortDescription()
				self.canal[5] = self.source.service.getPath().split(".ts")[0] + ".jpg"
			elif isinstance(self.source, CurrentService):
				self.canal[5] = self.source.getCurrentServiceReference().getPath().split(".ts")[0] + ".jpg"
			else:
				if self.instance:
					self.instance.hide()
				return

		except Exception as e:
			print("Error (service processing):", str(e))
			if self.instance:
				self.instance.hide()
			return
		try:
			match = findall(r".*? - (.*?) - (.*?).jpg", self.canal[5])
			if match and len(match[0]) > 1:
				self.canal[0] = match[0][0].strip()
				if not self.canal[2]:
					self.canal[2] = match[0][1].strip()

			self._log_debug("Service: {} - {} => {}".format(self.canal[0], self.canal[2], self.canal[5]))
			if self.canal[5]:
				self.timer.start(10, True)
			elif self.canal[0] and self.canal[2]:
				canal = self.canal[:]
				pdbemc.put(canal)
				# start_new_thread(self.waitPoster, ())
				self.runPosterThread()
			else:
				self._log_debug("Not detected...")
				if self.instance:
					self.instance.hide()
		except Exception as e:
			print("Error (file processing):", str(e))
			if self.instance:
				self.instance.hide()

	def generatePosterPath(self):
		"""Generate poster path from current channel data"""
		if len(self.canal) > 5 and self.canal[5]:
			self.pstcanal = clean_for_tvdb(self.canal[5])
			return join(self.path, str(self.pstcanal) + ".jpg")
		return None

	# @lru_cache(maxsize=150)
	def checkPosterExistence(self, poster_path):
		"""Check if poster file exists"""
		return exists(poster_path)

	def runPosterThread(self):
		"""Start poster download thread"""
		Thread(target=self.waitPoster).start()

	def showPoster(self):
		"""Display the poster image"""

		if self.instance:
			print('showPoster ide instance if self')
			self.instance.hide()
		"""
		if not self.instance:
			return
		"""
		if not self.pstrNm or not self.checkPosterExistence(self.pstrNm):
			self.instance.hide()
			print('showPoster ide instance')
			return

		print(f"[LOAD] Showing poster: {self.pstrNm}")
		self.instance.setPixmap(loadJPG(self.pstrNm))
		self.instance.setScale(1)
		self.instance.show()

	def waitPoster(self):
		"""Wait for poster download to complete"""
		self.pstrNm = self.generatePosterPath()
		if not hasattr(self, 'pstrNm') or self.pstrNm is None:  # <-- CONTROLLO AGGIUNTO
			self._log_error("pstrNm not initialized in waitPoster")
			return
		self.pstrNm = self.generatePosterPath()
		if not hasattr(self, 'pstrNm') or self.pstrNm is None:
			self._log_error("waitPosterXEMC pstrNm not initialized in waitPoster")
			return

		if not self.pstrNm:
			self.logPoster("[ERROR: waitPosterXEMC] Poster path is None")
			return

		loop = 180  # Maximum number of attempts
		found = False
		print(f"[WAIT] Checking for poster: {self.pstrNm}")
		while loop > 0:
			if self.pstrNm and self.checkPosterExistence(self.pstrNm):
				found = True
				break
			sleep(0.5)
			loop -= 1

		if found:
			self.timer.start(10, True)

	def _log_debug(self, message):
		"""Log debug message to file"""
		try:
			with open("/tmp/agplog/AgpPosterXEMC.log", "a") as w:
				w.write(f"{datetime.now()}: {message}\n")
		except Exception as e:
			print(f"Logging error: {e}")

	def _log_error(self, message):
		"""Log error message to file"""
		try:
			with open("/tmp/agplog/AgpPosterXEMC_errors.log", "a") as f:
				f.write(f"{datetime.now()}: ERROR: {message}\n")
		except Exception as e:
			print(f"Error logging error: {e}")


threadDBemc = PosterDBEMC()
threadDBemc.start()
