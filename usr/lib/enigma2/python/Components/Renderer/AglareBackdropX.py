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
#														#
#  Last Modified: "15:14 - 20250401"					#
#														#
#  Credits:												#
#	by base code from digiteng 2022						#
#  - Original concept by Lululla						#
#  - TMDB API integration								#
#  - TVDB API integration								#
#  - OMDB API integration								#
#  - Advanced caching system							#
#														#
#  Usage of this code without proper attribution		#
#  is strictly prohibited.								#
#  For modifications and redistribution,				#
#  please maintain this credit header.					#
#########################################################
"""
__author__ = "Lululla"
__copyright__ = "AGP Team"

# Standard library imports
from datetime import datetime
from glob import glob
from os import remove, utime, makedirs
from os.path import join, exists, getmtime, getsize
from re import compile
from threading import Thread
from time import sleep, time
from traceback import print_exc
from collections import OrderedDict
from queue import LifoQueue

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
from Components.Renderer.AgbDownloadThread import AgbDownloadThread
from .Agp_Utils import BACKDROP_FOLDER, clean_for_tvdb, logger	# , nobackdrop


# Constants and global variables
epgcache = eEPGCache.getInstance()
epgcache.load()
pdb = LifoQueue()
rw_mounts = ["/media/usb", "/media/hdd", "/media/mmc", "/media/sd"]
extensions = ['.jpg', '.jpeg', '.png']
autobouquet_file = None
apdb = dict()
SCAN_TIME = "02:00"


"""
Use:
# for infobar,
<widget source="session.Event_Now" render="AglareBackdropX" position="100,100" size="680,1000" />
<widget source="session.Event_Next" render="AglareBackdropX" position="100,100" size="680,1000" />
<widget source="session.Event_Now" render="AglareBackdropX" position="100,100" size="680,1000" nexts="2" />
<widget source="session.CurrentService" render="AglareBackdropX" position="100,100" size="680,1000" nexts="3" />
# for ch,
<widget source="ServiceEvent" render="AglareBackdropX" position="100,100" size="680,1000" nexts="2" />
<widget source="ServiceEvent" render="AglareBackdropX" position="100,100" size="185,278" nexts="2" />
# for epg, event
<widget source="Event" render="AglareBackdropX" position="100,100" size="680,1000" />
<widget source="Event" render="AglareBackdropX" position="100,100" size="680,1000" nexts="2" />
or put tag -->	path="/media/hdd/backdrop"
"""

"""
ADVANCED CONFIGURATIONS:
<widget source="ServiceEvent" render="AglareBackdropX"
	nexts="1"
	position="1202,672"
	size="200,300"
	cornerRadius="20"
	zPosition="95"
	path="/path/to/custom_folder"	<!-- Opzionale -->
	service.tmdb="true"				<!-- Abilita TMDB -->
	service.tvdb="false"			<!-- Disabilita TVDB -->
	service.imdb="false"			<!-- Disabilita IMDB -->
	service.fanart="false"			<!-- Disabilita Fanart -->
	service.google="false"			<!-- Disabilita Google -->
	scan_time="02:00"				<!-- Set the start time for backdrop download -->
