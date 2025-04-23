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

# Standard library imports
from Components.config import config
from pathlib import Path
from threading import Lock

# Initialize thread lock for API access synchronization
api_lock = Lock()

# ================ START SERVICE API CONFIGURATION ===============

# Default API keys (fallback values)
API_KEYS = {
	"tmdb_api": "3c3efcf47c3577558812bb9d64019d65",
	"omdb_api": "cb1d9f55",
	"thetvdb_api": "a99d487bb3426e5f3a60dea6d3d3c7ef",
	"fanart_api": "6d231536dea4318a88cb2520ce89473b",
}


def setup_api_keys():
	"""
	Configures API keys for the AGP system with flexible loading options.

	There are two methods to provide API keys:

	1. Direct Configuration (Recommended for development):
	   Simply replace the default values in the API_KEYS dictionary above.

	   Example:
	   API_KEYS = {
		   "tmdb_api": "your_tmdb_key_here",
		   "omdb_api": "your_omdb_key_here",
		   ...
	   }

	2. File-Based Configuration (Recommended for production):
	   Create individual files for each API key in the skin directory:
	   - /usr/share/enigma2/<skin_name>/tmdb_api
	   - /usr/share/enigma2/<skin_name>/omdb_api
	   - etc.

	   Each file should contain only the API key as plain text.

	Note: File-based configuration takes precedence over direct configuration.
	"""
	pass


def _load_api_keys():
	"""
	Internal function that loads API keys from configuration files.

	This function:
	1. Locates the current skin directory
	2. Checks for API key files
	3. Updates the API_KEYS dictionary with found keys
	4. Falls back to defaults if files aren't found

	Returns:
		bool: True if any keys were loaded successfully, False otherwise
	"""
	try:
		cur_skin = config.skin.primary_skin.value.replace("/skin.xml", "")
		skin_path = Path(f"/usr/share/enigma2/{cur_skin}")

		if not skin_path.exists():
			print(f"[API Config] Skin path not found: {skin_path}")
			return False

		# Map API key names to their corresponding file paths
		key_files = {
			"tmdb_api": skin_path / "tmdb_api",
			"thetvdb_api": skin_path / "thetvdb_api",
			"omdb_api": skin_path / "omdb_api",
			"fanart_api": skin_path / "fanart_api",
		}

		keys_loaded = False
		with api_lock:  # Lock to ensure thread-safety when accessing API key files

			for key_name, file_path in key_files.items():
				if file_path.exists():
					try:
						with open(file_path, "r") as f:
							API_KEYS[key_name] = f.read().strip()
						print(f"[API Config] Loaded {key_name} from {file_path}")
						keys_loaded = True
					except Exception as e:
						print(f"[API Config] Error reading {file_path}: {str(e)}")
				else:
					print(f"[API Config] Using default key for {key_name}")

		# Update global namespace with current API keys
		globals().update(API_KEYS)
		return keys_loaded

	except Exception as e:
		print(f"[API Config] Critical error loading keys: {str(e)}")
		return False


# Initialize API keys during module import
if not _load_api_keys():
	print("[API Config] Using default API keys")

# ================ END SERVICE API CONFIGURATION ================
