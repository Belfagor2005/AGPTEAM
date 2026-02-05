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
#  Last Modified: "18:14 - 20250512"                    #
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

# ========================
# SYSTEM IMPORTS
# ========================
from sys import version_info, stdout, stderr
from functools import lru_cache
from os import (
	makedirs,
	statvfs,
	listdir,
	remove,
	access,
	W_OK,
	system,
	stat,
	chmod,
	getuid
)
from os.path import (
	join,
	exists,
	isfile,
	dirname,
	getsize,
	getmtime,
	basename,
	isdir
)
from pathlib import Path
import glob
import tempfile

# from functools import lru_cache

# ========================
# IMPORTS FOR LOGGING
# ========================
from logging.handlers import RotatingFileHandler
import logging
from logging import (
	getLogger,
	DEBUG,
	INFO,
	Formatter,
	StreamHandler,
)

# ========================
# IMPORTS FOR TIME/DATE
# ========================
from time import ctime, mktime
from datetime import datetime, timedelta
import time
# ========================
# IMPORTS FOR TEXT PROCESSING
# ========================
from unicodedata import normalize
from re import sub, IGNORECASE, S, I, search

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


class AdvancedColorFormatter(Formatter):
	"""Advanced formatter with ANSI colors and timestamp management"""
	COLORS = {
		'DEBUG': '\033[36m',     # Cyan
		'INFO': '\033[32m',      # Green
		'WARNING': '\033[33m',   # Yellow
		'ERROR': '\033[31m',     # Red
		'CRITICAL': '\033[41m',  # Red on background
		'RESET': '\033[0m'
	}

	def format(self, record):
		"""Format the record with colors and timestamps"""
		level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
		timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
		return f"{timestamp} {level_color}[{record.levelname}]{self.COLORS['RESET']} {record.getMessage()}"


def setup_logging(log_file='/tmp/agplog/agp_full.log', max_log_size=2, backup_count=3):
	"""
	Advanced logging configuration with:
	- Colored console output
	- File rotation
	- Robust error handling
	"""

	# Create log folder if it does not exist
	log_dir = dirname(log_file)
	makedirs(log_dir, exist_ok=True)

	# Create main logger
	logger = getLogger('AGP')
	logger.setLevel(DEBUG)

	# Remove existing handlers
	for handler in logger.handlers[:]:
		logger.removeHandler(handler)

	try:
		# Console Handler
		console_handler = StreamHandler(stdout)
		console_handler.setFormatter(AdvancedColorFormatter())
		console_handler.setLevel(INFO)

		# File Handler with Rotation
		file_handler = RotatingFileHandler(
			log_file,
			maxBytes=max_log_size * 1024 * 1024,
			backupCount=backup_count,
			encoding='utf-8'
		)
		file_formatter = Formatter(
			'%(asctime)s [%(process)d] %(levelname)s: %(message)s',
			datefmt='%Y-%m-%d %H:%M:%S'
		)
		file_handler.setFormatter(file_formatter)
		file_handler.setLevel(DEBUG)

		# Add handler
		logger.addHandler(console_handler)
		logger.addHandler(file_handler)

		# Init Log
		logger.info("=" * 50)
		logger.info("AGP Logger initialized")
		logger.info(f"Log file: {log_file}")
		logger.info("=" * 50)

	except Exception as e:
		stderr.write(f"CRITICAL LOGGING ERROR: {str(e)}\n")
		raise

	return logger


def cleanup_old_logs(log_file, max_days=7):
	"""Pulizia log obsoleti con controllo errori"""
	try:
		cutoff = datetime.now() - timedelta(days=max_days)
		cutoff_timestamp = mktime(cutoff.timetuple())

		for f in glob.glob(f"{log_file}*"):
			if isfile(f) and stat(f).st_mtime < cutoff_timestamp:
				try:
					remove(f)
				except Exception as e:
					logging.error(f"Errore cancellazione {f}: {str(e)}")

	except Exception as e:
		logging.error(f"Log cleanup failed: {str(e)}")