/>
"""


class AglareBackdropX(Renderer):
	"""
	Main backdrop renderer class for Enigma2
	Handles backdrop display and refresh logic
	"""
	GUI_WIDGET = ePixmap

	def __init__(self):
		super().__init__()
		self.nxts = 0
		self.path = BACKDROP_FOLDER
		self.extensions = extensions
		self.canal = [None] * 6
		self.pstrNm = None
		self.oldCanal = None
		self.logdbg = None
		self.pstcanal = None
		self.loaded_backdrops = set()
		self.timer = eTimer()
		self.timer.callback.append(self.showBackdrop)

	def applySkin(self, desktop, parent):
		global SCAN_TIME
		attribs = []
		scan_time = SCAN_TIME
		self.providers = {
			"tmdb": True,
			"tvdb": False,
			"imdb": False,
			"fanart": False,
			"google": False
		}

		for (attrib, value) in self.skinAttributes:
			if attrib == "nexts":
				self.nxts = int(value)
			if attrib == "path":
				self.path = str(value)
			if attrib.startswith("service."):
				provider = attrib.split(".")[1]
				if provider in self.providers:
					self.providers[provider] = value.lower() == "true"
			if attrib == "scan_time":
				scan_time = str(value)

			attribs.append((attrib, value))

		SCAN_TIME = scan_time
		self.skinAttributes = attribs
		self.backdropdb = BackdropAutoDB(providers=self.providers)
		return Renderer.applySkin(self, desktop, parent)

	def changed(self, what):
		if not self.instance:
			return

		if what[0] == self.CHANGED_CLEAR:
			self.instance.hide()
			return

		servicetype = None
		try:
			service = None
			source_type = type(self.source)
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
				if self.nxts:
					service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
				else:
					self.canal[0] = None
					self.canal[1] = self.source.event.getBeginTime()
					event_name = self.source.event.getEventName().replace('\xc2\x86', '').replace('\xc2\x87', '')
					self.canal[2] = event_name
					self.canal[3] = self.source.event.getExtendedDescription()
					self.canal[4] = self.source.event.getShortDescription()
					self.canal[5] = event_name
				servicetype = "Event"

			if service is not None:
				service_str = service.toString()
				events = epgcache.lookupEvent(['IBDCTESX', (service_str, 0, -1, -1)])

				service_name = ServiceReference(service).getServiceName().replace('\xc2\x86', '').replace('\xc2\x87', '')
				self.canal[0] = service_name
				self.canal[1] = events[self.nxts][1]
				self.canal[2] = events[self.nxts][4]
				self.canal[3] = events[self.nxts][5]
				self.canal[4] = events[self.nxts][6]
				self.canal[5] = self.canal[2]

				if not autobouquet_file and service_name not in apdb:
					apdb[service_name] = service_str
		except Exception as e:
			logger.error(f"Error in service handling: {e}, Service: {service}, nxts: {self.nxts}, what: {what}")
			if self.instance:
				self.instance.hide()
			return

		if not servicetype:
			if self.instance:
				self.instance.hide()
			return

		try:
			logger.info(f"canal content: {self.canal}")
			logger.info(f"canal[1]: {self.canal[1]}, canal[2]: {self.canal[2]}, canal[5]: {self.canal[5]}")
			curCanal = "{}-{}".format(self.canal[1], self.canal[2])
			if curCanal == self.oldCanal and self.pstrNm and exists(self.pstrNm):
				logger.info(f"Backdrop already loaded: {self.pstrNm}")
				return

			if self.instance:
				self.instance.hide()

			self.oldCanal = curCanal
			self.pstcanal = clean_for_tvdb(self.canal[5])
			if self.pstcanal is not None:
				self.pstrNm = self.generateBackdropPath()  # join(self.path, str(self.pstcanal) + ".jpg")
				if self.pstrNm is not None:
					self.pstcanal = self.pstrNm

			if exists(self.pstcanal):
				utime(self.pstcanal, (time(), time()))
				self.timer.start(10, True)
			else:
				logger.warning(f"Error: Backdrop for event '{self.canal[2]}' not found. Queuing event.")
				canal = self.canal[:]
				pdb.put(canal)
				self.runBackdropThread()

		except Exception as e:
			logger.error(f"Error in backdrop display: {e}")
			if self.instance:
				self.instance.hide()
			return

	def generateBackdropPath(self):
		"""Generate backdrop path from current channel data, checking for multiple image extensions"""
		if isinstance(self.pstcanal, str) and self.pstcanal.strip():  # Ensure self.pstcanal is a valid string
			# Check if the Backdrop has already been loaded
			if hasattr(self, '_loaded_backdrops') and self.pstcanal in self._loaded_backdrops:
				logger.info(f"Backdrop already loaded: {self._loaded_backdrops[self.pstcanal]}")  # Log if Backdrop is already loaded
				return self._loaded_backdrops[self.pstcanal]  # Return the already loaded Backdrop path
			# Try to search for the Backdrop
			for ext in self.extensions:
				candidate = join(self.path, self.pstcanal + ext)
				logger.info(f"Checking Backdrop path: {candidate}")	 # Log the path being checked
				if exists(candidate):
					logger.info(f"Found Backdrop at: {candidate}")	# Log the found Backdrop path
					# Cache the found Backdrop path
					if not hasattr(self, '_loaded_backdrops'):
						self._loaded_backdrops = {}
					self._loaded_backdrops[self.pstcanal] = candidate  # Cache the loaded Backdrop path
					return candidate
			logger.info(f"Backdrop not found for {self.pstcanal}")
		else:
			logger.error(f"Invalid self.pstcanal value: {self.pstcanal}")
		return None

	# @lru_cache(maxsize=150)
	def checkBackdropExistence(self, backdrop_path):
		"""Check if backdrop file exists"""
		return exists(backdrop_path)

	def runBackdropThread(self):
		"""Start backdrop download thread"""
		Thread(target=self.waitBackdrop).start()

	def showBackdrop(self):
		"""Display the backdrop image"""
		if self.instance:
			self.instance.hide()
		if not self.pstrNm or not self.checkBackdropExistence(self.pstrNm):
			self.instance.hide()
			logger.info('showBackdrop ide instance')
			return

		# logger.info(f"[LOAD] Showing backdrop: {self.pstrNm}")
		self.instance.hide()
		self.instance.setPixmap(loadJPG(self.pstrNm))
		self.instance.setScale(1)
		self.instance.show()

	def waitBackdrop(self):
		"""Wait for backdrop download to complete"""
		if self.instance:
			self.instance.hide()
		self.pstrNm = self.generateBackdropPath()
		if not hasattr(self, 'pstrNm') or self.pstrNm is None:
			logger.info("Backdrop not found")
			return
		logger.info(f"Backdrop found: {self.pstrNm}")

		if not self.pstrNm:
			self._log_debug("[ERROR: waitBackdrop] Backdrop path is None")
			return

		loop = 180	# Maximum number of attempts
		found = False
		logger.info(f"[WAIT] Checking for backdrop: {self.pstrNm}")
		while loop > 0:
			if self.pstrNm and self.checkBackdropExistence(self.pstrNm):
				found = True
				break
			logger.info(f"[WAIT] Attempting to find Backdrop... (remaining tries: {loop})")	 # Add more logging
			sleep(0.5)
			loop -= 1

		if found:
			logger.info(f"Backdrop found: {self.pstrNm}")
			self.timer.start(10, True)
		else:
			logger.info("[ERROR] Backdrop not found after multiple attempts.")

	def _log_debug(self, message):
		"""Log debug message to file"""
		try:
			with open("/tmp/logBackdropX.log", "a") as w:
				w.write(f"{datetime.now()}: {message}\n")
		except Exception as e:
			logger.error(f"Logging error: {e}")

	def _log_error(self, message):
		"""Log error message to file"""
		try:
			with open("/tmp/agplog/AglareBackdropX_errors.log", "a") as f:
				f.write(f"{datetime.now()}: ERROR: {message}\n")
		except Exception as e:
			logger.error(f"Error logging error: {e}")


class BackdropDB(AgbDownloadThread):
	"""Handles backdrop downloading and database management"""
	def __init__(self, providers=None):
		super().__init__()
		self.logdbg = None
		self.pstcanal = None
		self.extensions = extensions
		self.service_pattern = compile(r'^#SERVICE (\d+):([^:]+:[^:]+:[^:]+:[^:]+:[^:]+:[^:]+)')
		default_providers = {
			"tmdb": True,
			"tvdb": False,
			"imdb": False,
			"fanart": False,
			"google": False
		}
		self.providers = {**default_providers, **(providers or {})}
		self.provider_engines = self.build_providers()

	def build_providers(self):
		"""Create the list of enabled provider engines"""
		engines = []
		if self.providers.get("tmdb"):
			engines.append(("TMDB", self.search_tmdb))
		if self.providers.get("tvdb"):
			engines.append(("TVDB", self.search_tvdb))
		if self.providers.get("fanart"):
			engines.append(("Fanart", self.search_fanart))
		if self.providers.get("imdb"):
			engines.append(("IMDB", self.search_imdb))
		if self.providers.get("google"):
			engines.append(("Google", self.search_google))
		return engines

	def run(self):
		"""Main processing loop"""
		while True:
			canal = pdb.get()
			self.process_canal(canal)
			pdb.task_done()

	def process_canal(self, canal):
		"""Process channel data and download backdrops"""
		try:
			self.pstcanal = clean_for_tvdb(canal[5])
			if not self.pstcanal:
				logger.info(f"Invalid channel name: {canal[0]}")
				return

			if not any(self.providers.values()):
				self._log_debug("No provider is enabled for backdrop download")
				return

			for ext in self.extensions:
				backdrop_path = join(BACKDROP_FOLDER, self.pstcanal + ext)
				if self.is_valid_backdrop(backdrop_path):
					utime(backdrop_path, (time(), time()))	# Update the timestamp to avoid re-downloading
					# self._log_debug(f"Backdrop already exists: {backdrop_path}")
					return

			for provider_name, provider_func in self.provider_engines:
				try:
					result = provider_func(backdrop_path, self.pstcanal, canal[4], canal[3], canal[0])
					if not result or len(result) != 2:
						continue

					success, log = result
					# self._log_debug(f"{provider_name}: {log}")	# fix: log anche se fallisce

					if success:
						break
				except Exception as e:
					self._log_error(f"Error with engine {provider_name}: {str(e)}")
					continue

		except Exception as e:
			self._log_error(f"Processing error: {e}")
			print_exc()

	def is_valid_backdrop(self, backdrop_path):
		"""Check if the backdrop file is valid (exists and has a valid size)"""
		return exists(backdrop_path) and getsize(backdrop_path) > 100

	def _log_debug(self, message):
		"""Log debug message to file"""
		try:
			with open("/tmp/BackdropDB.log", "a") as f:
				f.write(f"{datetime.now()}: {message}\n")
		except Exception as e:
			logger.error("logDB error:", str(e))

	def _log_error(self, message):
		"""Log error message to file"""
		try:
			with open("/tmp/agplog/BackdropDB_errors.log", "a") as f:
				f.write(f"{datetime.now()}: ERROR: {message}\n")
		except Exception as e:
			logger.error(f"Error logging error: {e}")


class BackdropAutoDB(AgbDownloadThread):

	def __init__(self, providers=None, max_backdrops=1000):
		super().__init__()
		self.pstcanal = None
		self.extensions = extensions
		self.service_queue = []
		self.last_scan = 0
		self.apdb = OrderedDict()
		self.max_retries = 3
		self.current_retry = 0
		default_providers = {
			"tmdb": True,
			"tvdb": False,
			"imdb": False,
			"fanart": False,
			"google": False
		}
		self.providers = {**default_providers, **(providers or {})}
		self.max_backdrops = max_backdrops
		self.backdrop_download_count = 0
		# Scheduled scan time (parsed from SCAN_TIME)
		try:
			hour, minute = map(int, SCAN_TIME.split(":"))
			self.scheduled_hour = hour
			self.scheduled_minute = minute
		except ValueError:
			self.scheduled_hour = 0
			self.scheduled_minute = 0

		self.last_scheduled_run = None

		# Logger initialization
		self.log_file = "/tmp/agplog/BackdropAutoDB.log"
		if not exists("/tmp/agplog"):
			makedirs("/tmp/agplog")
		self.clean_old_logs()
		self._log("=== INITIALIZATION COMPLETE ===")

	def run(self):
		"""Main loop - runs periodic full scans and processes services"""
		self._log("Renderer initialized - Starting main loop")

		while True:
			try:
				current_time = time()
				now = datetime.now()

				# Check if 2 hours passed since last scan
				do_time_scan = current_time - self.last_scan > 7200 or not self.last_scan

				# Check if it's the scheduled time and hasn't run yet today
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
		"""Perform complete service scan and populate the service queue"""
		self._log("Starting full service scan")
		self.service_queue = self._load_services()
		self._log(f"Scan completed, found {len(self.service_queue)} services")

	def _load_services(self):
		"""Load service references from Enigma2 bouquet files"""
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
		"""Validate if the given service reference is valid"""
		parts = sref.split(':')
		if len(parts) < 6:
			return False
		return parts[3:6] != ["0", "0", "0"]

	def is_valid_backdrop(self, backdrop_path):
		"""Check if the backdrop file is valid (exists and has a valid size)"""
		return exists(backdrop_path) and getsize(backdrop_path) > 100

	def _process_services(self):
		"""Process all loaded services and download their backdrops"""
		for service_ref in self.apdb.values():
			try:
				events = epgcache.lookupEvent(['IBDCTESX', (service_ref, 0, -1, 1440)])
				if not events:
					# self._log_debug(f"No EPG data for service: {service_ref}")
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
			self._log_error(f"Error preparing canal data: {str(e)}")
			return None

	def _download_backdrop(self, canal):
		"""Optimized backdrop downloader with fallback search providers and full error handling"""
		try:
			if self.backdrop_download_count >= self.max_backdrops:
				# self._log_debug("Backdrop download limit reached")
				return

			if not canal or len(canal) < 6:
				# self._log_debug("Invalid canal data")
				return

			if not any(self.providers.values()):
				self._log_debug("No provider is enabled for backdrop download")
				return

			event_name = str(canal[5]) if canal[5] else ""
			self.pstcanal = clean_for_tvdb(event_name) if event_name else None

			if not self.pstcanal:
				# self._log_debug(f"Invalid event name for: {canal[0]}")
				return

			# Log the generated URL for the backdrop for debugging
			# backdrop_url = f"http://image.tmdb.org/t/p/original/{self.pstcanal}.jpg"
			# self._log_debug(f"Generated URL for backdrop: {backdrop_url}")

			backdrop_path = None
			for ext in self.extensions:
				backdrop_path = join(BACKDROP_FOLDER, self.pstcanal + ext)
				if self.is_valid_backdrop(backdrop_path):
					utime(backdrop_path, (time(), time()))	# Update the timestamp to avoid re-downloading
					# self._log_debug(f"Backdrop already exists: {backdrop_path}")
					return

			# Create the list of providers enabled for download
			providers = []

			if self.providers["tmdb"]:
				providers.append(("TMDB", self.search_tmdb))
			if self.providers["tvdb"]:
				providers.append(("TVDB", self.search_tvdb))
			if self.providers["fanart"]:
				providers.append(("Fanart", self.search_fanart))
			if self.providers["imdb"]:
				providers.append(("IMDB", self.search_imdb))
			if self.providers["google"]:
				providers.append(("Google", self.search_google))

			downloaded = False
			# Cycle through providers to find the backdrop
			for provider_name, provider_func in providers:
				try:
					result = provider_func(backdrop_path, self.pstcanal, canal[4], canal[3], canal[0])
					if not result or len(result) != 2:
						continue

					success, log = result
					if success and log and "SUCCESS" in str(log).upper():
						if not exists(backdrop_path):
							self.backdrop_download_count += 1
							self._log(f"Backdrop downloaded from {provider_name}: {self.pstcanal}")
						downloaded = True
						break
				except Exception as e:
					self._log_error(f"Error with {provider_name}: {str(e)}")

			if not downloaded:
				self._log_debug(f"Backdrop download failed for: {self.pstcanal}")

		except Exception as e:
			self._log_error(f"CRITICAL ERROR in _download_backdrop: {str(e)}")
			print_exc()

	def clean_old_logs(self):
		"""Delete log file if older than 30 days or larger than 5MB"""
		try:
			if exists(self.log_file):
				# Delete if older than 30 days
				if time() - getmtime(self.log_file) > 2592000:
					remove(self.log_file)
					return

				# Delete if larger than 5 MB
				if getsize(self.log_file) > 5 * 1024 * 1024:
					remove(self.log_file)
		except Exception as e:
			logger.error(f"Log cleanup error: {str(e)}")

	def _log(self, message):
		self._write_log("INFO", message)

	def _log_debug(self, message):
		self._write_log("DEBUG", message)

	def _log_error(self, message):
		self._write_log("ERROR", message)

	def _write_log(self, level, message):
		"""Central log writer"""
		try:
			with open(self.log_file, 'a') as f:
				f.write(f"[{datetime.now()}] {level}: {message}\n")
		except Exception as e:
			logger.error(f"Log write error: {str(e)}")


def SearchBouquetTerrestrial():
	fallback = "/etc/enigma2/userbouquet.favourites.tv"
	for f in sorted(glob("/etc/enigma2/*.tv")):
		try:
			with open(f, "r") as file:
				content = file.read().lower()
				if "eeee" in content and not any(x in content for x in ["82000", "c0000"]):
					return f
		except:
			continue
	return fallback


def process_autobouquet(max_channels=1000, allowed_types=None):
	"""
	Process ALL TV bouquets extracting unique services, including the bouquets.tv file.

	Args:
		max_channels (int): Maximum number of channels to process
		allowed_types (list): Filter by service type (e.g. ['1:0:1', '1:0:2'])
	"""
	if allowed_types is None:
		allowed_types = ['1:0:1', '1:0:2', '1:0:16', '1:0:18', '1:0:19', '4097', '5002', '5001', '8193']

	service_pattern = compile(r'^#SERVICE (\d+):([^:]+:[^:]+:[^:]+:[^:]+:[^:]+:[^:]+)')
	unique_refs = OrderedDict()

	bouquets = ["/etc/enigma2/bouquets.tv"]
	if exists(bouquets[0]):
		try:
			with open(bouquets[0], 'r', encoding='utf-8', errors='ignore') as f:
				for line in f:
					if len(unique_refs) >= max_channels:
						return list(unique_refs.keys())
					if line.startswith("#SERVICE") and "FROM BOUQUET" not in line:
						match = service_pattern.match(line.strip())
						if match:
							service_type, sref = match.groups()
							if any(sref.startswith(t) for t in allowed_types):
								normalized_ref = f"{service_type}:{sref.split(':')[0]}"
								unique_refs[normalized_ref] = None
		except Exception as e:
			logger.error(f"Error processing bouquets.tv: {e}")

	for bouquet_file in glob("/etc/enigma2/*.tv"):
		try:
			with open(bouquet_file, 'r', encoding='utf-8', errors='ignore') as f:
				for line in f:
					if len(unique_refs) >= max_channels:
						return list(unique_refs.keys())
					match = service_pattern.match(line.strip())
					if match:
						service_type, sref = match.groups()
						if any(sref.startswith(t) for t in allowed_types):
							normalized_ref = f"{service_type}:{sref.split(':')[0]}"
							unique_refs[normalized_ref] = None
		except Exception as e:
			logger.error(f"Error processing {bouquet_file}: {e}")
			continue

	return list(unique_refs.keys())


autobouquet_file = SearchBouquetTerrestrial()
apdb = process_autobouquet()

threadDB = BackdropDB()
threadDB.start()

threadAutoDB = BackdropAutoDB()
threadAutoDB.start()
