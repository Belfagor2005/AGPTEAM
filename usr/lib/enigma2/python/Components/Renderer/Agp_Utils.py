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
# Import platform for OS information (currently commented out)
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
from os.path import (  # Path manipulation utilities
	join,
	exists,
	isfile,
	dirname,
	getsize,
	getmtime,
	basename,

)
from pathlib import Path  # Object-oriented path handling
import glob              # Pattern-based file searching
# from functools import lru_cache

# ========================
# IMPORTS FOR LOGGING
# ========================

from logging import (
	getLogger,
	DEBUG,
	INFO,
	Formatter,
	StreamHandler,
)
from logging.handlers import RotatingFileHandler

# ========================
# IMPORTS FOR TIME/DATE
# ========================
from time import ctime
from datetime import datetime, timedelta
import time
# ========================
# IMPORTS FOR TEXT PROCESSING
# ========================
from unicodedata import normalize
from re import sub, IGNORECASE

# ========================
# ENIGMA SPECIFIC IMPORTS
# ========================
from Components.config import config

# ========================
# THREADING
# ========================
from threading import Timer, Lock as threading_Lock

# Check Python version
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
		'RESET': '\033[0m'       # Reset color
	}

	@classmethod
	def log(cls, level, message):
		"""Log message with colored output"""
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
			'RESET': '\033[0m'       # Reset color
		}

		def format(self, record):
			"""Format log record with color"""
			levelname = record.levelname
			if levelname in self.COLORS:
				record.levelname = (f"{self.COLORS[levelname]}{levelname}" f"{self.COLORS['RESET']}")
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

MIN_BACKDROP_WIDTH = 500  # Minimum width in pixels
MAX_ORIGINAL_SIZE = 10    # Maximum file size in MB


def verify_backdrop_integrity(self):
	"""Verify that folder and cache are synchronized"""
	missing_files = 0

	# Check each cache entry
	for title, entry in list(self.cache.cache.items()):
		if not exists(entry['path']):
			logger.warning(f"Missing file: {entry['path']}")
			del self.cache.cache[title]
			missing_files += 1

	if missing_files:
		logger.info(f"Cleaned {missing_files} invalid cache entries")
		self.cache._async_save()
# validate_backdrop_folder()

# ================ END GUI CONFIGURATION ===============


# ================ START TEXT MANAGER ===============

try:
	from .Agp_lib import convtext
except ImportError:
	logger.warning("convtext not found, using fallback")

	def convtext(x):
		"""Fallback text conversion function"""
		return x


def clean_epg_text(text):
	"""Centralized text cleaning for EPG data"""
	if not text:
		return ""
	text = str(text).replace('\xc2\x86', '').replace('\xc2\x87', '')
	return text.encode('utf-8', 'ignore') if not PY3 else text


def clean_filename(title):
	"""
	Sanitize title for use as filename.
	Handles special characters and accents.

	Args:
		title: Original title string.

	Returns:
		str: Cleaned filename-safe string.
	"""
	if not title:
		return "no_title"

	# Convert to ASCII (remove accents)
	title = normalize('NFKD', title)
	title = title.encode('ascii', 'ignore').decode('ascii')

	# Remove special characters and normalize
	title = sub(r'[^\w\s-]', '_', title)  # Replace special chars with _
	title = sub(r'[\s-]+', '_', title)    # Replace spaces and - with _
	title = sub(r'_+', '_', title)        # Reduce multiple _ to single
	title = title.strip('_')                 # Remove _ from start/end

	return title.lower()[:100]  # Limit to 100 chars


def clean_for_tvdb_optimized(title):
	"""
	Optimized version for fast title cleaning
	Removes common articles and patterns for better API matching

	Args:
		title: Original title string

	Returns:
		str: Cleaned title ready for TVDB API
	"""
	if not title:
		return ""

	# Convert to ASCII (remove accents)
	title = normalize('NFKD', title)
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


# @lru_cache(maxsize=2000)
def clean_for_tvdb(title):
	"""
	Prepare title for API searches with comprehensive cleaning

	Args:
		title: Original title string

	Returns:
		str: Cleaned title ready for TVDB API
	"""
	original_title = title  # Safe copy for logging

	if not isinstance(title, str) or not title.strip():
		return ""

	try:
		# Convert to ASCII (remove accents)
		title = normalize('NFKD', title)
		title = title.encode('ascii', 'ignore').decode('ascii')

		# Final cleanup
		title = convtext(title)
		title = sub(r'\s+', ' ', title).strip()
		return title

	except Exception as e:
		logger.error("Error cleaning title '%s': %s", str(original_title), str(e))
		return ""

# ================ END TEXT MANAGER ===============


# ================ START MEDIASTORAGE CONFIGURATION ===============


