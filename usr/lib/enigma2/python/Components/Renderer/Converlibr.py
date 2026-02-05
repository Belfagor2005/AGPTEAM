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

from re import sub, S, I, search, escape, compile, DOTALL
import sys
from unicodedata import normalize, category


try:
	unicode
except NameError:
	unicode = str


PY3 = sys.version_info[0] >= 3
if not PY3:
	import html
	html_parser = html
	from urllib.parse import quote_plus
else:
	from urllib import quote_plus
	from HTMLParser import HTMLParser
	html_parser = HTMLParser()


def quoteEventName(eventName, safe="+"):
	"""
	Quote and clean event names for URL encoding
	Handles special characters and encoding issues
	:param eventName: Stringa da codificare
	:param safe: Caratteri da mantenere non codificati (default: "+")
	:return: Stringa codificata URL-safe
	"""
	try:
		text = eventName.decode('utf8').replace(u'\x86', u'').replace(u'\x87', u'').encode('utf8')
	except BaseException:
		text = eventName
	return quote_plus(text, safe=safe)


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


def cutName(eventName=""):
	if eventName:
		eventName = eventName.replace('"', '').replace('Х/Ф', '').replace('М/Ф', '').replace('Х/ф', '')  # .replace('.', '').replace(' | ', '')
		eventName = eventName.replace('(18+)', '').replace('18+', '').replace('(16+)', '').replace('16+', '').replace('(12+)', '')
		eventName = eventName.replace('12+', '').replace('(7+)', '').replace('7+', '').replace('(6+)', '').replace('6+', '')
		eventName = eventName.replace('(0+)', '').replace('0+', '').replace('+', '')
		eventName = eventName.replace('المسلسل العربي', '')
		eventName = eventName.replace('مسلسل', '')
		eventName = eventName.replace('برنامج', '')
		eventName = eventName.replace('فيلم وثائقى', '')
		eventName = eventName.replace('حفل', '')
		return eventName
	return ""


def getCleanTitle(eventitle=""):
	# save_name = sub('\\(\d+\)$', '', eventitle)
	# save_name = sub('\\(\d+\/\d+\)$', '', save_name)  # remove episode-number " (xx/xx)" at the end
	# # save_name = sub('\ |\?|\.|\,|\!|\/|\;|\:|\@|\&|\'|\-|\"|\%|\(|\)|\[|\]\#|\+', '', save_name)
	save_name = eventitle.replace(' ^`^s', '').replace(' ^`^y', '')
	return save_name


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


def sanitize_filename(filename):
	# Replace spaces with underscores and remove invalid characters (like ':')
	sanitized = sub(r'[^\w\s-]', '', filename)  # Remove invalid characters
	# sanitized = sanitized.replace(' ', '_')      # Replace spaces with underscores
	# sanitized = sanitized.replace('-', '_')      # Replace dashes with underscores
	return sanitized.strip()