def schedule_log_cleanup(interval_hours=12):
	"""Scheduler affidabile per pulizia log"""
	def _wrapper():
		try:
			cleanup_old_logs('/tmp/agplog/agp_full.log')
		finally:
			Timer(interval_hours * 3600, _wrapper).start()

	_wrapper()


logger = setup_logging()
schedule_log_cleanup()

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
except BaseException:
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
			logger.warning(f"verify_backdrop_integrity Missing file: {entry['path']}")
			del self.cache.cache[title]
			missing_files += 1

	if missing_files:
		logger.info(f"verify_backdrop_integrity Cleaned {missing_files} invalid cache entries")
		self.cache._async_save()
# validate_backdrop_folder()

# ================ END GUI CONFIGURATION ===============
# ================ START TEXT MANAGER ===============


try:
	from .Agp_lib import convtext
	# from .Converlib import convtext
except ImportError:
	logger.warning("AGP Utils ImportError convtext not found, using fallback")

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
	Handles special characters, accents, and Unicode properly.

	Args:
		title: Original title (str, bytes or any object).

	Returns:
		str: Cleaned filename-safe string (returns "no_title" for empty input).
	"""
	# Handle empty/None input
	if not title:
		return "no_title"

	# Convert to string if not already str/bytes
	if not isinstance(title, (str, bytes)):
		try:
			title = str(title)
		except Exception:
			return "no_title"

	try:
		# Decode bytes to UTF-8 string
		if isinstance(title, bytes):
			title = title.decode('utf-8', errors='ignore')

		# Preserve original for fallback
		original_title = title

		# Try ASCII conversion but keep original if it fails
		try:
			title = normalize('NFKD', title)
			title = title.encode('ascii', 'ignore').decode('ascii')
			if not title.strip():  # If conversion wiped the string
				title = original_title
		except Exception:
			title = original_title

		# Replace special chars (keep alphanumeric, spaces, and hyphens)
		title = sub(r'[^\w\s-]', '_', title)

		# Normalize separators
		title = sub(r'[\s-]+', '_', title)  # Convert spaces and hyphens to _
		title = sub(r'_+', '_', title)      # Collapse multiple _
		title = title.strip('_')            # Trim _ from ends

		# Final cleanup and length limit
		clean_title = title.lower()[:100]

		return clean_title if clean_title else "no_title"

	except Exception:
		return "no_title"


# Character replacement mapping for filename sanitization
CHAR_REPLACEMENTS = {
	"$": "s",
	"@": "at",
	"€": "",
	"&": "",
	"£": "",
	"¢": "",
	"¥": "",
	"©": "",
	"®": "",
	"™": "",
	"°": "",
	"¡": "",
	"¿": "",
	"§": "",
	"¶": "",
	"•": "",
	"–": "",  # En dash
	"—": "",  # Em dash
	"“": "",  # Left double quote
	"”": "",  # Right double quote
	"‘": "",  # Left single quote
	"’": "",  # Right single quote
	"«": "",  # Left-pointing double angle quote
	"»": "",  # Right-pointing double angle quote
	"/": "",  # Slash
	":": " ",  # Colon
	"*": "",  # Asterisk
	"?": "",  # Question mark
	"!": "",  # Exclamation mark
	"#": "",  # Hash
	"~": "",  # Tilde
	"^": "",  # Caret
	"=": "",  # Equals
	"(": "",  # Open parenthesis
	")": "",  # Close parenthesis
	"[": "",  # Open bracket
	"]": "",  # Close bracket
	'"': "",
	"live:": "",
	"Х/Ф": "",
	"М/Ф": "",
	"Х/ф": "",
	"18+": "",
	"18+": "",
	"16+": "",
	"16+": "",
	"12+": "",
	"12+": "",
	"7+": "",
	"7+": "",
	"6+": "",
	"6+": "",
	"0+": "",
	"0+": "",
	"+": "",
	"المسلسل العربي": "",
	"مسلسل": "",
	"برنامج": "",
	"فيلم وثائقى": "",
	"حفل": ""
}


def clean_for_tvdb_optimized(title):
	"""
	Optimized version for fast title cleaning
	Removes common articles and patterns for better API matching
	Handles special characters, encodings and Unicode normalization

	Args:
		title: Original title (str, bytes or any object)

	Returns:
		str: Cleaned title ready for TVDB API or empty string on error
	"""
	# Handle None or empty input
	if not title:
		return ""

	# Convert to string if not already str/bytes
	if not isinstance(title, (str, bytes)):
		try:
			title = str(title)
		except Exception as e:
			logger.error(f"clean_for_tvdb_optimized Title conversion error '{title!r}': {str(e)}")
			return ""

	try:
		# Decode bytes to UTF-8 string
		if isinstance(title, bytes):
			title = title.decode('utf-8', errors='ignore')

		# Preserve original for fallback
		original_title = title

		# Convert to ASCII (remove accents) but keep original if conversion fails
		try:
			title = normalize('NFKD', title)
			title = title.encode('ascii', 'ignore').decode('ascii')
			if not title.strip():  # If conversion wiped the string
				title = original_title
		except Exception:
			title = original_title

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

	except Exception as e:
		logger.error(f"clean_for_tvdb_optimized Error cleaning title: {str(e)}")
		return ""


def cleanText(text):
	cutlist = [
		# Video Resolutions and Formats
		'720p', '1080p', '1080i', 'PAL', 'HDTV', 'HDTVRiP', 'HDRiP', 'Web-DL', 'WEBHDTV', 'WebHD', 'WEBHDTVRiP',
		'WEBHDRiP', 'WEBRiP', 'ITUNESHD', 'DVDR', 'DVDR5', 'DVDR9', 'DVDRiP', 'BDRiP', 'BLURAY',

		# Codecs and audio
		'x264', 'h264', 'AVC', 'AC3', 'AC3D', 'AC3MD', 'DTS', 'DTSD', 'DD51', 'XViD', 'DIVX',

		# Release type
		'UNRATED', 'RETAIL', 'COMPLETE', 'INTERNAL', 'REPACK', 'SYNC',

		# Language and dubbing
		'GERMAN', 'ENGLiSH', 'DUBBED', 'LINE.DUBBED',

		# Various
		'WS', 'LD', 'MiC', 'MD', 'TS', 'DVDSCR', 'UNCUT', 'ANiME', 'DL'
	]

	text = text.replace('.wmv', '').replace('.flv', '').replace('.ts', '').replace('.m2ts', '').replace('.mkv', '').replace('.avi', '').replace('.mpeg', '').replace('.mpg', '').replace('.iso', '').replace('.mp4', '')

	for word in cutlist:
		text = sub(r'(\_|\-|\.|\+)' + word + r'(\_|\-|\.|\+)', '+', text, flags=I)
	text = text.replace('.', ' ').replace('-', ' ').replace('_', ' ').replace('+', '').replace(" Director's Cut", "").replace(" director's cut", "").replace("[Uncut]", "").replace("Uncut", "").replace("Elokuva: ", "").replace("Uusi Kino: ", "").replace("Kino Klassikko: ", "").replace("Kino Suomi: ", "").replace("Kino: ", "")

	text_split = text.split()
	if text_split and text_split[0].lower() in ("new:", "live:"):
		text_split.pop(0)  # remove annoying prefixes
	text = " ".join(text_split)

	if search(r'[Ss][\d]+[Ee][\d]+', text):
		text = sub(r'[Ss][\d]+[Ee][\d]+.*[\w]+', '', text, flags=S | I)
	text = sub(r'\(.*\)', '', text).rstrip()  # remove episode number from series, like "series name (234)"

	return text


@lru_cache(maxsize=2000)
def clean_for_tvdb(title):
	"""
	Prepare title for API searches with comprehensive cleaning
	Handles special characters, encodings and Unicode normalization

	Args:
		title: Original title (str, bytes or any object)

	Returns:
		str: Cleaned title ready for TVDB API or empty string on error
	"""
	# Handle None or empty input
	if title is None:
		return ""

	# Convert to string if not already str/bytes
	if not isinstance(title, (str, bytes)):
		try:
			title = str(title)
		except Exception as e:
			logger.error(f"clean_for_tvdb Title conversion error '{title!r}': {str(e)}")
			return ""

	# Handle empty string after conversion
	if not title.strip():
		return ""

	original_title = title  # Keep copy for error reporting

	try:
		# Decode bytes to UTF-8 string
		if isinstance(title, bytes):
			try:
				title = title.decode('utf-8')
			except UnicodeDecodeError:
				title = title.decode('utf-8', errors='ignore')

		# Preserve original for fallback
		clean_title = title

		# Replace characters based on the custom map
		for char, replacement in CHAR_REPLACEMENTS.items():
			title = title.replace(char, replacement)

		# Try ASCII conversion but keep original if it fails
		try:
			temp_title = normalize('NFKD', title)
			temp_title = temp_title.encode('ascii', 'ignore').decode('ascii')
			if temp_title.strip():  # Only use if conversion produced valid text
				clean_title = temp_title
		except Exception:
			pass  # Keep original title if conversion fails

		# Process with convtext
		final_title = convtext(clean_title)
		# final_title = cleanText(clean_title)

		# Handle convtext returning None
		if final_title is None:
			# Try with original title before ASCII conversion
			final_title = convtext(title)
			if final_title is None:
				return ""

		# Final whitespace cleanup
		final_title = sub(r'\s+', ' ', final_title).strip()

		return final_title

	except Exception as e:
		logger.error(f"clean_for_tvdb Error cleaning title '{str(original_title)}': {str(e)}")
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

		logger.warning(f"check_disk_space Low space in {path}: {free_mb:.1f}MB < {min_space_mb}MB")

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
		logger.error(f"check_disk_space Space check failed: {str(e)}")
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
					f"free_up_space Purged {media_type}: {basename(file_info['path'])} "f"({file_mb:.1f}MB, {ctime(file_info['mtime'])})")
			except Exception as e:
				logger.error(f"free_up_space Purge failed for {file_info['path']}: {str(e)}")

		# 4. Final check
		success = check_disk_space(path, min_space_mb, media_type=None)
		logger.info(f"free_up_space Freed {freed_mb:.1f}MB for {media_type}. Success: {success}")
		return success

	except Exception as e:
		logger.error(f"free_up_space Space purge failed: {str(e)}")
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
	try:

		if not exists(path):
			makedirs(path, exist_ok=True)

		if not access(path, W_OK):
			raise PermissionError(f"Path not writable: {path}")

		if min_space_mb is not None:
			stat = statvfs(path)
			free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
			if free_mb < min_space_mb:
				raise OSError(f"Insufficient space: {free_mb}MB < {min_space_mb}MB")

		return path

	except Exception as e:
		logger.error(f"validate_media_path Validation failed: {str(e)}")
		# Fallback a /tmp
		fallback = f"/tmp/{media_type}"
		makedirs(fallback, exist_ok=True)
		return fallback


"""
# def validate_media_path(path, media_type, min_space_mb=None):
	# '''
	# Validate and prepare a media storage path with comprehensive checks

	# Args:
		# path: Path to validate
		# media_type: Media type for logging
		# min_space_mb: Minimum required space

	# Returns:
		# str: Validated path (original or fallback)
	# '''
	# def _log(message, level='info'):
		# '''Internal logging wrapper'''
		# # Define the log method based on level
		# if level.lower() == 'debug':
			# logger.debug(f"[MediaPath/{media_type}] {message}")
		# elif level.lower() == 'warning':
			# logger.warning(f"[MediaPath/{media_type}] {message}")
		# elif level.lower() == 'error':
			# logger.error(f"[MediaPath/{media_type}] {message}")
		# elif level.lower() == 'critical':
			# logger.critical(f"[MediaPath/{media_type}] {message}")
		# else:  # default to info
			# logger.info(f"[MediaPath/{media_type}] {message}")

	# try:
		# start_time = time()

		# # 1. Path creation
		# try:
			# makedirs(path, exist_ok=True)
			# _log(f"Validated path: {path}", 'debug')
		# except OSError as e:
			# _log(f"Creation failed: {str(e)} - Using fallback", 'warning')
			# path = f"/tmp/{media_type}"
			# makedirs(path, exist_ok=True)
			# return path

		# # 2. Space validation (if requested)
		# if min_space_mb is not None:
			# try:
				# stat = statvfs(path)
				# free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)

				# if free_mb <= min_space_mb:
					# _log(f"Insufficient space: {free_mb:.1f}MB < {min_space_mb}MB - Using fallback", 'warning')
					# path = f"/tmp/{media_type}"
					# makedirs(path, exist_ok=True)
			# except Exception as e:
				# _log(f"Space check failed: {str(e)} - Using fallback", 'error')
				# path = f"/tmp/{media_type}"
				# makedirs(path, exist_ok=True)

		# # 3. Final verification
		# if not access(path, W_OK):
			# _log("Path not writable - Using fallback", 'error')
			# path = f"/tmp/{media_type}"
			# makedirs(path, exist_ok=True)

		# _log(f"Validation completed in {(time() - start_time):.2f}s - Final path: {path}", 'debug')
		# return path

	# except Exception as e:
		# _log(f"Critical failure: {str(e)} - Using fallback", 'critical')
		# fallback = f"/tmp/{media_type}"
		# makedirs(fallback, exist_ok=True)
		# return fallback
