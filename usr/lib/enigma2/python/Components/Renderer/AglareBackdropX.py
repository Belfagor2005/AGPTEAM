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

# Standard library
from datetime import datetime
from os import remove, makedirs
from os.path import join, exists, getsize
from re import compile, sub
import threading
from threading import Thread, Lock
from datetime import timedelta
from time import sleep, time
from traceback import print_exc, format_exc
from collections import OrderedDict
from queue import LifoQueue
# from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

# Enigma2/Dreambox specific imports
from enigma import ePixmap, loadJPG, eEPGCache, eTimer
# from Components.config import config
from Components.Renderer.Renderer import Renderer
from Components.Sources.Event import Event
from Components.Sources.EventInfo import EventInfo
from Components.Sources.CurrentService import CurrentService
from Components.Sources.ServiceEvent import ServiceEvent
from ServiceReference import ServiceReference
import NavigationInstance

# Local imports
from Components.Renderer.AgbDownloadThread import AgbDownloadThread
from Plugins.Extensions.Aglare.plugin import ApiKeyManager, config
from .Agp_Utils import (
	BACKDROP_FOLDER,
	check_disk_space,
	delete_old_files_if_low_disk_space,
	validate_media_path,
	# MemClean,
	clean_for_tvdb,
	logger
)

if not BACKDROP_FOLDER.endswith("/"):
	BACKDROP_FOLDER += "/"

# Constants and global variables
epgcache = eEPGCache.getInstance()
epgcache.load()
pdb = LifoQueue()
# extensions = ['.jpg', '.jpeg', '.png']
extensions = ['.jpg']
autobouquet_file = None
apdb = dict()
SCAN_TIME = "02:00"


global global_agb_auto_db
AgbDB = None
db_lock = Lock()
global_agb_auto_db = None


"""
Use:
# for infobar,
<widget source="session.Event_Now" render="AglareBackdropX" position="100,100" size="185,278" />
<widget source="session.Event_Next" render="AglareBackdropX" position="100,100" size="100,150" />
<widget source="session.Event_Now" render="AglareBackdropX" position="100,100" size="185,278" nexts="2" />
<widget source="session.CurrentService" render="AglareBackdropX" position="100,100" size="185,278" nexts="3" />

# for ch,
<widget source="ServiceEvent" render="AglareBackdropX" position="100,100" size="185,278" />
<widget source="ServiceEvent" render="AglareBackdropX" position="100,100" size="185,278" nexts="2" />

# for epg, event
<widget source="Event" render="AglareBackdropX" position="100,100" size="185,278" />
<widget source="Event" render="AglareBackdropX" position="100,100" size="185,278" nexts="2" />
# or/and put tag -->  path="/media/hdd/backdrop"
"""

"""
ADVANCED CONFIGURATIONS:
<widget source="ServiceEvent" render="AglareBackdropX"
	nexts="1"
	position="1202,672"
	size="200,300"
	cornerRadius="20"
	zPosition="95"
	path="/path/to/custom_folder"   <!-- Optional -->
/>
"""


