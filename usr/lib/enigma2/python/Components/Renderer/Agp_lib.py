#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
"""
#########################################################
#                                                       #
#  AGP - Advanced Graphics BackdropRenderer             #
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

from re import compile, DOTALL, sub, IGNORECASE
from unicodedata import normalize, category
import sys
from Components.config import config
# from functools import lru_cache


DEBUG = False  # active for show text cleaned in debug

try:
	unicode
except NameError:
	unicode = str


PY3 = sys.version_info[0] >= 3
if not PY3:
	from urllib import quote_plus
else:
	from urllib.parse import quote_plus


def quoteEventName(eventName):
	"""
	Quote and clean event names for URL encoding
	Handles special characters and encoding issues
	"""
	try:
		text = eventName.decode('utf8').replace(u'\x86', u'').replace(u'\x87', u'').encode('utf8')
	except:
		text = eventName
	return quote_plus(text, safe="+")


lng = "en"
try:
	lng = config.osd.language.value[:-3]
except:
	lng = "en"


# Complex regex pattern for cleaning various text patterns
REGEX = compile(
	r'[\(\[].*?[\)\]]|'                    # Round or square brackets
	r':?\s?odc\.\d+|'                      # "odc." with or without a preceding number
	r'\d+\s?:?\s?odc\.\d+|'                # Number followed by "odc."
	r'[:!]|'                               # Colon or exclamation mark
	r'\s-\s.*|'                            # Dash followed by text
	r',|'                                  # Comma
	r'/.*|'                                # Everything after a slash
	r'\|\s?\d+\+|'                         # Pipe followed by number and plus sign
	r'\d+\+|'                              # Number followed by plus sign
	r'\s\*\d{4}\Z|'                        # Asterisk followed by a 4-digit year
	r'[\(\[\|].*?[\)\]\|]|'                # Round, square brackets or pipe with content
	r'(?:\"[\.|\,]?\s.*|\"|'               # Text in quotes
	r'\.\s.+)|'                            # Dot followed by text
	r'Премьера\.\s|'                       # "Premiere." (specific to Russian)
	r'[хмтдХМТД]/[фс]\s|'                  # Russian pattern with /ф or /с
	r'\s[сС](?:езон|ерия|-н|-я)\s.*|'      # Season or episode in Russian
	r'\s\d{1,3}\s[чсЧС]\.?\s.*|'           # Part/episode number in Russian
	r'\.\s\d{1,3}\s[чсЧС]\.?\s.*|'         # Part/episode number in Russian with leading dot
	r'\s[чсЧС]\.?\s\d{1,3}.*|'             # Russian part/episode marker followed by number
	r'\d{1,3}-(?:я|й)\s?с-н.*', DOTALL)    # Ending with number and Russian suffix


def remove_accents(string):
	"""
	Remove diacritic marks from characters
	Normalizes unicode to decomposed form and removes combining marks
	"""
	if not isinstance(string, str):
		string = str(string, "utf-8")
	# Normalize to NFD form and remove all diacritic marks
	string = normalize("NFD", string)
	string = "".join(char for char in string if category(char) != "Mn")
	return string


def unicodify(s, encoding='utf-8', norm=None):
	"""Ensure string is unicode and optionally normalize it"""
	if not isinstance(s, str):
		s = str(s, encoding)
	if norm:
		s = normalize(norm, s)
	return s


def str_encode(text, encoding="utf8"):
	"""Ensure proper string encoding for Python 2/3 compatibility"""
	if not PY3 and isinstance(text, str):
		return text.encode(encoding)
	return text


def getCleanTitle(eventitle=""):
	"""Remove specific formatting markers from titles"""
	return eventitle.replace(' ^`^s', '').replace(' ^`^y', '')


# Character replacement mapping for filename sanitization
CHAR_REPLACEMENTS = {
	"$": "s",
	"&": "and",
	"@": "at",
	"€": "_",
	"£": "_",
	"¢": "_",
	"¥": "_",
	"©": "_",
	"®": "_",
	"™": "_",
	"°": "_",
	"¡": "_",
	"¿": "_",
	"§": "_",
	"¶": "_",
	"•": "_",
	"–": "_",  # En dash
	"—": "_",  # Em dash
	"“": "_",  # Left double quote
	"”": "_",  # Right double quote
	"‘": "_",  # Left single quote
	"’": "_",  # Right single quote
	"«": "_",  # Left-pointing double angle quote
	"»": "_",  # Right-pointing double angle quote
	"/": "_",  # Slash
	# ":": "-",  # Colon
	"*": "_",  # Asterisk
	"?": "_",  # Question mark
	"!": "_",  # Exclamation mark
	"#": "_",  # Hash
	"~": "_",  # Tilde
	"^": "_",  # Caret
	"=": "_",  # Equals
	"(": "_",  # Open parenthesis
	")": "_",  # Close parenthesis
	"[": "_",  # Open bracket
	"]": "_",  # Close bracket
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


def sanitize_filename(name):
	"""
	Sanitize strings to be safe for filenames
	Replaces problematic characters and cleans up formatting
	"""
	while "  " in name:
		name = name.replace("  ", " ")
	# name = name.replace(" ", "")
	# name = sub(r'\s+', '_', name)
	# name = sub(r"[^\w\-.]", "", name)

	name = sub(r"s[0-9]e[0-9]", "", name)

	# Remove invalid filename characters
	invalid_chars = '*?"<>|,'
	for char in invalid_chars:
		name = name.replace(char, '')

	# Clean common prefixes/suffixes
	if name.lower().startswith('live:'):
		name = name.partition(":")[1]
	if name.endswith(',') or name.endswith(':'):
		name = name.replace(",", "")

	name = sub(r'[^\w\s]', ' ', name)

	# Truncate to 50 characters if needed
	if len(name) > 50:
		name = name[:50]
	return name.strip()


convtext_cache = {}


# @lru_cache(maxsize=2500)
def convtext(text):
	try:
		if text is None:
			# print("return None original text:", type(text))
			return None

		if not text or not str(text).strip():
			return None

		if text == '':
			# print('text is an empty string')
			return None

		text = str(text).lower().strip()

		text = remove_accents(text)

		if 'live:' in text:
			text = text.replace('live:', '')

		# Special case substitutions
		substitutions = [

			# Set operations (exact matches)
			("1/2", "mezzo", "replace"),
			("c.s.i.", "csi", "replace"),
			("c.s.i:", "csi", "replace"),
			("c.s.i", "csi", "replace"),
			("n.c.i.s.:", "ncis", "replace"),
			("n.c.i.s.", "ncis", "replace"),
			("ncis:", "ncis", "replace"),
			("ncis - ", "ncis ", "replace"),
			("mission:", "mission", "replace"),
			("ritorno al futuro:", "ritorno al futuro", "replace"),
			("cash or trash chi offre di piu", "cash or trash", "replace"),

			# Replace operations (partial matches)
			("forget the lyrics", "dont forget the lyrics", "set"),
			("superman & lois", "superman e lois", "set"),
			("lois & clark", "superman e lois", "set"),
			("una 44 magnum per", "magnumxx", "set"),
			("john q", "johnq", "set"),
			("il ritorno di colombo", "colombo", "set"),
			("lingo: parole", "lingo", "set"),
			("heartland", "heartland", "set"),
			("io & marilyn", "io e marilyn", "set"),
			("giochi olimpici parigi", "olimpiadi di parigi", "set"),
			("bruno barbieri", "brunobarbierix", "set"),
			("anni '60", "anni 60", "set"),
			("cortesie per gli ospiti", "cortesieospiti", "set"),
			("tg regione", "tg3", "set"),
			("tg1", "tguno", "set"),
			("planet earth", "planet earth", "set"),
			("studio aperto", "studio aperto", "set"),
			("josephine ange gardien", "josephine ange gardien", "set"),
			("josephine angelo", "josephine ange gardien", "set"),
			# Josephine Guardian Angel
			("elementary", "elementary", "set"),
			("squadra speciale cobra 11", "squadra speciale cobra 11", "set"),
			("criminal minds", "criminal minds", "set"),
			("i delitti del barlume", "i delitti del barlume", "set"),
			("senza traccia", "senza traccia", "set"),
			("hudson e rex", "hudson e rex", "set"),
			("ben-hur", "ben-hur", "set"),
			("alessandro borghese - 4 ristoranti", "alessandroborgheseristoranti", "set"),
			("alessandro borghese: 4 ristoranti", "alessandroborgheseristoranti", "set"),
			("amici di maria", "amicimaria", "set"),
			("csi miami", "csi miami", "set"),
			("csi: miami", "csi miami", "set"),
			("csi: scena del crimine", "csi scena del crimine", "set"),
			("csi: new york", "csi new york", "set"),
			("csi: vegas", "csi vegas", "set"),
			("csi: cyber", "csi cyber", "set"),
			("csi: immortality", "csi immortality", "set"),
			("csi: crime scene talks", "csi crime scene talks", "set"),
			("ncis unità anticrimine", "ncis unità anticrimine", "set"),
			("ncis unita anticrimine", "ncis unita anticrimine", "set"),
			("ncis new orleans", "ncis new orleans", "set"),
			("ncis los angeles", "ncis los angeles", "set"),
			("ncis origins", "ncis origins", "set"),
			("ncis hawai", "ncis hawai", "set"),
			("ncis sydney", "ncis sydney", "set"),
			("ritorno al futuro - parte iii", "ritornoalfuturoparteiii", "set"),
			("ritorno al futuro - parte ii", "ritornoalfuturoparteii", "set"),
			("walker, texas ranger", "walker texas ranger", "set"),
			("e.r.", "ermediciinprimalinea", "set"),
			("alexa: vita da detective", "alexa vita da detective", "set"),
			("delitti in paradiso", "delitti in paradiso", "set"),
			("modern family", "modern family", "set"),
			("shaun: vita da pecora", "shaun", "set"),
			("calimero", "calimero", "set"),
			("i puffi", "i puffi", "set"),
			("stuart little", "stuart little", "set"),
			("gf daily", "grande fratello", "set"),
			("grande fratello", "grande fratello", "set"),
			("castle", "castle", "set"),
			("seal team", "seal team", "set"),
			("fast forward", "fast forward", "set"),
			("un posto al sole", "un posto al sole", "set"),
			("cash or trash chi offre di piu", "cash or trash", "set"),
		]

		for pattern, replacement, method in substitutions:
			if method == "replace":
				text = text.replace(pattern, replacement)
				break

			if method == "set" and pattern in text:
				text = replacement
				break

		# Split on separators
		for separator in [" -", "(", "[", "|"]:  # , ":"]:
			if separator in text:
				text = text.split(separator)[0].strip()

		# Replace characters based on the custom map
		for char, replacement in CHAR_REPLACEMENTS.items():
			text = text.replace(char, replacement)

		# Remove unwanted strings
		unwanted = [
			"\xe2\x80\x93", "\xc2\x86", "\xc2\x87", "webhdtv", "1080i", "dvdr5", "((", "))", "hdtvrip",
			"german", "english", "ws", "ituneshd", "hdtv", "dvdrip", "unrated", "retail", "web-dl", "divx",
			"bdrip", "uncut", "avc", "ac3d", "ts", "ac3md", "ac3", "webhdtvrip", "xvid", "bluray",
			"complete", "internal", "dtsd", "h264", "dvdscr", "dubbed", "line.dubbed", "dd51", "dvdr9",
			"sync", "webhdrip", "webrip", "repack", "dts", "webhd", "1^tv", "1^ tv", " - prima tv",
			" - primatv", "primatv", "en direct:", "first screening", "live:", "1^ visione rai",
			"1^ visione", "premiere:", "nouveau:", "prima visione", "film -", "en vivo:",
			"nueva emisión:", "new:", "film:", "première diffusion", "estreno:", "fhd", "hd", "4k", "uhd",
			" ep", " episodio", " st", " stag", " odc", " parte", " pt!series", " serie",
		]
		for item in unwanted:
			if item in text:
				text = text.split(item)[0].strip()

		text = sub(r'\d+[\s]*[a-z°\^]?[\s]*puntata.*', '', text, flags=IGNORECASE)

		text = getCleanTitle(text)
		# Remove invalid suffixes
		bad_suffixes = [
			" al", " ar", " ba", " da", " de", " en", " es", " eu", " ex-yu", " fi",
			" fr", " gr", " hr", " mk", " nl", " no", " pl", " pt", " ro", " rs",
			" ru", " si", " swe", " sw", " tr", " uk", " yu",  " it"
		]

		for suffix in bad_suffixes:
			if text.endswith(suffix):
				text = text[:-len(suffix)].strip()

		# Replace special characters
		for char in [".", "_", "'"]:
			text = text.replace(char, " ")

		# Final replacements
		final_replacements = {
			"XXXXXX": "60",
			"magnumxx": "una 44 magnum per l ispettore",
			"amicimaria": "amici di maria",
			"alessandroborgheseristoranti": "alessandro borghese - 4 ristoranti",
			"brunobarbierix": "bruno barbieri - 4 hotel",
			"johnq": "john q",
			"il ritorno di colombo": "colombo",
			"cortesieospiti": "cortesie per gli ospiti",
			"ermediciinprimalinea": "er medici in prima linea",
			"ritornoalfuturoparteiii": "ritorno al futuro parte iii",
			"ritornoalfuturoparteii": "ritorno al futuro parte ii",
			"tguno": "tg1"
		}

		for old, new in final_replacements.items():
			text = text.replace(old, new)

		text = sanitize_filename(text)
		text = sub(r"-+", "-", text)

		text = text.strip()

		# Store in cache
		text = sub(r'\s+', ' ', text).strip()
		capitalized_text = text.capitalize()
		if DEBUG:
			print("convtext capitalized safe:", capitalized_text)

		# Store in cache
		"""
		# if capitalized_text not in convtext_cache:
			# convtext_cache[capitalized_text] = capitalized_text  # Salva la versione capitalizzata
			# print(f"Adding to cache: {text} -> {capitalized_text}")  # Debug print
		# else:
			# print(f"Found in cache: {capitalized_text}")  # Debug print
		# Return the capitalized value from the cache
		# print(convtext.cache_info())  # Mostra hit/miss
		# return convtext_cache[capitalized_text]
		"""
		return capitalized_text

	except Exception as e:
		print("Error in convert_text:", str(e))
		return None
