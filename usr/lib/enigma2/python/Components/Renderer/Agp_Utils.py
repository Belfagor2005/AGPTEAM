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

# ========================
# SYSTEM IMPORTS
# ========================
# import platform      # Info sistema operativo
from sys import version_info, version, stdout
from os import (
	makedirs,
	statvfs,
	listdir,
	remove,
	access,
	W_OK,
	system
)
from os.path import (  # Utilities path
	join,
	exists,
	isfile,
	dirname,
	getsize,
	getmtime,
	basename,

)

import glob              # Search file pattern

# ========================
# IMPORTS FOR LOGGING
# ========================

from logging import (
	getLogger,
	DEBUG,
	INFO,
	Formatter,
	StreamHandler,
	# Handler,
	# FileHandler
)
from logging.handlers import RotatingFileHandler

# ========================
# IMPORTS FOR TIME/DATE
# ========================
from time import ctime
from datetime import datetime, timedelta
import time
from enigma import Timer
# ========================
# IMPORTS FOR WORD PROCESSING
# ========================
import unicodedata      # Gestione caratteri Unicode
from re import sub, IGNORECASE  # Regular expressions

# ========================
# ENIGMA SPECIFIC IMPORTS
# ========================
from Components.config import config  # Configurazione Enigma2


# Custom import for renderer
PY3 = version_info[0] >= 3


# Initialize logging
class ColorLogger:
	"""Enhanced logger with colored output for better visibility"""
	COLORS = {
		'DEBUG': '\033[94m',     # Blue
		'INFO': '\033[92m',      # Green
		'WARNING': '\033[93m',   # Yellow
		'ERROR': '\033[91m',     # Red
		'CRITICAL': '\033[91m',  # Red
		'RESET': '\033[0m'       # Reset
	}

	@classmethod
	def log(cls, level, message):
		color = cls.COLORS.get(level, '')
		print(f"{color}[{level}] {message}{cls.COLORS['RESET']}")


# Initialize enhanced logger
def setup_logging(log_file='/tmp/agplog/agp_utils.log', max_log_size=5, backup_count=3):
	"""
	Configure comprehensive logging for AGP application with:
	- Console output with colors
	- Rotating file handler
	- Error handling
	- System information

	Args:
		log_file (str): Path to log file
		max_log_size (int): Max log size in MB
		backup_count (int): Number of backup logs to keep
	"""

	class ColoredFormatter(Formatter):
		"""Custom formatter with colored output"""
		COLORS = {
			'DEBUG': '\033[36m',     # Cyan
			'INFO': '\033[32m',      # Green
			'WARNING': '\033[33m',   # Yellow
			'ERROR': '\033[31m',     # Red
			'CRITICAL': '\033[41m',  # Red background
			'RESET': '\033[0m'       # Reset
		}

		def format(self, record):
			levelname = record.levelname
			if levelname in self.COLORS:
				record.levelname = (f"{self.COLORS[levelname]}{levelname}"
									f"{self.COLORS['RESET']}")
			return super().format(record)

	# Create main logger
	logger = getLogger('AGP')
	logger.setLevel(DEBUG)

	# Clear existing handlers to avoid duplication
	for handler in logger.handlers[:]:
		logger.removeHandler(handler)

	try:
		# Console handler with colors
		console_handler = StreamHandler(stdout)
		console_handler.setFormatter(ColoredFormatter(
			'%(levelname)s: %(message)s'
		))
		console_handler.setLevel(INFO)
		logger.addHandler(console_handler)

		# File handler with rotation
		makedirs(dirname(log_file), exist_ok=True)
		file_handler = RotatingFileHandler(
			log_file,
			maxBytes=max_log_size * 1024 * 1024,
			backupCount=backup_count,
			encoding='utf-8'
		)
		file_handler.setFormatter(Formatter(
			'%(asctime)s [%(process)d] %(name)s %(levelname)s: %(message)s',
			datefmt='%Y-%m-%d %H:%M:%S'
		))
		file_handler.setLevel(DEBUG)
		logger.addHandler(file_handler)

		# Log system info at startup
		logger.info("=" * 50)
		logger.info(f"AGP Logger initialized (Python {version.split()[0]}")
		# logger.info(f"System: {platform.system()} {platform.release()}")
		logger.info(f"Log file: {log_file} (Max {max_log_size}MB)")
		logger.info("=" * 50)

	except Exception as e:
		print(f"Failed to configure logging: {str(e)}")
		raise

	return logger