class AglareBackdropX(Renderer):
	"""
	Main Backdrop renderer class for Enigma2
	Handles Backdrop display and refresh logic

	Features:
	- Dynamic backdrop loading based on current program
	- Automatic refresh when channel/program changes
	- Multiple image format support
	- Skin-configurable providers
	- Asynchronous backdrop loading
	"""
	GUI_WIDGET = ePixmap

	def __init__(self):
		"""Initialize the backdrop renderer"""
		super().__init__()
		self.nxts = 0
		self.storage_path = BACKDROP_FOLDER
		self.extensions = extensions
		self.canal = [None] * 6
		self.pstrNm = None
		self.oldCanal = None
		self.pstcanal = None
		self.backrNm = None
		self.log_file = "/tmp/agplog/AglareBackdropX.log"
		if not exists("/tmp/agplog"):
			makedirs("/tmp/agplog")

		# Initialize default providers configuration
		self.providers = api_key_manager.get_active_providers()

		clear_all_log()
		self.backdrop_cache = {}
		if len(self.backdrop_cache) > 50:
			self.backdrop_cache.clear()
		self.show_timer = eTimer()
		self.show_timer.callback.append(self.showBackdrop)
		# Initialize helper classes with providers config
		self.backdrop_db = BackdropDB(providers=self.providers)
		self.backdrop_auto_db = BackdropAutoDB(providers=self.providers)
		logger.info("AglareBackdropX Renderer initialized")

	def applySkin(self, desktop, parent):
		"""Apply skin configuration and settings"""
		attribs = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "nexts":
				self.nxts = int(value)
			if attrib == "path":
				self.storage_path = str(value)

			attribs.append((attrib, value))

		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def changed(self, what):
		"""Handle screen/channel changes and update backdrop"""
		if not self.instance:
			return

		# Skip unnecessary updates
		if what[0] not in (self.CHANGED_DEFAULT, self.CHANGED_ALL, self.CHANGED_SPECIFIC, self.CHANGED_CLEAR):
			if self.instance:
				self.instance.hide()
			return

		source = self.source
		source_type = type(source)
		servicetype = None
		service = None
		try:
			# Handle different source types
			if source_type is ServiceEvent:
				service = self.source.getCurrentService()
				servicetype = "ServiceEvent"
			elif source_type is CurrentService:
				service = self.source.getCurrentServiceRef()
				servicetype = "CurrentService"
			elif source_type is EventInfo:
				service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
				servicetype = "EventInfo"
			elif source_type is Event:
				servicetype = "Event"
				if self.nxts:
					service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
					print('fallback service:', service)
				else:
					# Clean and store event data
					# self.canal[0] = None
					self.canal[1] = source.event.getBeginTime()
					# event_name = source.event.getEventName().replace('\xc2\x86', '').replace('\xc2\x87', '')
					event_name = sub(r"[\u0000-\u001F\u007F-\u009F]", "", self.source.event.getEventName())
					self.canal[2] = event_name
					self.canal[3] = source.event.getExtendedDescription()
					self.canal[4] = source.event.getShortDescription()
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
			if not servicetype or not self.canal[5]:
				if self.instance:
					self.instance.hide()
				return

			# Check if program changed
			curCanal = f"{self.canal[1]}-{self.canal[2]}"
			if curCanal == self.oldCanal:
				return

			if self.instance:
				self.instance.hide()

			self.oldCanal = curCanal
			self.pstcanal = clean_for_tvdb(self.canal[5])
			if not self.pstcanal:
				return

			if self.pstcanal in self.backdrop_cache:
				cached_path = self.backdrop_cache[self.pstcanal]
				if checkBackdropExistence(cached_path):
					self.showBackdrop(cached_path)
					return

			# Try to display existing backdrop
			backdrop_path = join(self.storage_path, f"{self.pstcanal}.jpg")
			if checkBackdropExistence(backdrop_path):
				self.showBackdrop(backdrop_path)
			else:
				# Queue for download if not available
				pdb.put(self.canal[:])
				self.runBackdropThread()

		except Exception as e:
			logger.error(f"Error in changed: {str(e)}")
			if self.instance:
				self.instance.hide()
			return

	def generateBackdropPath(self):
		"""Generate filesystem path for current program's backdrop"""
		if len(self.canal) > 5 and self.canal[5]:
			self.pstcanal = clean_for_tvdb(self.canal[5])
			return join(self.storage_path, str(self.pstcanal) + ".jpg")
		return None

	def runBackdropThread(self):
		"""Start background thread to wait for backdrop download"""
		"""
		# for provider in self.providers:
			# if str(self.providers[provider]).lower() == "true":
				# self._log_debug(f"Providers attivi: {provider}")
		"""
		# Thread(target=self.waitBackdrop).start()
		Thread(target=self.waitBackdrop, daemon=True).start()

	def showBackdrop(self, backdrop_path=None):
		"""Display the backdrop image"""
		if not self.instance:
			return

		if self.instance:
			self.instance.hide()

		# Use cached path if none provided
		if not backdrop_path and self.backrNm:
			backdrop_path = self.backrNm
		if backdrop_path and checkBackdropExistence(backdrop_path):
			self.instance.setPixmap(loadJPG(backdrop_path))
			self.instance.setScale(1)
			self.instance.show()

	"""
	# def showBackdrop(self, backdrop_path=None):
		# if not self.instance:
			# return
		# try:
			# path = backdrop_path or self.backrNm
			# if not path:
				# self.instance.hide()
				# return

			# if not self.check_valid_backdrop(path):
				# # logger.warning(f"Invalid backdrop file: {path}")
				# self.instance.hide()
				# return

			# max_attempts = 3
			# for attempt in range(max_attempts):
				# try:
					# pixmap = loadJPG(path)
					# if pixmap:
						# self.instance.setPixmap(pixmap)
						# self.instance.setScale(1)
						# self.instance.show()
						# # logger.debug(f"Displayed backdrop: {path}")
						# return
					# else:
						# logger.warning(f"Failed to load pixmap (attempt {attempt + 1})")
						# sleep(0.1 * (attempt + 1))
				# except Exception as e:
					# logger.error(f"Pixmap error (attempt {attempt + 1}): {str(e)}")
					# sleep(0.1 * (attempt + 1))

			# self.instance.hide()

		# except Exception as e:
			# logger.error(f"Error in showBackdrop: {str(e)}")
			# self.instance.hide()
	"""

	def waitBackdrop(self):
		"""Wait for Backdrop download to complete with retries"""
		if not self.instance or not self.canal[5]:
			return

		self.backrNm = None
		pstcanal = clean_for_tvdb(self.canal[5])
		backdrop_path = join(self.storage_path, f"{pstcanal}.jpg")

		for attempt in range(5):
			if checkBackdropExistence(backdrop_path):
				self.backrNm = backdrop_path
				# logger.debug(f"Backdrop found after {attempt} attempts")
				self.showBackdrop(backdrop_path)
				return

			sleep(0.3 * (attempt + 1))
		# logger.warning(f"backdrop not found after retries: {backdrop_path}")

	def check_valid_backdrop(self, path):
		"""Verify Backdrop is valid JPEG and >1KB"""
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
			logger.error(f"Backdrop validation error: {str(e)}")
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