def convtext(text=''):
	try:
		if text is None:
			print("return None original text:", type(text))
			return None
		if text == '':
			print('text is an empty string')
			return None
		else:
			# if isinstance(text, unicode):  # Se è una stringa Unicode in Python 2
			text = str(text)  # Converti in una stringa di byte (str in Python 2)
			# print('original text:', text)
			# Converti tutto in minuscolo
			text = text.lower().rstrip()
			text = text.replace(':', '-')

			text = remove_accents(text)
			"""
			# Replace characters based on the custom map
			for char, replacement in CHAR_REPLACEMENTS.items():
				text = text.replace(char, replacement)
			"""
			# Mappatura sostituzioni con azione specifica
			sostituzioni = [
				# set
				('superman & lois', 'superman e lois', 'set'),
				('lois & clark', 'superman e lois', 'set'),
				("una 44 magnum per", 'magnumxx', 'set'),
				('john q', 'johnq', 'set'),
				# replace
				('1/2', 'mezzo', 'replace'),
				('c.s.i.', 'csi', 'replace'),
				('c.s.i:', 'csi', 'replace'),
				('ncis:', 'ncis', 'replace'),
				('ritorno al futuro:', 'ritorno al futuro', 'replace'),
				('law & order', 'law e order:', 'replace'),

				# set
				('il ritorno di colombo', 'colombo', 'set'),
				('lingo: parole', 'lingo', 'set'),
				('heartland', 'heartland', 'set'),
				('io & marilyn', 'io e marilyn', 'set'),
				('giochi olimpici parigi', 'olimpiadi di parigi', 'set'),
				('bruno barbieri', 'brunobarbierix', 'set'),
				("anni '60", 'anni 60', 'set'),
				('cortesie per gli ospiti', 'cortesieospiti', 'set'),
				('tg regione', 'tg3', 'set'),
				('tg1', 'tguno', 'set'),
				('planet earth', 'planet earth', 'set'),
				('studio aperto', 'studio aperto', 'set'),
				('josephine ange gardien', 'josephine ange gardien', 'set'),
				('josephine angelo', 'josephine ange gardien', 'set'),
				('elementary', 'elementary', 'set'),
				('squadra speciale cobra 11', 'squadra speciale cobra 11', 'set'),
				('criminal minds', 'criminal minds', 'set'),
				('i delitti del barlume', 'i delitti del barlume', 'set'),
				('senza traccia', 'senza traccia', 'set'),
				('hudson e rex', 'hudson e rex', 'set'),
				('ben-hur', 'ben-hur', 'set'),
				('alessandro borghese - 4 ristoranti', 'alessandroborgheseristoranti', 'set'),
				('alessandro borghese: 4 ristoranti', 'alessandroborgheseristoranti', 'set'),
				('amici di maria', 'amicimaria', 'set'),

				('csi miami', 'csi miami', 'set'),
				('csi: miami', 'csi miami', 'set'),
				('csi: scena del crimine', 'csi scena del crimine', 'set'),
				('csi: new york', 'csi new york', 'set'),
				('csi: vegas', 'csi vegas', 'set'),
				('csi: cyber', 'csi cyber', 'set'),
				('csi: immortality', 'csi immortality', 'set'),
				('csi: crime scene talks', 'csi crime scene talks', 'set'),

				('ncis unità anticrimine', 'ncis unità anticrimine', 'set'),
				('ncis unita anticrimine', 'ncis unita anticrimine', 'set'),
				('ncis new orleans', 'ncis new orleans', 'set'),
				('ncis los angeles', 'ncis los angeles', 'set'),
				('ncis origins', 'ncis origins', 'set'),
				('ncis hawai', 'ncis hawai', 'set'),
				('ncis sydney', 'ncis sydney', 'set'),

				('ritorno al futuro - parte iii', 'ritornoalfuturoparteiii', 'set'),
				('ritorno al futuro - parte ii', 'ritornoalfuturoparteii', 'set'),
				('walker, texas ranger', 'walker texas ranger', 'set'),
				('e.r.', 'ermediciinprimalinea', 'set'),
				('alexa: vita da detective', 'alexa vita da detective', 'set'),
				('delitti in paradiso', 'delitti in paradiso', 'set'),
				('modern family', 'modern family', 'set'),
				('shaun: vita da pecora', 'shaun', 'set'),
				('calimero', 'calimero', 'set'),
				('i puffi', 'i puffi', 'set'),
				('stuart little', 'stuart little', 'set'),
				('gf daily', 'grande fratello', 'set'),
				('grande fratello', 'grande fratello', 'set'),
				('castle', 'castle', 'set'),
				('seal team', 'seal team', 'set'),
				('fast forward', 'fast forward', 'set'),
				('un posto al sole', 'un posto al sole', 'set'),
			]

			# Applicazione delle sostituzioni
			for parola, sostituto, metodo in sostituzioni:
				if parola in text:
					if metodo == 'set':
						text = sostituto
						break
					elif metodo == 'replace':
						text = text.replace(parola, sostituto)

			# Applica le funzioni di taglio e pulizia del titolo
			text = cutName(text)
			text = getCleanTitle(text)

			# Regola il titolo se finisce con "the"
			if text.endswith("the"):
				text = "the " + text[:-4]

			# Sostituisci caratteri speciali con stringhe vuote
			text = text.replace("\xe2\x80\x93", "").replace('\xc2\x86', '').replace('\xc2\x87', '').replace('webhdtv', '')
			text = text.replace('1080i', '').replace('dvdr5', '').replace('((', '(').replace('))', ')') .replace('hdtvrip', '')
			text = text.replace('german', '').replace('english', '').replace('ws', '').replace('ituneshd', '').replace('hdtv', '')
			text = text.replace('dvdrip', '').replace('unrated', '').replace('retail', '').replace('web-dl', '').replace('divx', '')
			text = text.replace('bdrip', '').replace('uncut', '').replace('avc', '').replace('ac3d', '').replace('ts', '')
			text = text.replace('ac3md', '').replace('ac3', '').replace('webhdtvrip', '').replace('xvid', '').replace('bluray', '')
			text = text.replace('complete', '').replace('internal', '').replace('dtsd', '').replace('h264', '').replace('dvdscr', '')
			text = text.replace('dubbed', '').replace('line.dubbed', '').replace('dd51', '').replace('dvdr9', '').replace('sync', '')
			text = text.replace('webhdrip', '').replace('webrip', '').replace('repack', '').replace('dts', '').replace('webhd', '')
			# set add
			text = text.replace('1^tv', '').replace('1^ tv', '').replace(' - prima tv', '').replace(' - primatv', '')
			text = text.replace('primatv', '').replace('en direct:', '').replace('first screening', '').replace('live:', '')
			text = text.replace('1^ visione rai', '').replace('1^ visione', '').replace('premiere:', '').replace('nouveau:', '')
			text = text.replace('prima visione', '').replace('film -', '').replace('en vivo:', '').replace('nueva emisión:', '')
			text = text.replace('new:', '').replace('film:', '').replace('première diffusion', '').replace('estreno:', '')
			print('cutlist:', text)

			# Rimuovi accenti
			text = remove_accents(text)
			# print('remove_accents text:', text)

			# remove episode number from series, like "series"
			regex = compile(r'^(.*?)([ ._-]*(ep|episodio|st|stag|odc|parte|pt!series|serie||s[0-9]{1,2}e[0-9]{1,2}|[0-9]{1,2}x[0-9]{1,2})[ ._-]*[.]?[ ._-]*[0-9]+.*)$')
			text = sub(regex, r'\1', text).strip()
			print("titolo_pulito:", text)
			# Force and remove episode number from series, like "series"
			if search(r'[Ss][0-9]+[Ee][0-9]+', text):
				text = sub(r'[Ss][0-9]+[Ee][0-9]+.*[a-zA-Z0-9_]+', '', text, flags=S | I)
			text = sub(r'\(.*\)', '', text).rstrip()  # remove episode number from series, like "series"

			# Rimozione pattern specifici
			text = sub(r'^\w{2}:', '', text)  # Rimuove "xx:" all'inizio
			text = sub(r'^\w{2}\|\w{2}\s', '', text)  # Rimuove "xx|xx" all'inizio
			text = sub(r'^.{2}\+? ?- ?', '', text)  # Rimuove "xx -" all'inizio
			text = sub(r'^\|\|.*?\|\|', '', text)  # Rimuove contenuti tra "||"
			text = sub(r'^\|.*?\|', '', text)  # Rimuove contenuti tra "|"
			text = sub(r'\|.*?\|', '', text)  # Rimuove qualsiasi altro contenuto tra "|"
			text = sub(r'\(\(.*?\)\)|\(.*?\)', '', text)  # Rimuove contenuti tra "()"
			text = sub(r'\[\[.*?\]\]|\[.*?\]', '', text)  # Rimuove contenuti tra "[]"

			text = sub(r'[^\w\s]+$', '', text)

			text = sub(r' +ح| +ج| +م', '', text)  # Rimuove numeri di episodi/serie in arabo
			# Rimozione di stringhe non valide
			bad_strings = [
				"ae|", "al|", "ar|", "at|", "ba|", "be|", "bg|", "br|", "cg|", "ch|", "cz|", "da|", "de|", "dk|",
				"ee|", "en|", "es|", "eu|", "ex-yu|", "fi|", "fr|", "gr|", "hr|", "hu|", "in|", "ir|", "it|", "lt|",
				"mk|", "mx|", "nl|", "no|", "pl|", "pt|", "ro|", "rs|", "ru|", "se|", "si|", "sk|", "sp|", "tr|",
				"uk|", "us|", "yu|",
				"1080p", "4k", "720p", "hdrip", "hindi", "imdb", "vod", "x264"
			]

			bad_strings.extend(map(str, range(1900, 2030)))  # Anni da 1900 a 2030
			bad_strings_pattern = compile('|'.join(map(escape, bad_strings)))
			text = bad_strings_pattern.sub('', text)
			# Rimozione suffissi non validi
			bad_suffix = [
				" al", " ar", " ba", " da", " de", " en", " es", " eu", " ex-yu", " fi", " fr", " gr", " hr", " mk",
				" nl", " no", " pl", " pt", " ro", " rs", " ru", " si", " swe", " sw", " tr", " uk", " yu"
			]
			bad_suffix_pattern = compile(r'(' + '|'.join(map(escape, bad_suffix)) + r')$')
			text = bad_suffix_pattern.sub('', text)
			# Rimuovi "." "_" "'" e sostituiscili con spazi
			text = sub(r'[._\']', ' ', text)
			# Rimuove tutto dopo i ":" (incluso ":")
			text = sub(r':.*$', '', text)
			# Pulizia finale
			text = text.partition("(")[0]  # Rimuove contenuti dopo "("
			# text = text.partition(":")[0]
			# text = text + 'FIN'
			# text = sub(r'(odc.\s\d+)+.*?FIN', '', text)
			# text = sub(r'(odc.\d+)+.*?FIN', '', text)
			# text = sub(r'(\d+)+.*?FIN', '', text)
			# text = sub('FIN', '', text)

			text = text.partition(" -")[0]  # Rimuove contenuti dopo "-"
			text = text.strip(' -')
			# Forzature finali
			text = text.replace('XXXXXX', '60')
			text = text.replace('magnumxx', "una 44 magnum per l ispettore")
			text = text.replace('amicimaria', 'amici di maria')
			text = text.replace('alessandroborgheseristoranti', 'alessandro borghese - 4 ristoranti')
			text = text.replace('brunobarbierix', 'bruno barbieri - 4 hotel')
			text = text.replace('johnq', 'john q')
			text = text.replace('il ritorno di colombo', 'colombo')
			text = text.replace('cortesieospiti', 'cortesie per gli ospiti')
			text = text.replace('ermediciinprimalinea', 'er medici in prima linea')
			text = text.replace('ritornoalfuturoparteiii', 'ritorno al futuro parte iii')
			text = text.replace('ritornoalfuturoparteii', 'ritorno al futuro parte ii')
			text = text.replace('tguno', 'tg1')

			if text.startswith('live:'):
				text = text.partition(":")[1]

			# for char, replacement in CHAR_REPLACEMENTS.items():
				# text = text.replace(char, replacement)

			# text = quote(text, safe="")
			# text = unquote(text)
			print('text safe:', text)

		return text.capitalize()
	except Exception as e:
		print('convtext error:', e)
		return None