""" cleanup_old_logs('/tmp/agplog/agp_utils.log', max_days=7) """


def cleanup_old_logs(log_file, max_days=7):
	"""Delete log files older than max_days"""
	cutoff = datetime.now() - timedelta(days=max_days)

	for f in glob.glob(f"{log_file}*"):  # Also captures rotated files (e.g. agp_utils.log.1)
		if isfile(f):
			file_time = datetime.fromtimestamp(getmtime(f))
			if file_time < cutoff:
				try:
					remove(f)
				except Exception as e:
					print(f"Errore cancellazione {f}: {str(e)}")


def schedule_log_cleanup(interval_hours=12):
	"""Auto-schedule log cleanup every X hours"""
	def wrapper():
		cleanup_old_logs('/tmp/agp/agp_utils.log')
		Timer(interval_hours * 3600, wrapper).start()

	wrapper()


schedule_log_cleanup()
# interval_hours            Total Seconds       Equivalent
#    1 (hour)                    3.600               1h
#    12 (hours)                 43.200               12h
#    24 (hours)                 86.400              1 Day
#    72 (hours)                 259.200             3 Days

logger = setup_logging()
logger.info("AGP MediaUtils initialized")


# Initialize text converter debug mode
# convtext.DEBUG = False  # Set to True for debugging

# ================ END LOGGING CONFIGURATION ===============

# ================ START GUI CONFIGURATION ===============

# Initialize skin paths


# cur_skin = config.skin.primary_skin.value.replace('/skin.xml', '')
cur_skin = join(config.skin.primary_skin.value, "skin.xml").replace('/skin.xml', '')
noposter = join("/usr/share/enigma2", cur_skin, "noposter.jpg")
nobackdrop = join("/usr/share/enigma2", cur_skin, "nobackdrop.png")

# Active services configuration
ACTIVE_SERVICES = [
	'_search_tmdb',  # Main service
	'_search_tvdb',
	'_search_omdb'
]

lng = "en"
try:
	lng = config.osd.language.value[:-3]
except:
	lng = "en"


# ========================
# BACKDROP CONFIGURATION (shared)
# ========================
BACKDROP_SIZES = [
	"original",  # Highest quality
	"w1920",     # Full HD
	"w1280",     # HD ready
	"w780",      # Default recommendation
	"w500",      # Fallback
	"w300"       # Low bandwidth
]

MIN_BACKDROP_WIDTH = 500  # px
MAX_ORIGINAL_SIZE = 10    # MB


def verify_backdrop_integrity(self):
	"""Verifica che la cartella e la cache siano sincronizzate"""
	missing_files = 0

	# Controlla ogni entry nella cache
	for title, entry in list(self.cache.cache.items()):
		if not exists(entry['path']):
			logger.warning(f"Missing file: {entry['path']}")
			del self.cache.cache[title]
			missing_files += 1

	if missing_files:
		logger.info(f"Cleaned {missing_files} invalid cache entries")
		self.cache._async_save()  # Salva le modifiche
# validate_backdrop_folder()

# ================ END GUI CONFIGURATION ===============


# ================ START TEXT MANAGER ===============

try:
	from .Agp_lib import convtext
except ImportError:
	logger.warning("convtext not found, using fallback")

	def convtext(x):
		return x  # Fallback function


def clean_epg_text(text):
	"""Centralized text cleaning for both classes"""
	if not text:
		return ""
	text = str(text).replace('\xc2\x86', '').replace('\xc2\x87', '')
	return text.encode('utf-8', 'ignore') if not PY3 else text


