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

# Standard library
# # import Agp_apikeys
# from os.path import exists
from Components.config import config
from pathlib import Path
from threading import Lock
api_lock = Lock()

# ================ START SERVICE API CONFIGURATION ===============
# --- Dictionary for centralized management ---
API_KEYS = {
	"tmdb_api": "3c3efcf47c3577558812bb9d64019d65",
	"omdb_api": "cb1d9f55",
	"thetvdb_api": "a99d487bb3426e5f3a60dea6d3d3c7ef",
	"fanart_api": "6d231536dea4318a88cb2520ce89473b",
}


# --- Helper function to set up API keys ---


def setup_api_keys():
	"""
	Helper function to set up API keys.
	The user can either:
	1. Manually enter their API keys in the code.
	2. Provide the API keys via files stored in a specific directory.

	Instructions:
	1. To use the first method, directly replace the default values in the API_KEYS dictionary:

	   API_KEYS = {
		   "tmdb_api": "YOUR_TMDB_API_KEY",
		   "omdb_api": "YOUR_OMDB_API_KEY",
		   "thetvdb_api": "YOUR_THETVDB_API_KEY",
		   "fanart_api": "YOUR_FANART_API_KEY",
	   }

	2. To use the second method, create a file for each API key with the following naming convention:
	   - "tmdb_api" for the TMDB API key.
	   - "omdb_api" for the OMDB API key.
	   - "thetvdb_api" for the TVDB API key.
	   - "fanart_api" for the Fanart API key.

	   Each file should contain the respective API key as a plain text string.
	   These files should be stored in the following directory:
	   - /usr/share/enigma2/<skin_name>/

	   For example:
	   - /usr/share/enigma2/default_skin/tmdb_api contains the TMDB API key.

	Notes:
	- If you choose the file method, ensure that the file names match exactly with the keys in the API_KEYS dictionary.
	- The system will load the API keys from the files automatically if they exist, otherwise, it will fall back to the hardcoded default keys.
	"""
	pass


# --- Code management ---


my_cur_skin = False
cur_skin = config.skin.primary_skin.value.replace("/skin.xml", "")


def _load_api_keys():
	"""Internal function that loads API keys at startup."""
	try:
		cur_skin = config.skin.primary_skin.value.replace("/skin.xml", "")
		skin_path = Path(f"/usr/share/enigma2/{cur_skin}")

		if not skin_path.exists():
			print(f"[API Keys] Skin path not found: {skin_path}")
			return False

		key_files = {
			"tmdb_api": skin_path / "tmdb_api",
			"thetvdb_api": skin_path / "thetvdb_api",
			"omdb_api": skin_path / "omdb_api",
			"fanart_api": skin_path / "fanart_api",
		}

		for key_name, file_path in key_files.items():
			if file_path.exists():
				with open(file_path, "r") as f:
					API_KEYS[key_name] = f.read().strip()
			else:
				print(f"[API Keys] Warning: {key_name} file not found at {file_path}")

		globals().update(API_KEYS)
		return True

	except Exception as e:
		print(f"[API Keys] Error loading keys: {str(e)}")
		return False


_load_api_keys()


# ================ END SERVICE API CONFIGURATION ================