class BackdropDB(AgbDownloadThread):
	"""Handles Backdrop downloading and database management"""
	def __init__(self, providers=None):
		super().__init__()

		self.queued_backdrops = set()
		# self.backdrop_cache = {}
		self.executor = ThreadPoolExecutor(max_workers=4)
		self.extensions = extensions
		self.logdbg = None
		self.pstcanal = None
		self.service_pattern = compile(r'^#SERVICE (\d+):([^:]+:[^:]+:[^:]+:[^:]+:[^:]+:[^:]+)')

		self.log_file = "/tmp/agplog/BackdropDB.log"
		if not exists("/tmp/agplog"):
			makedirs("/tmp/agplog")

		self.providers = api_key_manager.get_active_providers()
		self.provider_engines = self.build_providers()

	def build_providers(self):
		"""Initialize enabled provider search engines"""
		provider_mapping = {
			"tmdb": self.search_tmdb,
			"fanart": self.search_fanart,
			"thetvdb": self.search_tvdb,
			"elcinema": self.search_elcinema,  # no apikey
			"google": self.search_google,  # no apikey
			"omdb": self.search_omdb,
			"imdb": self.search_imdb,  # no apikey
			"programmetv": self.search_programmetv_google,  # no apikey
			"molotov": self.search_molotov_google,  # no apikey
		}
		return [
			(name, func) for name, func in provider_mapping.items()
			if self.providers.get(name, False)
		]

	def run(self):
		"""Main processing loop - handles incoming channel requests"""
		while True:
			canal = pdb.get()
			self.process_canal(canal)
			pdb.task_done()

	def process_canal(self, canal):
		"""Schedule channel processing in thread pool"""
		self.executor.submit(self._process_canal_task, canal)

	def _process_canal_task(self, canal):
		"""Download and process backdrop for a single channel"""
		try:
			self.pstcanal = clean_for_tvdb(canal[5])
			if not self.pstcanal:
				logger.error(f"Invalid channel name: {canal[0]}")
				return

			backdrop_path = join(BACKDROP_FOLDER, f"{self.pstcanal}.jpg")

			# Check if already in the queue
			"""
			if self.pstcanal in self.queued_backdrops:
				logger.debug(f"Backdrop already queued: {self.pstcanal}")
				return
			"""
			# Add to queue and process
			with Lock():
				self.queued_backdrops.add(self.pstcanal)

			try:
				# Check if a valid file already exists
				if self.check_valid_backdrop(backdrop_path):
					# logger.debug(f"Valid backdrop exists: {backdrop_path}")
					return

				logger.info(f"Starting download: {self.pstcanal}")

				# Sort providers by configured priority
				sorted_providers = sorted(
					self.provider_engines,
					key=lambda x: self.providers.get(x[0], 0),
					reverse=True
				)

				for provider_name, provider_func in sorted_providers:
					try:
						# Retrieve the API key for the current provider
						api_key = api_key_manager.get_api_key(provider_name)
						if not api_key:
							logger.warning(f"Missing API key for {provider_name}")
							continue

						# Call the provider function to download the backdrop
						result = provider_func(
							dwn_backdrop=backdrop_path,
							title=self.pstcanal,
							shortdesc=canal[4],
							fulldesc=canal[3],
							channel=canal[0],
							api_key=api_key
						)
						if result and self.check_valid_backdrop(backdrop_path):
							logger.info(f"Download successful with {provider_name}")
							break

					except Exception as e:
						logger.error(f"Error with {provider_name}: {str(e)}")
						continue

			finally:
				# Remove the channel from the queue after processing
				with Lock():
					self.queued_backdrops.discard(self.pstcanal)

		except Exception as e:
			logger.error(f"Critical error in _process_canal_task: {str(e)}")
			logger.error(format_exc())

	def check_valid_backdrop(self, path):
		"""Verify backdrop is valid JPEG and >1KB"""
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
			logger.error(f"backdrop validation error: {str(e)}")
			return False

	# def update_backdrop_cache(self, backdrop_name, path):
		# """Force update cache entry"""
		# self.backdrop_cache[backdrop_name] = path
		# # Limit cache size
		# if len(self.backdrop_cache) > 20:
			# oldest = next(iter(self.backdrop_cache))
			# del self.backdrop_cache[oldest]

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


