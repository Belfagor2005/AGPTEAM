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
from datetime import datetime
from os import remove, utime, makedirs
from os.path import join, exists, getsize
from re import compile, sub
from threading import Thread
from time import sleep, time
from traceback import print_exc
from collections import OrderedDict
from queue import LifoQueue
# from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

# Enigma2/Dreambox specific imports
from enigma import ePixmap, loadJPG, eEPGCache, eTimer
from Components.Renderer.Renderer import Renderer
from Components.Sources.CurrentService import CurrentService
from Components.Sources.Event import Event
from Components.Sources.EventInfo import EventInfo
from Components.Sources.ServiceEvent import ServiceEvent
from ServiceReference import ServiceReference
import NavigationInstance

# Local imports
from Components.Renderer.AgpDownloadThread import AgpDownloadThread
from .Agp_Utils import POSTER_FOLDER, clean_for_tvdb, logger


# Constants and global variables
epgcache = eEPGCache.getInstance()
epgcache.load()
pdb = LifoQueue()
# extensions = ['.jpg', '.jpeg', '.png']
extensions = ['.jpg']
autobouquet_file = None
apdb = dict()
SCAN_TIME = "00:00"


"""
Use:
# for infobar,
<widget source="session.Event_Now" render="AglarePosterX" position="100,100" size="185,278" />
<widget source="session.Event_Next" render="AglarePosterX" position="100,100" size="100,150" />
<widget source="session.Event_Now" render="AglarePosterX" position="100,100" size="185,278" nexts="2" />
<widget source="session.CurrentService" render="AglarePosterX" position="100,100" size="185,278" nexts="3" />

# for ch,
<widget source="ServiceEvent" render="AglarePosterX" position="100,100" size="185,278" />
<widget source="ServiceEvent" render="AglarePosterX" position="100,100" size="185,278" nexts="2" />

# for epg, event
<widget source="Event" render="AglarePosterX" position="100,100" size="185,278" />
<widget source="Event" render="AglarePosterX" position="100,100" size="185,278" nexts="2" />
# or/and put tag -->  path="/media/hdd/poster"
"""

"""
ADVANCED CONFIGURATIONS:
<widget source="ServiceEvent" render="AglarePosterX"
	nexts="1"
	position="1202,672"
	size="200,300"
	cornerRadius="20"
	zPosition="95"
	path="/path/to/custom_folder"   <!-- Optional -->
	service.tmdb="true"             <!-- Enable TMDB -->
	service.tvdb="false"            <!-- Disable TVDB -->
	service.imdb="false"            <!-- Disable IMDB -->
	service.fanart="false"          <!-- Disable Fanart -->
	service.google="false"          <!-- Disable Google -->
	scan_time="00:00"               <!-- Set the start time for poster download -->
/>
"""