def check_disk_space(path, min_space_mb, media_type=None, purge_strategy="oldest_first"):
	"""
	Check disk space and optionally purge old files if needed

	Args:
		path: Path to check
		min_space_mb: Minimum required space in MB
		media_type: Type of media for logging
		purge_strategy: "oldest_first" or "largest_first"

	Returns:
		bool: True if enough space is available
	"""
	try:
		# Fallback to /tmp if path don't exist
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
	Free up space by deleting old files based on strategy

	Args:
		path: Path to clean up
		min_space_mb: Target free space in MB
		media_type: Type of media for logging
		strategy: Deletion strategy ("oldest_first" or "largest_first")

	Returns:
		bool: True if target space was achieved
	"""
	try:
		# 1. Collect files with metadata
		files = []
		for f in listdir(path):
			filepath = join(path, f)
			if isfile(filepath):
				files.append({
					"path": filepath,
					"size": getsize(filepath),
					"mtime": getmtime(filepath)
				})

		# 2. Sort files by strategy
		if strategy == "oldest_first":
			files.sort(key=lambda x: x["mtime"])  # Oldest first
		else:  # largest_first
			files.sort(key=lambda x: x["size"], reverse=True)  # Largest first

		# 3. Selective purge
		freed_mb = 0
		for file_info in files:
			if check_disk_space(path, min_space_mb, media_type=None):
				break

			try:
				file_mb = file_info["size"] / (1024 * 1024)
				remove(file_info["path"])
				freed_mb += file_mb
				logger.info(
					f"Purged {media_type}: {basename(file_info['path'])} "f"({file_mb:.1f}MB, {ctime(file_info['mtime'])})")
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
	Validate and prepare a media storage path with comprehensive checks

	Args:
		path: Path to validate
		media_type: Media type for logging
		min_space_mb: Minimum required space

	Returns:
		str: Validated path (original or fallback)
	"""
	def _log(message, level='info'):
		"""Internal logging wrapper"""
		# Define the log method based on level
		if level.lower() == 'debug':
			logger.debug(f"[MediaPath/{media_type}] {message}")
		elif level.lower() == 'warning':
			logger.warning(f"[MediaPath/{media_type}] {message}")
		elif level.lower() == 'error':
			logger.error(f"[MediaPath/{media_type}] {message}")
		elif level.lower() == 'critical':
			logger.critical(f"[MediaPath/{media_type}] {message}")
		else:  # default to info
			logger.info(f"[MediaPath/{media_type}] {message}")

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
	"""Centralized media storage management"""
	def __init__(self):
		self.logger = logger
		self.poster_folder = self._init_storage('poster')
		self.backdrop_folder = self._init_storage('backdrop')
		self.imovie_folder = self._init_storage('imovie')

	def _get_mount_points(self, media_type):
		"""Get potential storage locations based on media type"""
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
		"""Check available disk space (50MB minimum)"""
		try:
			stat = statvfs(path)
			return (stat.f_bavail * stat.f_frsize) / (1024 * 1024) > min_space
		except:
			return False

	def _init_storage(self, media_type):
		"""Initialize storage folder"""
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
	BACKDROP_FOLDER = media_config.backdrop_folder
	IMOVIE_FOLDER = media_config.imovie_folder
except Exception as e:
	logger.critical(f"MediaStorage initialization failed: {str(e)}")
	raise


def delete_old_files_if_low_disk_space(POSTER_FOLDER, min_free_space_mb=50, max_age_days=30):
	"""
	Delete old files if disk space is below threshold

	Args:
		POSTER_FOLDER: Folder to clean
		min_free_space_mb: Minimum required free space in MB
		max_age_days: Maximum age of files to keep
	"""
	try:
		from shutil import disk_usage
		total, used, free = disk_usage(POSTER_FOLDER)
		free_space_mb = free / (1024 ** 2)  # Convert to MB

		if free_space_mb < min_free_space_mb:
			print(f"Low disk space: {free_space_mb:.2f} MB available. Deleting old files...")

			current_time = time()

			age_limit = max_age_days * 86400  # Seconds in a day

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
	"""Clear system memory caches"""
	try:
		system('sync')  # Flush filesystem buffers
		system('echo 1 > /proc/sys/vm/drop_caches')  # Clear pagecache
		system('echo 2 > /proc/sys/vm/drop_caches')  # Clear dentries and inodes
		system('echo 3 > /proc/sys/vm/drop_caches')  # Clear all caches
	except:
		pass

# ================ END MEMORY CONFIGURATION ================

# ================ START SERVICE API CONFIGURATION ===============


# Initialize API lock for thread safety
api_lock = threading_Lock()

# Default API keys
tmdb_api = "3c3efcf47c3577558812bb9d64019d65"
thetvdb_api = "a99d487bb3426e5f3a60dea6d3d3c7ef"
# thetvdb_api = 'D19315B88B2DE21F'
omdb_api = "cb1d9f55"
fanart_api = "6d231536dea4318a88cb2520ce89473b"

# Centralized API key management
API_KEYS = {
	"tmdb_api": tmdb_api,
	"thetvdb_api": thetvdb_api,
	"omdb_api": omdb_api,
	"fanart_api": fanart_api,
}


def _load_api_keys():
	"""Load API keys from skin configuration files"""
	try:
		cur_skin = config.skin.primary_skin.value.replace('/skin.xml', '')
		skin_path = Path(f"/usr/share/enigma2/{cur_skin}")

		# Map API keys to their respective files
		key_files = {
			"tmdb_api": skin_path / "tmdb_api",
			"thetvdb_api": skin_path / "thetvdb_api",
			"omdb_api": skin_path / "omdb_api",
			"fanart_api": skin_path / "fanart_api",
		}

		# Load each key file if it exists
		for key_name, file_path in key_files.items():
			if file_path.exists():
				with open(file_path, "r") as f:
					API_KEYS[key_name] = f.read().strip()

		# Update global variables for backward compatibility
		globals().update(API_KEYS)
		return True

	except Exception as e:
		print(f"[API Keys] Loading error: {str(e)}")
		return False


# Initialize API keys
_load_api_keys()


# ================ END SERVICE API CONFIGURATION ================
