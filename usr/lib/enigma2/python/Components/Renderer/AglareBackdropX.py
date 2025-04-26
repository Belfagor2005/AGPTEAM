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
from threading import Thread, Lock
from time import sleep, time
from traceback import print_exc, format_exc
from collections import OrderedDict
from queue import LifoQueue
# from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

# Enigma2/Dreambox specific imports
from enigma import ePixmap, loadJPG, eEPGCache, eTimer
from Components.config import config
from Components.Renderer.Renderer import Renderer
from Components.Sources.Event import Event
from Components.Sources.EventInfo import EventInfo
from ServiceReference import ServiceReference
import NavigationInstance

# Local imports
from Components.Renderer.AgbDownloadThread import AgbDownloadThread
from Plugins.Extensions.Aglare.plugin import ApiKeyManager
from .Agp_Utils import (
	BACKDROP_FOLDER,
	check_disk_space,
	delete_old_files_if_low_disk_space,
	validate_media_path,
	# MemClean,
	clean_for_tvdb,
	logger
)

# Constants and global variables
epgcache = eEPGCache.getInstance()
epgcache.load()
pdb = LifoQueue()
# extensions = ['.jpg', '.jpeg', '.png']
extensions = ['.jpg']
autobouquet_file = None
apdb = dict()
SCAN_TIME = "02:00"


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
		self.path = BACKDROP_FOLDER
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
		self.show_timer = eTimer()
		self.show_timer.callback.append(self.showBackdrop)
		# Initialize helper classes with providers config
		self.backdrop_db = BackdropDB(providers=self.providers)
		self.backdrop_auto_db = BackdropAutoDB(providers=self.providers)

	def applySkin(self, desktop, parent):
		"""Apply skin configuration and settings"""
		attribs = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "nexts":
				self.nxts = int(value)
			if attrib == "path":
				self.path = str(value)

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
			if source_type is EventInfo:
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

			# Skip if no valid program data
			if not servicetype or not self.canal[5]:
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
			self.pstcanal = clean_for_tvdb(self.canal[5])
			if not self.pstcanal:
				return

			# Try to display existing backdrop
			backdrop_path = join(self.path, f"{self.pstcanal}.jpg")
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
			return join(self.path, str(self.pstcanal) + ".jpg")
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

		try:
			path = backdrop_path or self.backrNm
			if not path:
				self.instance.hide()
				return

			if not self.check_valid_backdrop(path):
				# logger.warning(f"Invalid backdrop file: {path}")
				self.instance.hide()
				return

			max_attempts = 3
			for attempt in range(max_attempts):
				try:
					pixmap = loadJPG(path)
					if pixmap:
						self.instance.setPixmap(pixmap)
						self.instance.setScale(1)
						self.instance.show()
						# logger.debug(f"Displayed backdrop: {path}")
						return
					else:
						logger.warning(f"Failed to load pixmap (attempt {attempt + 1})")
						sleep(0.1 * (attempt + 1))
				except Exception as e:
					logger.error(f"Pixmap error (attempt {attempt + 1}): {str(e)}")
					sleep(0.1 * (attempt + 1))

			self.instance.hide()

		except Exception as e:
			logger.error(f"Error in showBackdrop: {str(e)}")
			self.instance.hide()

	def waitBackdrop(self):
		"""Wait for Backdrop download to complete with retries"""
		if not self.instance or not self.canal[5]:
			return

		self.backrNm = None
		pstcanal = clean_for_tvdb(self.canal[5])
		backdrop_path = join(self.path, f"{pstcanal}.jpg")

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
		self.backdrop_cache = {}

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
			# "omdb": self.search_omdb,
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
			canal = pdb.get()  # Get channel from queue
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

	def update_backdrop_cache(self, backdrop_name, path):
		"""Force update cache entry"""
		self.backdrop_cache[backdrop_name] = path
		# Limit cache size
		if len(self.backdrop_cache) > 20:
			oldest = next(iter(self.backdrop_cache))
			del self.backdrop_cache[oldest]

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

		if not config.plugins.Aglare.bkddown.value:
			logger.debug("BackdropAutoDB: Automatic downloads DISABLED in configuration")
			self.active = False
			return

		logger.debug("BackdropAutoDB: Automatic downloads ENABLED in configuration")
		self.active = True
		if not any(api_key_manager.get_active_providers().values()):
			logger.debug("Disabilitato - nessun provider attivo")
			self.active = False
			return

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
			# Get scan time from config instead of global
			scan_time = config.plugins.Aglare.bscan_time.value
			hour, minute = map(int, scan_time.split(":"))
			self.scheduled_hour = hour
			self.scheduled_minute = minute
		except Exception as e:
			logger.error(f"Error parsing scan time: {str(e)}")
			self.scheduled_hour = 0  # Default to midnight
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
		"""Initialize enabled provider search engines"""
		provider_mapping = {
			"tmdb": self.search_tmdb,
			"fanart": self.search_fanart,
			"thetvdb": self.search_tvdb,
			"elcinema": self.search_elcinema,  # no apikey
			"google": self.search_google,  # no apikey
			# "omdb": self.search_omdb,
			"imdb": self.search_imdb,  # no apikey
			"programmetv": self.search_programmetv_google,  # no apikey
			"molotov": self.search_molotov_google,  # no apikey
		}
		return [
			(name, func) for name, func in provider_mapping.items()
			if self.providers.get(name, False)
		]

	def run(self):
		"""Main execution loop - handles scheduled operations"""
		self._log("Renderer initialized - Starting main loop")

		if not hasattr(self, 'active') or not self.active:
			logger.debug("BackdropAutoDB thread terminated - disabled in configuration")
			return

		if not config.plugins.Aglare.bkddown:
			self._log("Auto download disabled - thread termination")
			return

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
				event[4]   # backdrop name
			]
			return canal
		except Exception as e:
			self._log_error(f"Error preparing channel data: {str(e)}")
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
			if not api_key:
				logger.warning(f"API key missing for {provider_name}")
				return False

			backdrop_path = join(BACKDROP_FOLDER, f"{self.pstcanal}.jpg")
			result = provider_func(
				dwn_backdrop=backdrop_path,
				title=self.pstcanal,
				shortdesc=canal[4],
				fulldesc=canal[3],
				channel=canal[0],
				api_key=api_key
			)
			if result and self._validate_download(backdrop_path):
				logger.info(f"Download successful with {provider_name}")
				return True

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
	AgbDB = BackdropDB()
	AgbDB.daemon = True
	AgbDB.start()
else:
	logger.debug("BackdropDB not started - no active providers")

# automatic download
if config.plugins.Aglare.bkddown.value:
	logger.debug("Start BackdropAutoDB - configuration ENABLED")
	# Get active providers from the central manager
	active_providers = api_key_manager.get_active_providers()

	if any(active_providers.values()):
		logger.debug("VALID configuration - at least one provider is active")
		AgbAutoDB = BackdropAutoDB()

		if AgbAutoDB.active:
			AgbAutoDB.daemon = True
			AgbAutoDB.start()
			logger.debug("BackdropAutoDB SUCCESSFULLY STARTED")
		else:
			logger.debug("BackdropAutoDB internally disabled")
			AgbAutoDB = type('DisabledBackdropAutoDB', (), {'start': lambda self: None})()
	else:
		logger.debug("INVALID configuration - no active providers")
		AgbAutoDB = type('DisabledBackdropAutoDB', (), {'start': lambda self: None})()
else:
	logger.debug("BackdropAutoDB NOT started - downloads disabled in configuration")
	AgbAutoDB = type('DisabledBackdropAutoDB', (), {'start': lambda self: None})()