"""


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
			("/media/hdd", f"/media/hdd/{media_type}"),
			("/media/usb", f"/media/usb/{media_type}"),
			("/media/mmc", f"/media/mmc/{media_type}"),
			("/media/nas", f"/media/nas/{media_type}"),
			("/mnt/media", f"/mnt/media/{media_type}"),
			("/media/network", f"/media/net/{media_type}"),
			("/tmp", f"/tmp/{media_type}"),
			("/var/tmp", f"/var/tmp/{media_type}")
		]

	def _check_disk_space(self, path, min_space=50):
		"""Check available disk space (50MB minimum)"""
		try:
			stat = statvfs(path)
			return (stat.f_bavail * stat.f_frsize) / (1024 * 1024) > min_space
		except BaseException:
			return False

	def _init_storage(self, media_type):
		"""Initialize storage folder"""
		for base_path, folder in self._get_mount_points(media_type):
			if exists(base_path) and access(base_path, W_OK):
				if self._check_disk_space(base_path):
					try:
						makedirs(folder, exist_ok=True)
						self.logger.info(f"MediaStorage Using {media_type} storage: {folder}")
						return folder
					except OSError as e:
						self.logger.warning(f"MediaStorage Create folder failed: {str(e)}")

		# Fallback
		fallback = f"/tmp/{media_type}"
		try:
			makedirs(fallback, exist_ok=True)
			self.logger.warning(f"MediaStorage Using fallback storage: {fallback}")
			return fallback
		except OSError as e:
			self.logger.critical(f"MediaStorage All storage options failed: {str(e)}")
			raise RuntimeError(f"MediaStorage No valid {media_type} storage available")


# MediaStorage Configuration
try:
	media_config = MediaStorage()
	POSTER_FOLDER = media_config.poster_folder
	BACKDROP_FOLDER = media_config.backdrop_folder
	IMOVIE_FOLDER = media_config.imovie_folder
except Exception as e:
	logger.critical(f"MediaStorage initialization failed: {str(e)}")
	raise


def delete_old_files_if_low_disk_space(MEDIA_FOLDER, min_free_space_mb=50, max_age_days=30):
	"""
	Delete old files if disk space is below threshold

	Args:
		MEDIA_FOLDER: Folder to clean
		min_free_space_mb: Minimum required free space in MB
		max_age_days: Maximum age of files to keep
	"""
	try:
		from shutil import disk_usage
		total, used, free = disk_usage(MEDIA_FOLDER)
		free_space_mb = free / (1024 ** 2)  # Convert to MB

		if free_space_mb < min_free_space_mb:
			logger.warning(f"{MEDIA_FOLDER}: Low disk space: {free_space_mb:.2f} MB available. Deleting old files...")

			current_time = time()

			age_limit = max_age_days * 86400  # Seconds in a day

			for filename in listdir(MEDIA_FOLDER):
				file_path = join(MEDIA_FOLDER, filename)

				if isfile(file_path):
					file_age = current_time - getmtime(file_path)

					if file_age > age_limit:
						remove(file_path)
						logger.debug(f"{MEDIA_FOLDER}: Deleted {filename}, it was {file_age / 86400:.2f} days old.")
		else:
			logger.info(f"{MEDIA_FOLDER}: Sufficient disk space: {free_space_mb:.2f} MB available. No files will be deleted.")

	except Exception as e:
		logger.critical(f"Error while checking disk space or deleting old files: {e}")


delete_old_files_if_low_disk_space(POSTER_FOLDER, min_free_space_mb=50, max_age_days=30)
delete_old_files_if_low_disk_space(BACKDROP_FOLDER, min_free_space_mb=50, max_age_days=30)
delete_old_files_if_low_disk_space(IMOVIE_FOLDER, min_free_space_mb=50, max_age_days=30)


def create_secure_log_dir():
	"""Create a secure log directory with safety checks for Python 2.7"""
	base_tmp = tempfile.gettempdir()
	target_dir = join(base_tmp, "agplog")

	try:
		# Create directory with secure permissions
		if not exists(target_dir):
			makedirs(target_dir, 0o700)
		else:
			# Ensure existing directory has safe permissions
			chmod(target_dir, 0o700)

		# Verify directory security
		# 1. Check it's a real directory (using os.path.isdir instead of stat)
		if not isdir(target_dir):
			return tempfile.mkdtemp(prefix="agplog_")  # Fallback

		# 2. Verify ownership
		if stat(target_dir).st_uid != getuid():
			return tempfile.mkdtemp(prefix="agplog_")  # Fallback

		return target_dir

	except (OSError, Exception):
		# Fallback to secure tempfile method if any operation fails
		return tempfile.mkdtemp(prefix="agplog_")


# Usage:
secure_log_dir = create_secure_log_dir()


# ================ END MEDIASTORAGE CONFIGURATION ===============
# ================ START MEMORY CONFIGURATION ================


def MemClean():
	"""Clear system memory caches"""
	try:
		logger.info("Clear system memory caches")
		system('sync')  # Flush filesystem buffers
		system('echo 1 > /proc/sys/vm/drop_caches')  # Clear pagecache
		system('echo 2 > /proc/sys/vm/drop_caches')  # Clear dentries and inodes
		system('echo 3 > /proc/sys/vm/drop_caches')  # Clear all caches
	except BaseException:
		pass

# ================ END MEMORY CONFIGURATION ================
# ================ START SERVICE API CONFIGURATION ===============


# Initialize API lock for thread safety
api_lock = threading_Lock()

# Default API keys
tmdb_api = "3c3efcf47c3577558812bb9d64019d65"
thetvdb_api = "a99d487bb3426e5f3a60dea6d3d3c7ef"
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
		logger.info("Load API keys from skin configuration files")
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
		logger.warning(f"[API Keys] Loading error: {str(e)}")
		return False


# Initialize API keys
_load_api_keys()


# ================ END SERVICE API CONFIGURATION ================
if __name__ == "__main__":
	# Test locale del logger
	test_logger = setup_logging()
	test_logger.debug("Test debug")
	test_logger.info("Test info")
	test_logger.warning("Test warn")
	test_logger.error("Test error")
	test_logger.critical("Test critical")
else:
	# Inizializzazione per Enigma2
	logger = setup_logging()
	logger.info("AGP Utils initialized")