class AglarePosterX(Renderer):
	"""
	Main Poster renderer class for Enigma2
	Handles Poster display and refresh logic

	Features:
	- Dynamic poster loading based on current program
	- Automatic refresh when channel/program changes
	- Multiple image format support
	- Skin-configurable providers
	- Asynchronous poster loading
	"""
	GUI_WIDGET = ePixmap

	def __init__(self):
		"""Initialize the poster renderer"""
		super().__init__()
		self.nxts = 0
		self.path = POSTER_FOLDER
		self.extensions = extensions
		self.canal = [None] * 6
		self.pstrNm = None
		self.oldCanal = None
		self.pstcanal = None
		self.backrNm = None
		self.log_file = "/tmp/agplog/AglarePosterX.log"
		if not exists("/tmp/agplog"):
			makedirs("/tmp/agplog")
		self.providers = {}  # Poster providers configuration
		clear_all_log()

		self.queued_posters = set()
		self.loaded_posters = set()

		self.poster_cache = {}
		if len(self.poster_cache) > 50:
			self.poster_cache.clear()

		self.last_service = None

		self.show_timer = eTimer()
		self.show_timer.callback.append(self.showPoster)

	def applySkin(self, desktop, parent):
		"""Apply skin configuration and settings"""
		global SCAN_TIME
		attribs = []
		scan_time = SCAN_TIME

		# Default provider configuration
		self.providers = {
			"tmdb": True,       # The Movie Database
			"tvdb": False,      # The TV Database
			"imdb": False,      # Internet Movie Database
			"fanart": False,    # Fanart.tv
			"google": False     # Google Images
		}

		for (attrib, value) in self.skinAttributes:
			if attrib == "nexts":
				self.nxts = int(value)  # Set next service flag
			if attrib == "path":
				self.path = str(value)  # Set custom poster path
			if attrib.startswith("service."):
				provider = attrib.split(".")[1]
				if provider in self.providers:
					self.providers[provider] = value.lower() == "true"
			if attrib == "scan_time":
				scan_time = str(value)  # Set scan time from skin

			attribs.append((attrib, value))

		SCAN_TIME = scan_time
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def changed(self, what):
		"""Handle screen/channel changes and update poster"""
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

		source = self.source
		source_type = type(source)
		servicetype = None
		service = None
		try:
			# Handle different source types
			if source_type is ServiceEvent:
				service = self.source.getCurrentService()
				servicetype = "ServiceEvent"
				# self._log_debug(f"ServiceEvent: service = {service}")
			elif source_type is CurrentService:
				service = self.source.getCurrentServiceRef()
				servicetype = "CurrentService"
				# self._log_debug(f"CurrentService: service = {service}")
			elif source_type is EventInfo:
				service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
				servicetype = "EventInfo"
				# self._log_debug(f"EventInfo: service = {service}")
			elif source_type is Event:
				servicetype = "Event"
				# self._log_debug("Event type detected")
				if self.nxts:
					service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
					print('fallback service:', service)
				else:
					# Clean and store event data
					self.canal[0] = None
					self.canal[1] = self.source.event.getBeginTime()
					# event_name = self.source.event.getEventName().replace('\xc2\x86', '').replace('\xc2\x87', '')
					event_name = sub(r"[\u0000-\u001F\u007F-\u009F]", "", self.source.event.getEventName())
					self.canal[2] = event_name
					self.canal[3] = self.source.event.getExtendedDescription()
					self.canal[4] = self.source.event.getShortDescription()
					self.canal[5] = event_name
					# self._log_debug(f"Event details set: {self.canal}")

			else:
				servicetype = None

			if service is not None:
				service_str = service.toString()
				# self._log_debug(f"Service string: {service_str}")
				events = epgcache.lookupEvent(['IBDCTESX', (service_str, 0, -1, -1)])

				if not events or len(events) <= self.nxts:
					# self._log_debug("No events or insufficient events")
					if self.instance:
						self.instance.hide()
					return

				service_name = ServiceReference(service).getServiceName().replace('\xc2\x86', '').replace('\xc2\x87', '')
				# self._log_debug(f"Service name: {service_name}")
				self.canal = [None] * 6
				self.canal[0] = service_name
				self.canal[1] = events[self.nxts][1]
				self.canal[2] = events[self.nxts][4]
				self.canal[3] = events[self.nxts][5]
				self.canal[4] = events[self.nxts][6]
				self.canal[5] = self.canal[2]
				# self._log_debug(f"Event data set: {self.canal}")

				if not autobouquet_file and service_name not in apdb:
					apdb[service_name] = service_str

			# Skip if no valid program data
			if not servicetype:
				if self.instance:
					self.instance.hide()
				return

			# Check if program changed
			curCanal = f"{self.canal[1]}-{self.canal[2]}"
			if curCanal == self.oldCanal:
				return  # Same program, no update needed

			if self.instance:
				self.instance.hide()

			self.oldCanal = curCanal
			self.pstcanal = clean_for_tvdb(self.canal[5])  # if self.canal[5] else None
			if not self.pstcanal:
				return

			if self.pstcanal in self.poster_cache:
				cached_path = self.poster_cache[self.pstcanal]
				if checkPosterExistence(cached_path):
					self.showPoster(cached_path)
					return

			# Try to display existing poster
			poster_path = join(self.path, f"{self.pstcanal}.jpg")

			# self._log_debug(f"Event name used for poster: {self.canal[5]}")
			# self._log_debug(f"Poster path: {poster_path}")

			if checkPosterExistence(poster_path):
				self.showPoster(poster_path)
			else:
				# Queue for download if not available
				pdb.put(self.canal[:])
				self.runPosterThread()

		except Exception as e:
			logger.error(f"Error in changed: {str(e)}")
			if self.instance:
				self.instance.hide()
			return

	def generatePosterPath(self):
		"""Generate filesystem path for current program's poster"""
		if len(self.canal) > 5 and self.canal[5]:
			self.pstcanal = clean_for_tvdb(self.canal[5])
			return join(self.path, str(self.pstcanal) + ".jpg")
		return None

	def runPosterThread(self):
		"""Start background thread to wait for poster download"""
		"""
		# for provider in self.providers:
			# if str(self.providers[provider]).lower() == "true":
				# self._log_debug(f"Providers attivi: {provider}")
		"""
		Thread(target=self.waitPoster).start()
		# Thread(target=self.waitPoster, daemon=True).start()

	def showPoster(self, poster_path=None):
		"""Display the poster image"""
		if not self.instance:
			return

		if self.instance:
			self.instance.hide()

		# Use cached path if none provided
		if not poster_path and self.backrNm:
			poster_path = self.backrNm
		if poster_path and checkPosterExistence(poster_path):
			self.instance.setPixmap(loadJPG(poster_path))
			self.instance.setScale(1)
			self.instance.show()

	def waitPoster(self):
		"""Wait for poster download to complete with retries"""
		if not self.instance or not self.canal[5]:
			return

		self.backrNm = None
		self.instance.hide()
		pstcanal = clean_for_tvdb(self.canal[5])
		backrNm = join(self.path, pstcanal + ".jpg")
		# Retry with increasing delays
		for attempt in range(5):
			if checkPosterExistence(backrNm):
				self.backrNm = backrNm
				self.show_timer.start(10, True)  # Show after short delay
				return

			sleep(0.3 * (attempt + 1))  # Progressive delay: 0.3s, 0.6s, 0.9s etc.

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