class BackdropAutoDB(AgbDownloadThread):
	"""Automatic Backdrop download scheduler

	Features:
	- Scheduled daily scans (configurable)
	- Batch processing for efficiency
	- Automatic retry mechanism
	- Provider fallback system

	Configuration:
	- providers: Configured via plugin setup parameters
	"""
	_instance = None

	def __init__(self, providers=None, max_backdrops=1000):
		"""Initialize the backdrop downloader with provider configurations"""
		if hasattr(self, '_initialized') and self._initialized:
			return

		super().__init__()
		self._initialized = True

		self._stop_event = threading.Event()
		self._active_event = threading.Event()
		self._active_event.set()
		self._scan_lock = Lock()
		self.daemon = True

		if not config.plugins.Aglare.bkddown.value:
			logger.debug("BackdropAutoDB: Automatic downloads DISABLED in configuration")
			self.active = False
			return

		if not any(api_key_manager.get_active_providers().values()):
			logger.debug("Disabilitato - nessun provider attivo")
			self.active = False
			return

		logger.debug("BackdropAutoDB: Automatic downloads ENABLED in configuration")
		self.active = True

		self.providers = api_key_manager.get_active_providers()

		self.pstcanal = None
		self.extensions = extensions
		self.service_queue = []
		self.last_scan = 0
		self.apdb = OrderedDict()  # Active services database
		self.max_retries = 3
		self.current_retry = 0

		self.min_disk_space = 100
		self.max_backdrop_age = 30
		self.backdrop_folder = self._init_backdrop_folder()
		self.max_backdrops = max_backdrops

		self.processed_titles = OrderedDict()  # Tracks processed shows
		self.backdrop_download_count = 0
		self.provider_engines = self.build_providers()
		try:
			scan_time = config.plugins.Aglare.bscan_time.value
			self.scheduled_hour = int(scan_time[0])
			self.scheduled_minute = int(scan_time[1])
			logger.debug(f"Configured time: {self.scheduled_hour:02d}:{self.scheduled_minute:02d}")
		except Exception as e:
			logger.error("Error parsing scan time: " + str(e))
			self.scheduled_hour = 0
			self.scheduled_minute = 0

		self.last_scheduled_run = None

		self.log_file = "/tmp/agplog/BackdropAutoDB.log"
		if not exists("/tmp/agplog"):
			makedirs("/tmp/agplog")

		self._log("=== INITIALIZATION COMPLETE ===")

	def __new__(cls, *args, **kwargs):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
		return cls._instance

	def build_providers(self):
		active_providers = api_key_manager.get_active_providers()
		valid_providers = []
		provider_mapping = {
			"tmdb": self.search_tmdb,
			"fanart": self.search_fanart,
			"thetvdb": self.search_tvdb,
			"elcinema": self.search_elcinema,  # no apikey
			"google": self.search_google,  # no apikey
			"omdb": self.search_omdb,
			"imdb": self.search_imdb,  # no apikey
			"programmetv": self.search_programmetv_google,  # no apikey
			"molotov": self.search_molotov_google,  # no apikey
		}
		for name, func in provider_mapping.items():
			if active_providers.get(name, False):
				if name in ["tmdb", "fanart", "omdb"]:  # Providers requiring API keys
					key = api_key_manager.get_api_key(name)
					if not key:
						logger.error(f"Invalid API key for {name}")
						continue
				valid_providers.append((name, func))

		logger.debug(f"Active providers: {[p[0] for p in valid_providers]}")
		return valid_providers

	@property
	def active(self):
		return self._active_event.is_set()

	@active.setter
	def active(self, value):
		if value:
			self._active_event.set()
		else:
			self._active_event.clear()

	def start(self):
		if not self.is_alive():
			self.active = True
			super().start()

	def run(self):
		logger.info("BackdropAutoDB THREAD STARTED")
		# logger.info("RUNNING IN TEST MODE - BYPASSING SCHEDULER")
		# self._execute_scheduled_scan()  # Force immediate scan
		# logger.info("TEST SCAN COMPLETED")
		try:
			while self.active:
				now = datetime.now()
				next_run = self._calculate_next_run(now)
				logger.debug(f"Scheduled for: {next_run}")

				# Wait until scheduled time
				while True:
					now = datetime.now()
					remaining = (next_run - now).total_seconds()
					if remaining <= 0:
						break

					logger.debug(f"Waiting {remaining:.1f}s")
					sleep(min(remaining, 60))  # Check every minute

				logger.debug("=== SCANNING NOW ===")
				self._execute_scheduled_scan()

		except Exception as e:
			logger.error(f"CRASH: {str(e)}")
		finally:
			logger.info("BackdropAutoDB STOPPED")

	def _calculate_next_run(self, current_time):
		next_run = datetime(
			year=current_time.year,
			month=current_time.month,
			day=current_time.day,
			hour=self.scheduled_hour,
			minute=self.scheduled_minute,
			second=0  # Force seconds to 0
		)
		if next_run <= current_time:  # Use <= instead of <
			next_run += timedelta(days=1)

		logger.debug(f"Next scan: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
		return next_run

	def _execute_scheduled_scan(self):
		"""Run a single scheduled scan"""
		with self._scan_lock:
			if self.active:
				logger.debug("Starting scheduled scan")
				self._full_scan()
				self._process_services()
				self.last_scan = time()
				logger.debug("Scheduled scan completed")

	def stop(self):
		"""Safe stop with timeout"""
		self.active = False
		self._active_event.set()
		if self.is_alive():
			self.join(timeout=2.0)
		logger.debug("BackdropAutoDB fully stopped")

	def _cleanup(self):
		self.active = False
		logger.info("BackdropAutoDB stopped gracefully")

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
		"""Process all services and download backdrops"""
		for service_ref in self.apdb.values():
			try:
				events = epgcache.lookupEvent(['IBDCTESX', (service_ref, 0, -1, 1440)])
				if not events:
					self._log_debug(f"No EPG data for service: {service_ref}")
					continue

				for evt in events:
					canal = self._prepare_canal_data(service_ref, evt)
					if canal:
						self._download_backdrop(canal)

			except Exception as e:
				self._log_error(f"Error processing service {service_ref}: {str(e)}")
				print_exc()

	def _prepare_canal_data(self, service_ref, event):
		try:
			# Get service name from service reference
			service_name = ServiceReference(service_ref).getServiceName()
			service_name = service_name.replace("\xc2\x86", "").replace("\xc2\x87", "")

			# Safely get the raw event title (could be None)
			raw_title = event[4] or ""
			event_name = raw_title.strip()
			if not event_name:
				# nothing to search for, skip this event
				return None

			clean_title = clean_for_tvdb(event_name)

			logger.debug(f"Processing event: {event_name} -> {clean_title}")

			return [
				service_name,
				event[1],      # begin_time
				event_name,
				event[5],      # extended_desc
				event[6],      # short_desc
				clean_title,
			]

		except Exception as e:
			logger.error(f"Failed to parse event: {str(e)}")
			return None

	def _download_backdrop(self, canal):
		"""Download backdrop with provider fallback logic"""
		try:
			if not self._pre_download_checks(canal):
				return
			downloaded = False
			for provider_name, provider_func in self.provider_engines:
				if self._try_provider(provider_name, provider_func, canal):
					downloaded = True
					break
			if not downloaded:
				logger.error(f"Download failed for: {self.pstcanal}")
		except Exception as e:
			logger.error(f"Critical error: {str(e)}")
			print_exc()

	def _pre_download_checks(self, canal):
		"""Run pre-download checks"""
		if not canal or len(canal) < 6:
			return False

		self.pstcanal = clean_for_tvdb(canal[5] or "")
		if not self.pstcanal:
			return False

		if self.backdrop_download_count >= self.max_backdrops:
			return False

		if not self._check_storage():
			self._log("Download skipped due to insufficient storage")
			return False

		if not check_disk_space(BACKDROP_FOLDER, 10):
			logger.warning("Not enough space to download")
			return False

		return True

	def _try_provider(self, provider_name, provider_func, canal):
		"""Try downloading with a specific provider"""
		try:
			api_key = api_key_manager.get_api_key(provider_name)
			# logger.debug(f"Trying {provider_name} with key: {api_key[:3]}...")
			backdrop_path = join(BACKDROP_FOLDER, f"{self.pstcanal}.jpg")
			# logger.debug(f"Searching: {self.pstcanal} | Channel: {canal[0]}")
			result = provider_func(
				dwn_backdrop=backdrop_path,
				title=self.pstcanal,
				shortdesc=canal[4],
				fulldesc=canal[3],
				channel=canal[0],
				api_key=api_key
			)
			if result:
				logger.debug(f"{provider_name} returned URL: {result}")
				if self._validate_download(backdrop_path):
					return True
			else:
				logger.debug(f"{provider_name} returned no results")

		except Exception as e:
			logger.error(f"Error with {provider_name}: {str(e)}")

		return False

	def _validate_download(self, backdrop_path):
		"""Verify the integrity of the downloaded file"""
		if checkBackdropExistence(backdrop_path) and getsize(backdrop_path) > 1024:
			self.backdrop_download_count += 1
			return True
		return False

	def _init_backdrop_folder(self):
		"""Initialize the folder with validation"""
		try:
			return validate_media_path(
				BACKDROP_FOLDER,
				media_type="backdrops",
				min_space_mb=self.min_disk_space
			)
		except Exception as e:
			self._log_error(f"backdrop folder init failed: {str(e)}")
			return "/tmp/backdrops"

	def _check_storage(self):
		"""Version optimized using utilities"""
		try:
			if check_disk_space(self.backdrop_folder, self.min_disk_space):
				return True

			self._log("Low disk space detected, running cleanup...")
			delete_old_files_if_low_disk_space(
				self.backdrop_folder,
				min_free_space_mb=self.min_disk_space,
				max_age_days=self.max_backdrop_age
			)

			return check_disk_space(self.backdrop_folder, self.min_disk_space)

		except Exception as e:
			self._log_error(f"Storage check failed: {str(e)}")
			return False

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


def checkBackdropExistence(backdrop_path):
	return exists(backdrop_path)


def is_valid_backdrop(backdrop_path):
	"""Check if the backdrop file is valid (exists and has a valid size)"""
	return exists(backdrop_path) and getsize(backdrop_path) > 100


def clear_all_log():
	log_files = [
		"/tmp/agplog/BackdropX_errors.log",
		"/tmp/agplog/BackdropX.log",
		"/tmp/agplog/BackdropAutoDB.log"
	]
	for files in log_files:
		try:
			if exists(files):
				remove(files)
				logger.warning(f"Removed cache: {files}")
		except Exception as e:
			logger.error(f"log_files cleanup failed: {e}")


# Create an API Key Manager instance
api_key_manager = ApiKeyManager()

# download on requests
if any(api_key_manager.get_active_providers().values()):
	logger.debug("Starting BackdropDB with active providers")
	with db_lock:
		if AgbDB is None or not AgbDB.is_alive():
			AgbDB = BackdropDB()
			AgbDB.daemon = True
			AgbDB.start()
			logger.debug("BackdropDB started with PID: %s" % AgbDB.ident)
else:
	logger.debug("BackdropDB not started - no active providers")


# automatic download
if config.plugins.Aglare.bkddown.value:
	logger.debug("Starting BackdropAutoDB...")

	# Stop existing instance if any
	if global_agb_auto_db:
		global_agb_auto_db.stop()
		global_agb_auto_db = None

	# Start new instance
	global_agb_auto_db = BackdropAutoDB()
	global_agb_auto_db.daemon = True
	global_agb_auto_db.start()
	logger.debug("BackdropAutoDB ACTIVE")
