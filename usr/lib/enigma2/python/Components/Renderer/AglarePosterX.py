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
from datetime import datetime
from glob import glob
from os import remove, utime, makedirs
from os.path import join, exists, getmtime
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
from Components.Renderer.AgpDownloadThread import AgpDownloadThread
from .Agp_Utils import POSTER_FOLDER, clean_for_tvdb  # , noposter

# Constants and global variables
epgcache = eEPGCache.getInstance()
epgcache.load()
pdb = LifoQueue()
rw_mounts = ["/media/usb", "/media/hdd", "/media/mmc", "/media/sd"]
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
	Main poster renderer class for Enigma2
	Handles poster display and refresh logic
	"""
	GUI_WIDGET = ePixmap

	def __init__(self):
		super().__init__()
		self.nxts = 0
		self.path = POSTER_FOLDER
		self.canal = [None] * 6
		self.pstrNm = None
		self.oldCanal = None
		self.logdbg = None
		self.pstcanal = None
		self.timer = eTimer()
		self.timer.callback.append(self.showPoster)
		self.max_channels = 200  # You can adjust this as needed
		self.current_channels = 0  # Track number of channels processed

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
		self.posterdb = PosterAutoDB(providers=self.providers)
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

				"""
				# global autobouquet_file
				if not globals().get('autobouquet_file') and service_name not in apdb:
					apdb[service_name] = service_str
				# if not getattr(modules[__name__], 'autobouquet_file', False) and service_name not in apdb:
					# apdb[service_name] = service_str
				"""
				if not autobouquet_file and service_name not in apdb:
					apdb[service_name] = service_str

		except Exception as e:
			print(f"Error in service handling: {e}")
			if self.instance:
				self.instance.hide()
			return

		if not servicetype:
			if self.instance:
				self.instance.hide()
			return

		try:
			curCanal = "{}-{}".format(self.canal[1], self.canal[2])
			if curCanal == self.oldCanal:
				return

			self.oldCanal = curCanal
			self.pstcanal = clean_for_tvdb(self.canal[5])
			if self.pstcanal is not None:
				self.pstrNm = join(self.path, str(self.pstcanal) + ".jpg")
				self.pstcanal = self.pstrNm

			if exists(self.pstcanal):
				self.timer.start(10, True)
			else:
				canal = self.canal[:]
				pdb.put(canal)
				self.runPosterThread()

		except Exception as e:
			print(f"Error in poster display: {e}")
			if self.instance:
				self.instance.hide()
			return

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
			self.instance.hide()
		self.pstrNm = self.generatePosterPath()
		if self.pstrNm and self.checkPosterExistence(self.pstrNm):
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

		if self.instance:
			self.instance.hide()

		if not self.pstrNm:
			self.logPoster("[ERROR: waitPoster] Poster path is None")
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
			with open("/tmp/agplog/AglarePosterX.log", "a") as f:
				f.write(f"{datetime.now()}: {message}\n")
		except Exception as e:
			print(f"Logging error: {e}")

	def _log_error(self, message):
		"""Log error message to file"""
		try:
			with open("/tmp/agplog/AglarePosterX_errors.log", "a") as f:
				f.write(f"{datetime.now()}: ERROR: {message}\n")
		except Exception as e:
			print(f"Error logging error: {e}")


class PosterDB(AgpDownloadThread):
	"""Handles poster downloading and database management"""
	def __init__(self):
		super().__init__()
		self.logdbg = None
		self.pstcanal = None
		self.service_pattern = compile(r'^#SERVICE (\d+):([^:]+:[^:]+:[^:]+:[^:]+:[^:]+:[^:]+)')

	def run(self):
		"""Main processing loop"""
		while True:
			canal = pdb.get()
			self.process_canal(canal)
			pdb.task_done()

	def process_canal(self, canal):
		"""Process channel data and download posters"""
		try:
			self.pstcanal = clean_for_tvdb(canal[5])
			if not self.pstcanal:
				print(f"Invalid channel name: {canal[0]}")
				return

			dwn_poster = join(POSTER_FOLDER, f"{self.pstcanal}.jpg")

			if exists(dwn_poster):
				utime(dwn_poster, (time(), time()))
				return

			search_engines = [
				self.search_tmdb,
				self.search_tvdb,
				self.search_fanart,
				self.search_imdb,
				self.search_google
			]

			for engine in search_engines:
				success, log = engine(dwn_poster, self.pstcanal, canal[4], canal[3], canal[0])
				self._log_debug(log)
				if success:
					break

		except Exception as e:
			self._log_error(f"Processing error: {e}")
			print_exc()

	def _log_debug(self, message):
		"""Log debug message to file"""
		try:
			with open("/tmp/agplog/PosterDB.log", "a") as f:
				f.write(f"{datetime.now()}: {message}\n")
		except Exception as e:
			print(f"Logging error: {e}")

	def _log_error(self, message):
		"""Log error message to file"""
		try:
			with open("/tmp/agplog/PosterDB_errors.log", "a") as f:
				f.write(f"{datetime.now()}: ERROR: {message}\n")
		except Exception as e:
			print(f"Error logging error: {e}")


class PosterAutoDB(AgpDownloadThread):

	def __init__(self, providers=None, max_posters=2000):
		super().__init__()
		self.pstcanal = None
		self.service_queue = []
		self.last_scan = 0
		self.apdb = OrderedDict()
		self.max_retries = 3
		self.current_retry = 0
		self.providers = providers or {
			"tmdb": True,
			"tvdb": False,
			"imdb": False,
			"fanart": False,
			"google": False
		}
		self.max_posters = max_posters
		self.poster_download_count = 0
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
		self.log_file = "/tmp/agplog/PosterAutoDB.log"
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

	def _process_services(self):
		"""Process all loaded services and download their posters"""
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
			self._log_error(f"Error preparing canal data: {str(e)}")
			return None

	def _download_poster(self, canal):
		"""Optimized poster downloader with fallback search providers and full error handling"""
		try:
			if self.poster_download_count >= self.max_posters:
				# self._log_debug("Poster download limit reached")
				return

			if not canal or len(canal) < 6:
				self._log_debug("Invalid canal data")
				return

			if not any(self.providers.values()):
				self._log_debug("No provider is enabled for poster download")
				return

			event_name = str(canal[5]) if canal[5] else ""
			self.pstcanal = clean_for_tvdb(event_name) if event_name else None

			if not self.pstcanal:
				self._log_debug(f"Invalid event name for: {canal[0]}")
				return

			# Log the generated URL for the poster for debugging
			# poster_url = f"http://image.tmdb.org/t/p/original/{self.pstcanal}.jpg"
			# self._log_debug(f"Generated URL for poster: {poster_url}")

			for ext in [".jpg", ".jpeg", ".png"]:
				poster_path = join(POSTER_FOLDER, self.pstcanal + ext)
				if exists(poster_path):
					utime(poster_path, (time(), time()))  # Update the poster's timestamp
					self._log(f"Poster already exists with extension {ext}, timestamp updated: {self.pstcanal}")
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
			# Cycle through providers to find the poster
			for provider_name, provider_func in providers:
				try:
					result = provider_func(poster_path, self.pstcanal, canal[4], canal[3], canal[0])
					if not result or len(result) != 2:
						continue

					success, log = result
					if success and log and "SUCCESS" in str(log).upper():
						self.poster_download_count += 1
						self._log(f"Poster downloaded from {provider_name}: {self.pstcanal}")
						downloaded = True
						break
				except Exception as e:
					self._log_error(f"Error with {provider_name}: {str(e)}")

			if not downloaded:
				self._log_debug(f"Poster download failed for: {self.pstcanal}")

		except Exception as e:
			self._log_error(f"CRITICAL ERROR in _download_poster: {str(e)}")
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
			print(f"Log cleanup error: {str(e)}")

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
			print(f"Log write error: {str(e)}")


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


def process_autobouquet(max_channels=2000, allowed_types=None):
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
			print(f"Error processing bouquets.tv: {e}")

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
			print(f"Error processing {bouquet_file}: {e}")
			continue

	return list(unique_refs.keys())


autobouquet_file = SearchBouquetTerrestrial()
apdb = process_autobouquet()

threadDB = PosterDB()
threadDB.start()

threadAutoDB = PosterAutoDB()
threadAutoDB.start()