# filename cleaner

def clean_filename(title):
	"""Sanitize title for use as filename (handles special chars and accents)"""
	if not title:
		return "no_title"

	# Handle unicode conversion for Python 2/3
	if version_info[0] == 2:
		if isinstance(title, str):
			title = title.decode('utf-8', 'ignore')
	else:
		if isinstance(title, bytes):
			title = title.decode('utf-8', 'ignore')

	# Convert to ASCII (remove accents)
	title = unicodedata.normalize('NFKD', title)
	title = title.encode('ascii', 'ignore').decode('ascii')

	# Remove special characters and normalize
	title = sub(r'[^\w\s-]', '_', title)  # Sostituisce caratteri speciali con _
	title = sub(r'[\s-]+', '_', title)    # Sostituisce spazi e - con _
	title = sub(r'_+', '_', title)        # Riduce multipli _ a uno solo
	title = title.strip('_')              # Rimuove _ all'inizio/fine

	return title.lower()[:100]  # Limita a 100 caratteri


def clean_for_tvdb_optimized(title):
	"""Optimized version for fast title cleaning"""
	if not title:
		return ""

	# Convert to ASCII (remove accents)
	title = unicodedata.normalize('NFKD', title)
	title = title.encode('ascii', 'ignore').decode('ascii')

	# Remove common articles from start/end
	title = sub(r'^(il|lo|la|i|gli|le|un|uno|una|a|an)\s+', '', title, flags=IGNORECASE)
	title = sub(r'\s+(il|lo|la|i|gli|le|un|uno|una|a|an)$', '', title, flags=IGNORECASE)

	# Remove common patterns (years, quality indicators, etc.)
	patterns = [
		r'\([0-9]{4}\)', r'\[.*?\]', r'\bHD\b', r'\b4K\b',
		r'\bS\d+E\d+\b', r'\b\(\d+\)', r'\bodc\.\s?\d+\b',
		r'\bep\.\s?\d+\b', r'\bparte\s?\d+\b'
	]
	for pattern in patterns:
		title = sub(pattern, '', title, flags=IGNORECASE)

	# Final cleanup
	title = sub(r'[^\w\s]', ' ', title)
	title = sub(r'\s+', ' ', title).strip().lower()

	return title

# Uso in `_fill_from_event` o `_fill_from_service`
# normalized_name = clean_for_tvdb_optimized(event_name)


def clean_for_tvdb(title):
	"""Prepare title for API searches"""
	if not title:
		return ""

	# Convert to ASCII (remove accents)
	title = unicodedata.normalize('NFKD', title)
	title = title.encode('ascii', 'ignore').decode('ascii')

	# Remove common patterns (years, quality indicators, etc.)
	patterns = [
		r'\([0-9]{4}\)', r'\[.*?\]', r'\bHD\b', r'\b4K\b',
		r'\bS\d+E\d+\b', r'\b\(\d+\)', r'\bodc\.\s?\d+\b',
		r'\bep\.\s?\d+\b', r'\bparte\s?\d+\b'
	]
	for pattern in patterns:
		title = sub(pattern, '', title, flags=IGNORECASE)

	# Final cleanup before returning
	title = sub(r'[^\w\s]', ' ', title)
	title = sub(r'\s+', ' ', title).strip().lower()

	return convtext(title)


# ================ END TEXT MANAGER ===============


# ================ START MEDIASTORAGE CONFIGURATION ===============


def check_disk_space(path, min_space_mb, media_type=None, purge_strategy="oldest_first"):
	"""
	Advanced version with automatic purge
	Args:
		purge_strategy: "oldest_first" o "largest_first"
	"""
	try:
		# Fallback a /tmp if the path does not exist
		if not exists(path):
			path = "/tmp"

		# Calculate available space
		stat = statvfs(path)
		free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)

		if free_mb >= min_space_mb:
			return True

		logger.warning(f"Low space in {path}: {free_mb:.1f}MB < {min_space_mb}MB")

		# If media_type is specified, activate purge
		if media_type:
			return free_up_space(
				path=path,
				min_space_mb=min_space_mb,
				media_type=media_type,
				strategy=purge_strategy
			)
		return False

	except Exception as e:
		logger.error(f"Space check failed: {str(e)}")
		return False


