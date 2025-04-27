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
from Components.Sources.CurrentService import CurrentService
from Components.Sources.ServiceEvent import ServiceEvent
from ServiceReference import ServiceReference
import NavigationInstance

# Local imports
from Components.Renderer.AgpDownloadThread import AgpDownloadThread
from Plugins.Extensions.Aglare.plugin import ApiKeyManager
from .Agp_Utils import (
    POSTER_FOLDER,
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

        # Initialize default providers configuration
        self.providers = api_key_manager.get_active_providers()

        clear_all_log()

        self.queued_posters = set()
        self.loaded_posters = set()
        self.poster_cache = {}
        if len(self.poster_cache) > 50:
            self.poster_cache.clear()

        self.show_timer = eTimer()
        self.show_timer.callback.append(self.showPoster)

        # Initialize helper classes with providers config
        self.poster_db = PosterDB(providers=self.providers)
        self.poster_auto_db = PosterAutoDB(providers=self.providers)

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
        """Handle screen/channel changes and update poster"""
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

            if self.pstcanal in self.poster_cache:
                cached_path = self.poster_cache[self.pstcanal]
                if checkPosterExistence(cached_path):
                    self.showPoster(cached_path)
                    return

            # Try to display existing poster
            poster_path = join(self.path, f"{self.pstcanal}.jpg")

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
        # Thread(target=self.waitPoster).start()
        Thread(target=self.waitPoster, daemon=True).start()

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

    # def showPoster(self, poster_path=None):
        # """Safe poster display with retry logic"""
        # if not self.instance:
            # return

        # try:
            # path = poster_path or self.backrNm
            # if not path:
                # self.instance.hide()
                # return

            # if not self.check_valid_poster(path):
                # # logger.warning(f"Invalid poster file: {path}")
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
                        # # logger.debug(f"Displayed poster: {path}")
                        # return
                    # else:
                        # logger.warning(f"Failed to load pixmap (attempt {attempt + 1})")
                        # sleep(0.1 * (attempt + 1))
                # except Exception as e:
                    # logger.error(f"Pixmap error (attempt {attempt + 1}): {str(e)}")
                    # sleep(0.1 * (attempt + 1))

            # self.instance.hide()

        # except Exception as e:
            # logger.error(f"Error in showPoster: {str(e)}")
            # self.instance.hide()

    def waitPoster(self):
        """Wait for Poster download to complete with retries"""
        if not self.instance or not self.canal[5]:
            return

        self.backrNm = None
        pstcanal = clean_for_tvdb(self.canal[5])
        poster_path = join(self.path, f"{pstcanal}.jpg")

        for attempt in range(5):
            if checkPosterExistence(poster_path):
                self.backrNm = poster_path
                logger.debug(f"Poster found after {attempt} attempts")
                self.showPoster(poster_path)
                return

            sleep(0.3 * (attempt + 1))
        # logger.warning(f"Poster not found after retries: {poster_path}")

    def check_valid_poster(self, path):
        """Verify Poster is valid JPEG and >1KB"""
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
    """Handles Poster downloading and database management"""
    def __init__(self, providers=None):
        super().__init__()

        self.queued_posters = set()
        self.poster_cache = {}

        self.executor = ThreadPoolExecutor(max_workers=4)
        self.extensions = extensions
        self.logdbg = None
        self.pstcanal = None
        self.service_pattern = compile(r'^#SERVICE (\d+):([^:]+:[^:]+:[^:]+:[^:]+:[^:]+:[^:]+)')

        self.log_file = "/tmp/agplog/PosterDB.log"
        if not exists("/tmp/agplog"):
            makedirs("/tmp/agplog")

        self.providers = api_key_manager.get_active_providers()
        self.provider_engines = self.build_providers()

    def build_providers(self):
        """Initialize enabled provider search engines"""
        provider_mapping = {
            'tmdb': self.search_tmdb,
            'fanart': self.search_fanart,
            'thetvdb': self.search_tvdb,
            'elcinema': self.search_elcinema,   # no apikey
            'google': self.search_google,   # no apikey
            'omdb': self.search_omdb,
            'imdb': self.search_imdb,   # no apikey
            'programmetv': self.search_programmetv_google,  # no apikey
            'molotov': self.search_molotov_google  # no apikey
        }
        return [(name, func) for name, func in provider_mapping.items()
                if self.providers.get(name, False)]

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
        """Download and process poster for a single channel"""
        try:
            self.pstcanal = clean_for_tvdb(canal[5])
            if not self.pstcanal:
                logger.error(f"Invalid channel: {canal[0]}")
                return

            poster_path = join(POSTER_FOLDER, f"{self.pstcanal}.jpg")

            # Check if already in the queue
            """
            # if self.pstcanal in self.queued_posters:
                # logger.debug(f"Poster already queued: {self.pstcanal}")
                # return
            """
            # Add to queue and process
            with Lock():
                self.queued_posters.add(self.pstcanal)

            try:
                # Check if a valid file already exists
                if self.check_valid_poster(poster_path):
                    # logger.debug(f"Valid existing poster: {poster_path}")
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

                        # Call the provider function to download the poster
                        result = provider_func(
                            dwn_poster=poster_path,
                            title=self.pstcanal,
                            shortdesc=canal[4],
                            fulldesc=canal[3],
                            channel=canal[0],
                            api_key=api_key
                        )
                        if result and self.check_valid_poster(poster_path):
                            logger.info(f"Download successful with {provider_name}")
                            break

                    except Exception as e:
                        logger.error(f"Error from {provider_name}: {str(e)}")
                        continue

            finally:
                # Remove the channel from the queue after processing
                with Lock():
                    self.queued_posters.discard(self.pstcanal)

        except Exception as e:
            logger.error(f"Critical error in _process_canal_task: {str(e)}")
            logger.error(format_exc())

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

    def update_poster_cache(self, poster_name, path):
        """Force update cache entry"""
        self.poster_cache[poster_name] = path
        # Limit cache size
        if len(self.poster_cache) > 50:
            oldest = next(iter(self.poster_cache))
            del self.poster_cache[oldest]

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
    - providers: Configured via plugin setup parameters
    """
    _instance = None

    def __init__(self, providers=None, max_posters=2000):
        """Initialize the poster downloader with provider configurations"""
        if hasattr(self, '_initialized') and self._initialized:
            return

        super().__init__()
        self._initialized = True

        if not config.plugins.Aglare.pstdown.value:
            logger.debug("PosterAutoDB: Automatic downloads DISABLED in configuration")
            self.active = False
            return

        logger.debug("PosterAutoDB: Automatic downloads ENABLED in configuration")
        self.active = True
        if not any(api_key_manager.get_active_providers().values()):
            logger.debug("Disabled - no active provider")
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
        self.max_poster_age = 30
        self.poster_folder = self._init_poster_folder()
        self.max_posters = max_posters

        self.processed_titles = OrderedDict()  # Tracks processed shows
        self.poster_download_count = 0
        self.provider_engines = self.build_providers()

        try:
            # Get scan time from config instead of global
            scan_time = config.plugins.Aglare.pscan_time.value
            hour, minute = map(int, scan_time.split(":"))
            self.scheduled_hour = hour
            self.scheduled_minute = minute
        except Exception as e:
            logger.error(f"Error parsing scan time: {str(e)}")
            self.scheduled_hour = 0  # Default to midnight
            self.scheduled_minute = 0

        self.last_scheduled_run = None

        self.log_file = "/tmp/agplog/PosterAutoDB.log"
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
            'tmdb': self.search_tmdb,
            'fanart': self.search_fanart,
            'thetvdb': self.search_tvdb,
            'elcinema': self.search_elcinema,   # no apikey
            'google': self.search_google,   # no apikey
            'omdb': self.search_omdb,
            'imdb': self.search_imdb,   # no apikey
            'programmetv': self.search_programmetv_google,  # no apikey
            'molotov': self.search_molotov_google,  # no apikey
        }
        return [(name, func) for name, func in provider_mapping.items()
                if self.providers.get(name, False)]

    def run(self):
        """Main execution loop - handles scheduled operations"""
        self._log("Renderer initialized - Starting main loop")

        if not hasattr(self, 'active') or not self.active:
            logger.debug("PosterAutoDB thread terminated - disabled in configuration")
            return

        if not config.plugins.Aglare.pstdown:
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

        if self.poster_download_count >= self.max_posters:
            return False

        if not self._check_storage():
            self._log("Download skipped due to insufficient storage")
            return False

        if not check_disk_space(POSTER_FOLDER, 10):
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

            poster_path = join(POSTER_FOLDER, f"{self.pstcanal}.jpg")
            result = provider_func(
                dwn_poster=poster_path,
                title=self.pstcanal,
                shortdesc=canal[4],
                fulldesc=canal[3],
                channel=canal[0],
                api_key=api_key
            )
            if result and self._validate_download(poster_path):
                logger.info(f"Download successful with {provider_name}")
                return True

        except Exception as e:
            logger.error(f"Error with {provider_name}: {str(e)}")

        return False

    def _validate_download(self, poster_path):
        """Verify the integrity of the downloaded file"""
        if checkPosterExistence(poster_path) and getsize(poster_path) > 1024:
            self.poster_download_count += 1
            return True
        return False

    def _init_poster_folder(self):
        """Initialize the folder with validation"""
        try:
            return validate_media_path(
                POSTER_FOLDER,
                media_type="posters",
                min_space_mb=self.min_disk_space
            )
        except Exception as e:
            self._log_error(f"Poster folder init failed: {str(e)}")
            return "/tmp/posters"

    def _check_storage(self):
        """Version optimized using utilities"""
        try:
            if check_disk_space(self.poster_folder, self.min_disk_space):
                return True

            self._log("Low disk space detected, running cleanup...")
            delete_old_files_if_low_disk_space(
                self.poster_folder,
                min_free_space_mb=self.min_disk_space,
                max_age_days=self.max_poster_age
            )

            return check_disk_space(self.poster_folder, self.min_disk_space)

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


# Create an API Key Manager instance
api_key_manager = ApiKeyManager()

# download on requests
if any(api_key_manager.get_active_providers().values()):
    logger.debug("Starting PosterDB with active providers")
    AgpDB = PosterDB()
    AgpDB.daemon = True
    AgpDB.start()
else:
    logger.debug("PosterDB not started - no active providers")

# automatic download
if config.plugins.Aglare.pstdown.value:
    logger.debug("Checking PosterAutoDB startup...")
    # Get active providers from the central manager
    active_providers = api_key_manager.get_active_providers()

    if any(active_providers.values()):
        logger.debug("VALID configuration - at least one provider is active")
        AgpAutoDB = PosterAutoDB()

        if AgpAutoDB.active:
            AgpAutoDB.daemon = True
            AgpAutoDB.start()
            logger.debug("PosterAutoDB SUCCESSFULLY STARTED")
        else:
            logger.debug("PosterAutoDB internally disabled")
            AgpAutoDB = type('DisabledPosterAutoDB', (), {'start': lambda self: None})()
    else:
        logger.debug("INVALID configuration - no active providers")
        AgpAutoDB = type('DisabledPosterAutoDB', (), {'start': lambda self: None})()
else:
    logger.debug("PosterAutoDB NOT started - downloads disabled in configuration")
    AgpAutoDB = type('DisabledPosterAutoDB', (), {'start': lambda self: None})()