class PosterDB(AgpDownloadThread):
	"""Handles poster downloading and database management"""
	def __init__(self, providers=None):
		super().__init__()
		self.executor = ThreadPoolExecutor(max_workers=4)
		self.extensions = extensions
		self.logdbg = None
		self.pstcanal = None  # Current channel being processed
		self.service_pattern = compile(r'^#SERVICE (\d+):([^:]+:[^:]+:[^:]+:[^:]+:[^:]+:[^:]+)')
		self.log_file = "/tmp/agplog/PosterDB.log"
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
			canal = pdb.get()  # Get channel from queue
			self.process_canal(canal)
			pdb.task_done()

	def prefetch_popular_posters(self):
		"""Pre-load posters for frequently watched channels"""
		popular_channels = self.get_popular_channels()  # Da implementare
		for channel in popular_channels:
			poster_path = join(POSTER_FOLDER, f"{channel}.jpg")
			if checkPosterExistence(poster_path):
				self.picload.startDecode(poster_path)

	@staticmethod
	def check_poster_exists(poster_name):
		"""Check if poster exists (any supported extension)"""
		base_path = join(POSTER_FOLDER, poster_name)
		return any(exists(f"{base_path}{ext}") for ext in extensions)

	def process_canal(self, canal):
		"""Schedule channel processing in thread pool"""
		self.executor.submit(self._process_canal_task, canal)

	def _process_canal_task(self, canal):
		"""Download and process poster for a single channel"""
		try:
			self.pstcanal = clean_for_tvdb(canal[5])
			if not self.pstcanal:
				print(f"Invalid channel name: {canal[0]}")
				return

			if not any(self.providers.values()):
				self._log_debug("No provider is enabled for poster download")
				return

			# Check if poster already exists
			poster_path = join(POSTER_FOLDER, f"{self.pstcanal}.jpg")
			if self.check_poster_exists(self.pstcanal):
				utime(poster_path, (time(), time()))
				return

			# Try each enabled provider until successful
			downloaded = False
			for provider_name, provider_func in self.provider_engines:
				if downloaded:
					break

				try:
					result = provider_func(poster_path, self.pstcanal, canal[4], canal[3], canal[0])
					if not result or len(result) != 2:
						continue  # Skip if result is not as expected

					success, log = result
					self._log_debug(f"{provider_name}: {log}")

					if success and checkPosterExistence(poster_path):
						downloaded = True
					else:
						self.mark_failed_attempt(self.pstcanal)
				except Exception as e:
					self._log_error(f"Error with engine {provider_name}: {str(e)}")

		except Exception as e:
			self._log_error(f"Processing error: {e}")
			print_exc()

	def mark_failed_attempt(self, canal_name):
		"""Track failed download attempts"""
		self._log_debug(f"Failed attempt for {canal_name}")

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