def free_up_space(path, min_space_mb, media_type, strategy="oldest_first"):
	"""
	Differentiated purging by media type
	"""
	try:
		# 1. File collection with metadata
		files = []
		for f in listdir(path):
			filepath = join(path, f)
			if isfile(filepath):
				files.append({
					"path": filepath,
					"size": getsize(filepath),
					"mtime": getmtime(filepath)
				})

		# 2. Sorting by strategy
		if strategy == "oldest_first":
			files.sort(key=lambda x: x["mtime"])  # First old
		else:  # largest_first
			files.sort(key=lambda x: x["size"], reverse=True)  # The biggest ones first

		# 3. Selective purge
		freed_mb = 0
		for file_info in files:
			if check_disk_space(path, min_space_mb, media_type=None):
				break

			try:
				file_mb = file_info["size"] / (1024 * 1024)
				remove(file_info["path"])
				freed_mb += file_mb
				logger.info(f"Purged {media_type}: {basename(file_info['path'])} "
							f"({file_mb:.1f}MB, {ctime(file_info['mtime'])})")
			except Exception as e:
				logger.error(f"Purge failed for {file_info['path']}: {str(e)}")

		# 4. Final check
		success = check_disk_space(path, min_space_mb, media_type=None)
		logger.info(f"Freed {freed_mb:.1f}MB for {media_type}. Success: {success}")
		return success

	except Exception as e:
		logger.error(f"Space purge failed: {str(e)}")
		return False


def validate_media_path(path, media_type, min_space_mb=None):
	"""
	Validates and prepares a media storage path with comprehensive checks.
	Integrates with the custom ColorLogger system.

	Args:
		path: Path to validate (str)
		media_type: Media type for logging ('poster'|'backdrop')
		min_space_mb: Minimum required space in MB (int/float or None to skip check)

	Returns:
		str: Validated path (original or fallback to /tmp)
	"""

	def _log(message, level='info'):
		"""Internal wrapper for consistent logging with ColorLogger"""
		log_method = getattr(logger, level.lower())
		log_method(f"[MediaPath/{media_type}] {message}")

	try:
		start_time = time()

		# 1. Path creation
		try:
			makedirs(path, exist_ok=True)
			_log(f"Validated path: {path}", 'debug')
		except OSError as e:
			_log(f"Creation failed: {str(e)} - Using fallback", 'warning')
			path = f"/tmp/{media_type}"
			makedirs(path, exist_ok=True)
			return path

		# 2. Space validation (if requested)
		if min_space_mb is not None:
			try:
				stat = statvfs(path)
				free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)

				if free_mb <= min_space_mb:
					_log(f"Insufficient space: {free_mb:.1f}MB < {min_space_mb}MB - Using fallback", 'warning')
					path = f"/tmp/{media_type}"
					makedirs(path, exist_ok=True)
			except Exception as e:
				_log(f"Space check failed: {str(e)} - Using fallback", 'error')
				path = f"/tmp/{media_type}"
				makedirs(path, exist_ok=True)

		# 3. Final verification
		if not access(path, W_OK):
			_log("Path not writable - Using fallback", 'error')
			path = f"/tmp/{media_type}"
			makedirs(path, exist_ok=True)

		_log(f"Validation completed in {(time() - start_time):.2f}s - Final path: {path}", 'debug')
		return path

	except Exception as e:
		_log(f"Critical failure: {str(e)} - Using fallback", 'critical')
		fallback = f"/tmp/{media_type}"
		makedirs(fallback, exist_ok=True)
		return fallback


class MediaStorage:
	def __init__(self):
		self.logger = logger
		self.poster_folder = self._init_storage('poster')
		self.backdrop_folder = self._init_storage('backdrop')

	def _get_mount_points(self, media_type):
		"""Restituisce i punti di mount in base al tipo di media"""
		return [
			("/media/usb", f"/media/usb/{media_type}"),
			("/media/hdd", f"/media/hdd/{media_type}"),
			("/media/mmc", f"/media/mmc/{media_type}"),
			("/media/nas", f"/media/nas/{media_type}"),
			("/mnt/media", f"/mnt/media/{media_type}"),
			("/media/network", f"/media/network/{media_type}"),
			("/tmp", f"/tmp/{media_type}"),
			("/var/tmp", f"/var/tmp/{media_type}")
		]

	def _check_disk_space(self, path, min_space=50):
		"""Verifica spazio disponibile (50MB minimo)"""
		try:
			stat = statvfs(path)
			return (stat.f_bavail * stat.f_frsize) / (1024 * 1024) > min_space
		except:
			return False

	def _init_storage(self, media_type):
		"""Inizializza la cartella di storage"""
		for base_path, folder in self._get_mount_points(media_type):
			if exists(base_path) and access(base_path, W_OK):
				if self._check_disk_space(base_path):
					try:
						makedirs(folder, exist_ok=True)
						self.logger.info(f"Using {media_type} storage: {folder}")
						return folder
					except OSError as e:
						self.logger.warning(f"Create folder failed: {str(e)}")

		# Fallback
		fallback = f"/tmp/{media_type}"
		try:
			makedirs(fallback, exist_ok=True)
			self.logger.warning(f"Using fallback storage: {fallback}")
			return fallback
		except OSError as e:
			self.logger.critical(f"All storage options failed: {str(e)}")
			raise RuntimeError(f"No valid {media_type} storage available")


# Nella sezione MediaStorage Configuration
try:
	media_config = MediaStorage()
	POSTER_FOLDER = media_config.poster_folder
	BACKDROP_FOLDER = media_config.backdrop_folder  # <-- Questo già esiste
except Exception as e:
	logger.critical(f"MediaStorage initialization failed: {str(e)}")
	raise


def delete_old_files_if_low_disk_space(POSTER_FOLDER, min_free_space_mb=50, max_age_days=30):
	"""
	Elimina i file più vecchi se lo spazio disponibile nel disco è inferiore a min_free_space_mb.
	:param POSTER_FOLDER: la cartella in cui cercare i file da eliminare.
	:param min_free_space_mb: spazio minimo (in MB) che deve essere disponibile prima di eliminare i file.
	:param max_age_days: il numero di giorni oltre i quali i file verranno eliminati.
	"""
	try:
		from shutil import disk_usage
		total, used, free = disk_usage(POSTER_FOLDER)
		free_space_mb = free / (1024 ** 2)  # Converti in MB

		if free_space_mb < min_free_space_mb:
			print(f"Low disk space: {free_space_mb:.2f} MB available. Deleting old files...")

			current_time = time()

			age_limit = max_age_days * 86400  # 86400 è il numero di secondi in un giorno

			for filename in listdir(POSTER_FOLDER):
				file_path = join(POSTER_FOLDER, filename)

				if isfile(file_path):
					file_age = current_time - getmtime(file_path)

					if file_age > age_limit:
						remove(file_path)
						print(f"Deleted {filename}, it was {file_age / 86400:.2f} days old.")
		else:
			print(f"Sufficient disk space: {free_space_mb:.2f} MB available. No files will be deleted.")

	except Exception as e:
		print(f"Error while checking disk space or deleting old files: {e}")


delete_old_files_if_low_disk_space(POSTER_FOLDER, min_free_space_mb=50, max_age_days=30)

# ================ END MEDIASTORAGE CONFIGURATION ===============

# ================ START MEMORY CONFIGURATION ================


def MemClean():
	try:
		system('sync')
		system('echo 1 > /proc/sys/vm/drop_caches')
		system('echo 2 > /proc/sys/vm/drop_caches')
		system('echo 3 > /proc/sys/vm/drop_caches')
	except:
		pass

# ================= END MEMORY CONFIGURATION =================