class PosterAutoDB(AgpDownloadThread):
	"""Automatic Poster download scheduler

	Features:
	- Scheduled daily scans (configurable)
	- Batch processing for efficiency
	- Automatic retry mechanism
	- Provider fallback system

	Configuration:
	- scan_time: Set via SCAN_TIME global
	- providers: Configured via skin parameters
	"""
	def __init__(self, providers=None, max_posters=2000):
		"""Initialize the poster downloader with provider configurations"""
		super().__init__()
		self.pstcanal = None  # Current channel being processed
		self.extensions = extensions
		self.service_queue = []
		self.last_scan = 0
		self.apdb = OrderedDict()  # Active services database
		self.max_retries = 3
		self.current_retry = 0
		default_providers = {
			"tmdb": True,       # The Movie Database
			"tvdb": False,      # The TV Database
			"imdb": False,      # Internet Movie Database
			"fanart": False,    # Fanart.tv
			"google": False     # Google Images
		}
		self.providers = {**default_providers, **(providers or {})}
		self.max_posters = max_posters
		self.processed_titles = OrderedDict()  # Tracks processed shows
		self.poster_download_count = 0
		try:
			hour, minute = map(int, SCAN_TIME.split(":"))
			self.scheduled_hour = hour
			self.scheduled_minute = minute
		except ValueError:
			self.scheduled_hour = 0
			self.scheduled_minute = 0

		self.last_scheduled_run = None

		self.log_file = "/tmp/agplog/PosterAutoDB.log"
		if not exists("/tmp/agplog"):
			makedirs("/tmp/agplog")
		self.provider_engines = self.build_providers()
		self._log("=== INITIALIZATION COMPLETE ===")

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
		"""Main execution loop - handles scheduled operations"""
		self._log("Renderer initialized - Starting main loop")

		while True:
			try:
				current_time = time()
				now = datetime.now()

				# Check if 2 hours passed since last scan
				do_time_scan = current_time - self.last_scan > 7200 or not self.last_scan

				# Check scheduled daily scan time
				do_scheduled_scan = (
					now.hour == self.scheduled_hour and
					now.minute == self.scheduled_minute and
					(not self.last_scheduled_run or self.last_scheduled_run.date() != now.date())
				)

				if do_time_scan or do_scheduled_scan:
					self._full_scan()
					self.last_scan = current_time
					if do_scheduled_scan:
						self.last_scheduled_run = now
					self.current_retry = 0

				self._process_services()
				sleep(60)

			except Exception as e:
				self.current_retry += 1
				self._log_error(f"Error in main loop (retry {self.current_retry}/{self.max_retries}): {str(e)}")
				print_exc()
				if self.current_retry >= self.max_retries:
					self._log("Max retries reached, restarting...")
					self.current_retry = 0
					sleep(300)

	def _full_scan(self):
		"""Scan all available TV services"""
		self._log("Starting full service scan")
		self.service_queue = self._load_services()
		self._log(f"Scan completed, found {len(self.service_queue)} services")

	def _load_services(self):
		"""Load services from Enigma2 bouquet files"""
		services = OrderedDict()
		fav_path = "/etc/enigma2/userbouquet.favourites.tv"
		bouquets = [fav_path] if exists(fav_path) else []

		main_path = "/etc/enigma2/bouquets.tv"
		if exists(main_path):
			try:
				with open(main_path, "r") as f:
					bouquets += [
						"/etc/enigma2/" + line.split("\"")[1]
						for line in f
						if line.startswith("#SERVICE") and "FROM BOUQUET" in line
					]
			except Exception as e:
				self._log_error(f"Error reading bouquets.tv: {str(e)}")

		for bouquet in bouquets:
			if exists(bouquet):
				try:
					with open(bouquet, "r", encoding="utf-8", errors="ignore") as f:
						for line in f:
							line = line.strip()
							if line.startswith("#SERVICE") and "FROM BOUQUET" not in line:
								service_ref = line[9:]
								if self._is_valid_service(service_ref):
									services[service_ref] = None
									self.apdb[service_ref] = service_ref
				except Exception as e:
					self._log_error(f"Error reading bouquet {bouquet}: {str(e)}")

		return list(services.keys())

	def _is_valid_service(self, sref):
		"""Validate service reference format"""
		parts = sref.split(':')
		if len(parts) < 6:
			return False
		return parts[3:6] != ["0", "0", "0"]

	def _process_services(self):
		"""Process all services and download posters"""
		for service_ref in self.apdb.values():
			try:
				events = epgcache.lookupEvent(['IBDCTESX', (service_ref, 0, -1, 1440)])
				if not events:
					self._log_debug(f"No EPG data for service: {service_ref}")
					continue

				for evt in events:
					canal = self._prepare_canal_data(service_ref, evt)
					if canal:
						self._download_poster(canal)

			except Exception as e:
				self._log_error(f"Error processing service {service_ref}: {str(e)}")
				print_exc()

	def _prepare_canal_data(self, service_ref, event):
		"""Prepare channel data from EPG event"""
		try:
			service_name = ServiceReference(service_ref).getServiceName()
			if not service_name:
				service_name = "Channel_" + service_ref.split(':')[3]

			canal = [
				service_name.replace('\xc2\x86', '').replace('\xc2\x87', ''),
				event[1],  # begin_time
				event[4],  # event_name
				event[5],  # extended_desc
				event[6],  # short_desc
				event[4]   # poster name
			]
			return canal
		except Exception as e:
			self._log_error(f"Error preparing channel data: {str(e)}")
			return None

	def _download_poster(self, canal):
		"""Download poster with provider fallback logic"""
		try:
			if self.poster_download_count >= self.max_posters:
				return

			if not canal or len(canal) < 6:
				return

			if not any(self.providers.values()):
				self._log_debug("No provider is enabled for poster download")
				return

			event_name = str(canal[5]) if canal[5] else ""
			self.pstcanal = clean_for_tvdb(event_name) if event_name else None

			if not self.pstcanal:
				return

			# Check if title was already successfully processed
			if self.pstcanal in self.processed_titles:
				if self.processed_titles[self.pstcanal] == "SUCCESS":
					return
				elif self.processed_titles[self.pstcanal] >= self.max_retries:
					return

			# Check if file already exists
			for ext in extensions:
				poster_path = join(POSTER_FOLDER, self.pstcanal + ext)
				if checkPosterExistence(poster_path):
					utime(poster_path, (time(), time()))
					self.processed_titles[self.pstcanal] = "SUCCESS"
					return

			# Try each enabled provider
			downloaded = False
			for provider_name, provider_func in self.provider_engines:
				try:
					result = provider_func(poster_path, self.pstcanal, canal[4], canal[3], canal[0])
					if not result or len(result) != 2:
						continue

					success, log = result
					if success and log and "SUCCESS" in str(log).upper():
						if not checkPosterExistence(poster_path):
							self.poster_download_count += 1
							self._log(f"Poster downloaded from {provider_name}: {self.pstcanal}")
							self.processed_titles[self.pstcanal] = "SUCCESS"
						downloaded = True
						break
					else:
						if self.pstcanal in self.processed_titles:
							self.processed_titles[self.pstcanal] += 1
						else:
							self.processed_titles[self.pstcanal] = 1
						self._log(f"Skip downloaded from {provider_name}: {self.pstcanal}")
				except Exception as e:
					self._log_error(f"Error with {provider_name}: {str(e)}")

			if not downloaded:
				self._log_debug(f"Poster download failed for: {self.pstcanal}")

		except Exception as e:
			self._log_error(f"CRITICAL ERROR in _download_poster: {str(e)}")
			print_exc()

	def _log(self, message):
		self._write_log("INFO", message)

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


def clear_all_log():
	log_files = [
		"/tmp/agplog/PosterX_errors.log",
		"/tmp/agplog/PosterX.log",
		"/tmp/agplog/PosterAutoDB.log"
	]
	for files in log_files:
		try:
			if exists(files):
				remove(files)
				logger.warning(f"Removed cache: {files}")
		except Exception as e:
			logger.error(f"log_files cleanup failed: {e}")


# download on requests
AgpDB = PosterDB()
AgpDB.daemon = True
AgpDB.start()

# automatic download
AgpAutoDB = PosterAutoDB()
AgpAutoDB.daemon = True
AgpAutoDB.start()
