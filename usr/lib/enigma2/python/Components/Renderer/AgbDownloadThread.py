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
from os import remove
from os.path import exists
from re import compile, findall, DOTALL, search, sub
from threading import Thread
from json import loads
from random import choice
from unicodedata import normalize

# Third-party libraries
from PIL import Image
from requests import get, codes, Session  # , exceptions
from requests.exceptions import RequestException
from requests.adapters import HTTPAdapter, Retry
from twisted.internet.reactor import callInThread

# Enigma2 specific
from enigma import getDesktop
from Components.config import config

# Local imports
from .Agp_lib import PY3, quoteEventName
from .Agp_apikeys import tmdb_api, thetvdb_api, fanart_api  # , omdb_api
from .Agp_Utils import logger

try:
	from http.client import HTTPConnection
	HTTPConnection.debuglevel = 0
except ImportError:
	from httplib import HTTPConnection
	HTTPConnection.debuglevel = 0


global my_cur_skin, srch

try:
	lng = config.osd.language.value
	lng = lng[:-3]
except:
	lng = 'en'
	pass


def getRandomUserAgent():
	useragents = [
		'Mozilla/5.0 (compatible; Konqueror/4.5; FreeBSD) KHTML/4.5.4 (like Gecko)',
		'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.67 Safari/537.36',
		'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:29.0) Gecko/20120101 Firefox/29.0',
		'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:33.0) Gecko/20100101 Firefox/33.0',
		'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:35.0) Gecko/20120101 Firefox/35.0',
		'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0',
		'Mozilla/5.0 (X11; Linux x86_64; rv:28.0) Gecko/20100101 Firefox/28.0',
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.13+ (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2',
		'Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; de) Presto/2.9.168 Version/11.52',
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'
	]
	return choice(useragents)


AGENTS = [
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
	"Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0",
	"Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edge/87.0.664.75",
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363"
]


isz = "300,450"
screenwidth = getDesktop(0).size()
if screenwidth.width() <= 1280:
	isz = isz.replace(isz, "300,450")
elif screenwidth.width() <= 1920:
	isz = isz.replace(isz, "780,1170")
else:
	isz = isz.replace(isz, "1280,1920")


"""
🖼️ Poster:
"w92", "w154", "w185", "w342", "w500", "w780", "original"

🖼️ Backdrop:
"w300", "w780", "w1280", "original"

🧑‍🎤 Profile:
"w45", "w185", "h632", "original"

📺 Still (frame episodio):
"w92", "w185", "w300", "original"

🏷️ Logo:
"w45", "w92", "w154", "w185", "w300", "w500", "original"

📐 Consigli sulle dimensioni (in pixel)
Tipo	          Dimensioni consigliate	Aspetto
Poster	            500x750 → 2000x3000	    1.5 (2:3)
Poster TV Season	400x578 → 2000x3000 	1.5 (2:3)
Backdrop	        1280x720 → 3840x2160	1.777 (16:9)
Still (episodio)	400x225 → 3840x2160	    1.777 (16:9)
Profile	            300x450 → 2000x3000	    1.5 (2:3)
Logo PNG	        500x1 → 2000x2000	    Variabile
Logo SVG	        500x1 → vettoriale	    Variabile
"""


class AgbDownloadThread(Thread):
	def __init__(self):
		Thread.__init__(self)
		self.checkMovie = [
			"film", "movie", "фильм", "кино", "ταινία",
			"película", "cinéma", "cine", "cinema", "filma"
		]
		self.checkTV = [
			"serial", "series", "serie", "serien", "série", "séries",
			"serious", "folge", "episodio", "episode", "épisode",
			"l'épisode", "ep.", "animation", "staffel", "soap", "doku",
			"tv", "talk", "show", "news", "factual", "entertainment",
			"telenovela", "dokumentation", "dokutainment", "documentary",
			"informercial", "information", "sitcom", "reality", "program",
			"magazine", "mittagsmagazin", "т/с", "м/с", "сезон", "с-н",
			"эпизод", "сериал", "серия", "actualité", "discussion",
			"interview", "débat", "émission", "divertissement", "jeu",
			"magasine", "information", "météo", "journal", "sport",
			"culture", "infos", "feuilleton", "téléréalité", "société",
			"clips", "concert", "santé", "éducation", "variété"
		]

	def search_tmdb(self, dwn_backdrop, title, shortdesc, fulldesc, channel=None):
		try:
			self.dwn_backdrop = dwn_backdrop
			self.title_safe = title.replace("+", " ")
			url = "https://api.themoviedb.org/3/search/multi?api_key={}&language={}&query={}".format(
				tmdb_api, lng, self.title_safe
			)
			retries = Retry(total=1, backoff_factor=1)
			adapter = HTTPAdapter(max_retries=retries)
			http = Session()
			http.mount("http://", adapter)
			http.mount("https://", adapter)
			headers = {"User-Agent": choice(AGENTS)}

			response = http.get(url, headers=headers, timeout=(10, 20), verify=False)
			response.raise_for_status()

			if response.status_code == codes.ok:
				try:
					data = response.json()
					return self.downloadData2(data)
				except ValueError as e:
					logger.error("TMDb response decode error: " + str(e))
					return False, "Errore nel parsing della risposta TMDb"
			else:
				return False, "Errore durante la richiesta a TMDb: {}".format(response.status_code)
		except Exception as e:
			logger.error("TMDb search error: " + str(e))
			return False, "Errore durante la ricerca su TMDb"

	def downloadData2(self, data):
		if not isinstance(data, dict):
			try:
				data = loads(data)
			except Exception as e:
				logger.error("JSON decoding error: " + str(e))
				return False, "[ERROR : tmdb] Invalid JSON"

		results = data.get("results", [])
		if not results:
			return False, "[SKIP : tmdb] Nessun risultato trovato"

		try:
			for each in results:
				media_type = each.get("media_type", "")
				if media_type == "tv":
					media_type = "serie"

				if media_type in ["serie", "movie"]:
					title = each.get("name") or each.get("title", "")
					year = ""

					if media_type == "movie":
						year = each.get("release_date", "").split("-")[0]
					elif media_type == "serie":
						year = each.get("first_air_date", "").split("-")[0]

					backdrop_path = each.get("backdrop_path")
					poster_path = each.get("poster_path")

					backdrop = "http://image.tmdb.org/t/p/original" + backdrop_path if backdrop_path else ""
					poster = "http://image.tmdb.org/t/p/original" + poster_path if poster_path else ""

					rating = str(each.get("vote_average", 0))
					show_title = "{} ({})".format(title, year) if year else title

					if backdrop:
						callInThread(self.saveBackdrop, backdrop, self.dwn_backdrop)
						msg = "[SUCCESS poster: tmdb] title {} [poster{}-backdrop{}] => year{} => rating{} => showtitle{}".format(
							title, poster, backdrop, year, rating, show_title
						)
						# logger.info("TMDb match: " + msg)
						return True, msg
			return False, "[SKIP : tmdb] Nessun film o serie valida"
		except Exception as e:
			logger.error("TMDb parsing error: " + str(e))
			if exists(self.dwn_backdrop):
				remove(self.dwn_backdrop)
			return False, "[ERROR : tmdb]"

	def search_tvdb(self, dwn_backdrop, title, shortdesc, fulldesc, channel=None):
		try:
			self.dwn_backdrop = dwn_backdrop
			series_nb = -1
			chkType, fd = self.checkType(shortdesc, fulldesc)
			title_safe = title
			self.title_safe = title_safe.replace('+', ' ')
			year = findall(r'19\d{2}|20\d{2}', fd)
			if len(year) > 0:
				year = year[0]
			else:
				year = ''
			url_tvdbg = "https://thetvdb.com/api/GetSeries.php?seriesname={}".format(self.title_safe)
			url_read = get(url_tvdbg).text
			series_id = findall(r'<seriesid>(.*?)</seriesid>', url_read)
			series_name = findall(r'<SeriesName>(.*?)</SeriesName>', url_read)
			series_year = findall(r'<FirstAired>(19\d{2}|20\d{2})-\d{2}-\d{2}</FirstAired>', url_read)
			'''
			# series_banners = findall(r'<banner>(.*?)</banner>', url_read)
			# if series_banners:
				# series_banners = 'https://thetvdb.com' + series_banners
			'''
			i = 0
			for iseries_year in series_year:
				if year == '':
					series_nb = 0
					break
				elif year == iseries_year:
					series_nb = i
					break
				i += 1
			backdrop = None
			if series_nb >= 0 and series_id and series_id[series_nb]:
				if series_name and series_name[series_nb]:
					series_name = self.UNAC(series_name[series_nb])
				else:
					series_name = ''
				if self.PMATCH(self.title_safe, series_name):
					url_tvdb = "https://thetvdb.com/api/{}/series/{}".format(thetvdb_api, series_id[series_nb])
					if lng:
						url_tvdb += "/{}".format(lng)
					else:
						url_tvdb += "/en"
					url_read = get(url_tvdb).text
					backdrop = findall(r'<backdrop>(.*?)</backdrop>', url_read)
					url_backdrop = "https://artworks.thetvdb.com/banners/{}".format(backdrop[0])
					if backdrop and backdrop[0]:
						callInThread(self.saveBackdrop, url_backdrop, dwn_backdrop)
						# if exists(dwn_backdrop):
						return True, "[SUCCESS backdrop: tvdb] {} [{}-{}] => {} => {} => {}".format(title, chkType, year, url_tvdbg, url_tvdb, url_backdrop)
					return False, "[SKIP : tvdb] {} [{}-{}] => {} (Not found)".format(self.title_safe, chkType, year, url_tvdbg)
			else:
				return False, "[SKIP : tvdb] {} [{}-{}] => {} (Not found)".format(self.title_safe, chkType, year, url_tvdbg)

		except Exception as e:
			if exists(dwn_backdrop):
				remove(dwn_backdrop)
			return False, "[ERROR : tvdb] {} => {} ({})".format(title, url_tvdbg, str(e))

	def search_fanart(self, dwn_backdrop, title, shortdesc, fulldesc, channel=None):
		try:
			year = ""
			url_maze = ""
			url_fanart = ""
			# url_backdrop = ""
			tvmaze_id = "-"
			self.title_safe = title.replace("+", " ")
			chkType, fd = self.checkType(shortdesc, fulldesc)

			# Estrazione dell'anno se presente
			try:
				matches = findall(r"19\d{2}|20\d{2}", fd)
				if matches:
					year = matches[1] if len(matches) > 1 else matches[0]
			except Exception:
				pass

			# Recupero ID TVMaze
			try:
				url_maze = "http://api.tvmaze.com/singlesearch/shows?q={}".format(self.title_safe)
				resp = get(url_maze, timeout=5)
				resp.raise_for_status()
				mj = resp.json()
				tvmaze_id = mj.get("externals", {}).get("thetvdb", "-")
			except Exception as err:
				logger.error("TVMaze error: " + str(err))

			# Fanart.tv
			try:
				m_type = "tv"
				url_fanart = "https://webservice.fanart.tv/v3/{}/{}?api_key={}".format(m_type, tvmaze_id, fanart_api)
				fanart_resp = get(url_fanart, verify=False, timeout=5)
				fanart_resp.raise_for_status()
				fjs = fanart_resp.json()

				url = ""
				if "showbackground" in fjs and fjs["showbackground"]:
					url = fjs["showbackground"][0]["url"]
				elif "moviebackground" in fjs and fjs["moviebackground"]:
					url = fjs["moviebackground"][0]["url"]

				if url:
					callInThread(self.saveBackdrop, url, dwn_backdrop)
					msg = "[SUCCESS backdrop: fanart] {} [{}-{}] => {} => {} => {}".format(
						self.title_safe, chkType, year, url_maze, url_fanart, url
					)
					# logger.info("Fanart match: " + msg)
					return True, msg
				else:
					return False, "[SKIP : fanart] {} [{}-{}] => {} (Not found)".format(self.title_safe, chkType, year, url_maze)
			except Exception as e:
				# logger.error("Fanart API error: " + str(e))
				return False, "[ERROR : fanart] {} [{}-{}] => {} ({})".format(self.title_safe, chkType, year, url_maze, str(e))

		except Exception as e:
			# logger.error("Unhandled error in search_fanart: " + str(e))
			if exists(dwn_backdrop):
				remove(dwn_backdrop)
			return False, "[ERROR : fanart] {} => {} ({})".format(self.title_safe, url_maze, str(e))

	def search_imdb(self, dwn_backdrop, title, shortdesc, fulldesc, channel=None):
		try:
			self.dwn_backdrop = dwn_backdrop
			self.title_safe = title.replace("+", " ")
			chkType, fd = self.checkType(shortdesc, fulldesc)

			# Try to extract AKA title
			aka_list = findall(r"\((.*?)\)", fd)
			aka = next((a for a in aka_list if not a.isdigit()), None)
			paka = self.UNAC(aka) if aka else ""

			# Extract year
			year_matches = findall(r"19\d{2}|20\d{2}", fd)
			year = year_matches[0] if year_matches else ""

			imsg = ""
			url_mimdb = ""
			url_backdrop = ""
			url_imdb = []

			# Build IMDb search URL
			if aka and aka != self.title_safe:
				url_mimdb = "https://m.imdb.com/find?q={}%20({})".format(self.title_safe, quoteEventName(aka))
			else:
				url_mimdb = "https://m.imdb.com/find?q={}".format(self.title_safe)

			url_read = get(url_mimdb).text
			rc = compile(r'<img src="(.*?)".*?<span class="h3">\n(.*?)\n</span>.*?\((\d+)\)(\s\(.*?\))?(.*?)</a>', DOTALL)
			url_imdb = rc.findall(url_read)

			# Retry without AKA if not found
			if not url_imdb and aka:
				url_mimdb = "https://m.imdb.com/find?q={}".format(self.title_safe)
				url_read = get(url_mimdb).text
				url_imdb = rc.findall(url_read)

			len_imdb = len(url_imdb)
			idx_imdb = 0
			pfound = False

			for imdb in url_imdb:
				imdb = list(imdb)
				imdb[1] = self.UNAC(imdb[1])  # Title
				tmp = findall(r'aka <i>"(.*?)"</i>', imdb[4])
				imdb[4] = self.UNAC(tmp[0]) if tmp else self.UNAC(imdb[4])  # AKA

				# Extract image URL
				backdrop_match = search(r"(.*?)._V1_.*?.jpg", imdb[0])
				if not backdrop_match:
					continue

				imdb_year = imdb[2]
				imdb_title = imdb[1]
				imdb_aka = imdb[4]
				base_url = backdrop_match.group(1)
				url_backdrop = "{}._V1_UY278,1,185,278_AL_.jpg".format(base_url)

				# Compare by year and title similarity
				if imdb[3] == "":
					# Exact year match
					if year and year == imdb_year:
						imsg = "Found title: '{}', aka: '{}', year: '{}'".format(imdb_title, imdb_aka, imdb_year)
						if self.PMATCH(self.title_safe, imdb_title) or self.PMATCH(self.title_safe, imdb_aka) or self.PMATCH(paka, imdb_title) or self.PMATCH(paka, imdb_aka):
							pfound = True
							break
					# Tolerate ±1 year
					elif year and (int(year) - 1 == int(imdb_year) or int(year) + 1 == int(imdb_year)):
						imsg = "Found title: '{}', aka: '{}', year: '+/-{}'".format(imdb_title, imdb_aka, imdb_year)
						if self.title_safe == imdb_title or self.title_safe == imdb_aka or paka == imdb_title or paka == imdb_aka:
							pfound = True
							break
					# No year available
					elif not year:
						imsg = "Found title: '{}', aka: '{}', year: ''".format(imdb_title, imdb_aka)
						if self.title_safe == imdb_title or self.title_safe == imdb_aka or paka == imdb_title or paka == imdb_aka:
							pfound = True
							break
				idx_imdb += 1

			if url_backdrop and pfound:
				callInThread(self.saveBackdrop, url_backdrop, dwn_backdrop)
				msg = "[SUCCESS url_backdrop: imdb] {} [{}-{}] => {} [{}/{}] => {} => {}".format(
					self.title_safe, chkType, year, imsg, idx_imdb, len_imdb, url_mimdb, url_backdrop
				)
				# _log(msg)
				return True, msg

			return False, "[SKIP : imdb] {} [{}-{}] => {} (No Entry found [{}])".format(self.title_safe, chkType, year, url_mimdb, len_imdb)

		except Exception as e:
			if exists(dwn_backdrop):
				remove(dwn_backdrop)
			return False, "[ERROR : imdb] {} [{}-{}] => {} ({})".format(self.title_safe, chkType, year, url_mimdb, str(e))

	def search_programmetv_google(self, dwn_backdrop, title, shortdesc, fulldesc, channel=None):
		try:
			self.dwn_backdrop = dwn_backdrop
			url_ptv = ''
			headers = {"User-Agent": choice(AGENTS)}
			chkType, fd = self.checkType(shortdesc, fulldesc)

			if chkType.startswith("movie"):
				return False, "[SKIP : programmetv-google] {} [{}] => Skip movie title".format(title, chkType)

			title_safe = title
			self.title_safe = title_safe.replace('+', ' ')
			url_ptv = "site:programme-tv.net+" + self.title_safe

			if channel and self.title_safe.find(channel.split()[0]) < 0:
				url_ptv += "+" + quoteEventName(channel)

			url_ptv = "https://www.google.com/search?q={}&tbm=isch&tbs=ift:jpg%2Cisz:m".format(url_ptv)
			ff = get(url_ptv, stream=True, headers=headers, cookies={'CONSENT': 'YES+'}).text

			if not PY3:
				ff = ff.encode('utf-8')

			ptv_id = 0
			plst = findall(r'\],\["https://www.programme-tv.net(.*?)",\d+,\d+]', ff)

			for backdroplst in plst:
				ptv_id += 1
				url_backdrop = "https://www.programme-tv.net{}".format(backdroplst)
				url_backdrop = sub(r"\\u003d", "=", url_backdrop)
				url_backdrop_size = findall(r'([\d]+)x([\d]+).*?([\w\.-]+).jpg', url_backdrop)

				if url_backdrop_size and url_backdrop_size[0]:
					get_title = self.UNAC(url_backdrop_size[0][2].replace('-', ''))
					if self.title_safe == get_title:
						# Use fixed target height
						h_tar = 278.0
						h_ori = float(url_backdrop_size[0][1])
						ratio = h_ori / h_tar
						w_ori = float(url_backdrop_size[0][0])
						w_tar = int(w_ori / ratio)
						h_tar = int(h_tar)

						url_backdrop = sub(r'/\d+x\d+/', "/" + str(w_tar) + "x" + str(h_tar) + "/", url_backdrop)
						url_backdrop = sub(r'crop-from/top/', '', url_backdrop)

						callInThread(self.saveBackdrop, url_backdrop, dwn_backdrop)

						return True, "[SUCCESS url_backdrop: programmetv-google] {} [{}] => Found title : '{}' => {} => {} (initial size: {}) [{}]".format(title, chkType, get_title, url_ptv, url_backdrop, url_backdrop_size, ptv_id)

			return False, "[SKIP : programmetv-google] {} [{}] => Not found [{}] => {}".format(self.title_safe, chkType, ptv_id, url_ptv)

		except Exception as e:
			if exists(dwn_backdrop):
				remove(dwn_backdrop)
			return False, "[ERROR : programmetv-google] {} [{}] => {} ({})".format(title, chkType, url_ptv, str(e))

	def search_molotov_google(self, dwn_backdrop, title, shortdesc, fulldesc, channel=None):
		try:
			self.dwn_backdrop = dwn_backdrop
			url_mgoo = ''
			# headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"}
			headers = {"User-Agent": choice(AGENTS)}

			# Check type and handle movie exclusion early
			chkType, fd = self.checkType(shortdesc, fulldesc)
			if chkType.startswith("movie"):
				return False, "[SKIP : molotov-google] {} [{}] => Skip movie title".format(title, chkType)

			title_safe = title.replace('+', ' ')
			self.title_safe = title_safe
			pchannel = self.UNAC(channel).replace(' ', '') if channel else ''

			backdrop = None
			imsg = ''
			url_mgoo = "site:molotov.tv+" + self.title_safe

			# Add channel if applicable
			if channel and self.title_safe.find(channel.split()[0]) < 0:
				url_mgoo += "+" + quoteEventName(channel)

			url_mgoo = "https://www.google.com/search?q={}&tbm=isch".format(url_mgoo)
			ff = get(url_mgoo, stream=True, headers=headers, cookies={'CONSENT': 'YES+'}).text
			if not PY3:
				ff = ff.encode('utf-8')

			# Extract image results
			plst = findall(r'https://www.molotov.tv/(.*?)"(?:.*?)?"(.*?)"', ff)
			molotov_id = 0
			molotov_table = [0, 0, None, None, 0]
			partialtitle = 0
			partialchannel = 0

			# Process the results
			for pl in plst:
				get_path = "https://www.molotov.tv/" + pl[0]
				get_name = self.UNAC(pl[1])
				get_title = findall(r'(.*?)[ ]+en[ ]+streaming', get_name)
				get_title = get_title[0] if get_title else None

				get_channel = findall(r'(?:streaming|replay)?[ ]+sur[ ]+(.*?)[ ]+molotov.tv', get_name)
				if not get_channel:
					get_channel = findall(r'regarder[ ]+(.*?)[ ]+en', get_name)
				get_channel = self.UNAC(get_channel[0]).replace(' ', '') if get_channel else None

				# Match title and channel
				partialchannel = self.PMATCH(pchannel, get_channel)
				partialtitle = self.PMATCH(self.title_safe, get_title)

				# Update the best match
				if partialtitle > molotov_table[0]:
					molotov_table = [partialtitle, partialchannel, get_name, get_path, molotov_id]
				if partialtitle == 100 and partialchannel == 100:
					break
				molotov_id += 1

			# If a match is found, download image
			if molotov_table[0]:
				ffm = get(molotov_table[3], stream=True, headers=headers).text
				if not PY3:
					ffm = ffm.encode('utf-8')
				pltt = findall(r'"https://fusion.molotov.tv/(.*?)/jpg" alt="(.*?)"', ffm)
				if len(pltt) > 0:
					pltc = self.UNAC(pltt[0][1])
					plst = "https://fusion.molotov.tv/" + pltt[0][0] + "/jpg"
					imsg = "Found title ({}%) & channel ({}%) : '{}' + '{}' [{}/{}]".format(
						molotov_table[0], molotov_table[1], molotov_table[2], pltc, molotov_table[4], len(plst)
					)
			else:
				# Fallback image search
				plst = findall(r'\],\["https://(.*?)",\d+,\d+].*?"https://.*?","(.*?)"', ff)
				len_plst = len(plst)
				if len_plst > 0:
					for pl in plst:
						if pl[1].startswith("Regarder"):
							pltc = self.UNAC(pl[1])
							partialtitle = self.PMATCH(self.title_safe, pltc)
							get_channel = findall(r'regarder[ ]+(.*?)[ ]+en', pltc)
							get_channel = self.UNAC(get_channel[0]).replace(' ', '') if get_channel else None
							partialchannel = self.PMATCH(pchannel, get_channel)
							if partialchannel > 0 and partialtitle < 50:
								partialtitle = 50
							plst = "https://" + pl[0]
							molotov_table = [partialtitle, partialchannel, pltc, plst, -1]
							imsg = "Fallback title ({}%) & channel ({}%) : '{}' [{}/{}]".format(
								molotov_table[0], molotov_table[1], pltc, -1, len(plst)
							)
							break

			# Determine if valid backdrop is found
			if molotov_table[0] == 100 and molotov_table[1] == 100:
				backdrop = plst
			elif chkType.startswith("movie"):
				imsg = "Skip movie type '{}' [{}%-{}%-{}]".format(pltc, molotov_table[0], molotov_table[1], len(plst))
			elif molotov_table[0] == 100:
				backdrop = plst
			elif molotov_table[0] >= 50 and molotov_table[1]:
				backdrop = plst
			elif molotov_table[0] >= 75:
				backdrop = plst
			elif chkType == '':
				imsg = "Skip unknown type '{}' [{}%-{}%-{}]".format(pltc, molotov_table[0], molotov_table[1], len(plst))
			elif molotov_table[0] >= 25 and molotov_table[1]:
				backdrop = plst
			elif molotov_table[0] >= 50:
				backdrop = plst
			else:
				imsg = "Not found '{}' [{}%-{}%-{}]".format(pltc, molotov_table[0], molotov_table[1], len(plst))

			# If backdrop is found, download it
			if backdrop:
				url_backdrop = sub(r'/\d+x\d+/', "/" + sub(r',', 'x', isz) + "/", backdrop)
				callInThread(self.saveBackdrop, url_backdrop, dwn_backdrop)
				return True, "[SUCCESS url_backdrop: molotov-google] {} ({}) [{}] => {} => {} => {}".format(
					self.title_safe, channel, chkType, imsg, url_mgoo, url_backdrop
				)

			return False, "[SKIP : molotov-google] {} ({}) [{}] => {} => {}".format(self.title_safe, channel, chkType, imsg, url_mgoo)

		except Exception as e:
			if exists(dwn_backdrop):
				remove(dwn_backdrop)
			return False, "[ERROR : molotov-google] {} [{}] => {} ({})".format(self.title_safe, chkType, url_mgoo, str(e))

	def search_google(self, dwn_backdrop, title, shortdesc, fulldesc, channel=None):
		try:
			self.dwn_backdrop = dwn_backdrop
			# headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"}
			headers = {"User-Agent": choice(AGENTS)}

			chkType, fd = self.checkType(shortdesc, fulldesc)
			backdrop = None
			url_backdrop = ''
			year = None
			srch = None

			title_safe = title.replace('+', ' ')  # Replace '+' with space in title
			self.title_safe = title_safe

			# Extract year from the full description
			year = findall(r'19\d{2}|20\d{2}', fd)
			year = year[0] if year else None

			# Determine the search term based on the type
			if chkType.startswith("movie"):
				srch = chkType[6:]
			elif chkType.startswith("tv"):
				srch = chkType[3:]

			# Construct the Google search URL
			url_google = '"{}"'.format(self.title_safe)
			if channel and self.title_safe.find(channel) < 0:
				url_google += "+{}".format(quoteEventName(channel))
			if srch:
				url_google += "+{}".format(srch)
			if year:
				url_google += "+{}".format(year)

			url_google = "https://www.google.com/search?q={}&tbm=isch&tbs=sbd:0".format(url_google)

			# Get the response from Google
			ff = get(url_google, stream=True, headers=headers, cookies={'CONSENT': 'YES+'}).text

			# Extract image URLs from the response
			backdroplst = findall(r'\],\["https://(.*?)",\d+,\d+]', ff)

			# If no results found, try searching again with a different query
			if not backdroplst:
				url_google = "https://www.google.com/search?q={}&tbm=isch&tbs=ift:jpg%2Cisz:m".format(self.title_safe)
				ff = get(url_google, stream=True, headers=headers).text
				backdroplst = findall(r'\],\["https://(.*?)",\d+,\d+]', ff)

			# Process the image results
			for pl in backdroplst:
				url_backdrop = "https://{}".format(pl)
				url_backdrop = sub(r"\\u003d", "=", url_backdrop)
				callInThread(self.saveBackdrop, url_backdrop, dwn_backdrop)

				# Check if the backdrop file exists after downloading
				if exists(dwn_backdrop):
					backdrop = pl
					break

			# Return the result based on whether a backdrop was found
			if backdrop:
				return True, "[SUCCESS backdrop: google] {} [{}-{}] => {} => {}".format(self.title_safe, chkType, year, url_google, url_backdrop)

			return False, "[SKIP : google] {} [{}-{}] => {} => {} (Not found)".format(self.title_safe, chkType, year, url_google, url_backdrop)

		except Exception as e:
			if exists(dwn_backdrop):
				remove(dwn_backdrop)
			return False, "[ERROR : google] {} [{}-{}] => {} => {} ({})".format(self.title_safe, chkType, year, url_google, url_backdrop, str(e))

	def saveBackdrop(self, url, callback):
		headers = {"User-Agent": choice(AGENTS)}
		try:
			if not url or url.strip().endswith("/original"):
				return None

			response = get(url, headers=headers, timeout=(3.05, 6))
			response.raise_for_status()

			if response.status_code == 200:
				with open(callback, "wb") as local_file:
					local_file.write(response.content)

		except RequestException as error:
			logger.error("ERROR in module 'download': Error:{} Url:{} Callback:{}".format(str(error), url, callback))

		return callback

	def resizebackdrop(self, dwn_backdrop):
		try:
			img = Image.open(dwn_backdrop)
			width, height = img.size
			ratio = float(width) // float(height)
			new_height = int(isz.split(",")[1])
			new_width = int(ratio * new_height)
			try:
				rimg = img.resize((new_width, new_height), Image.LANCZOS)
			except:
				rimg = img.resize((new_width, new_height), Image.ANTIALIAS)
			img.close()
			rimg.save(dwn_backdrop)
			rimg.close()
		except Exception as e:
			logger.error("ERROR:{}".format(e))

	def verifybackdrop(self, dwn_backdrop):
		try:
			img = Image.open(dwn_backdrop)
			img.verify()
			if img.format == "JPEG":
				pass
			else:
				try:
					remove(dwn_backdrop)
				except:
					pass
				return False
		except Exception as e:
			logger.error(e)
			try:
				remove(dwn_backdrop)
			except:
				pass
			return False
		return True

	def checkType(self, shortdesc, fulldesc):
		if shortdesc and shortdesc != '':
			fd = shortdesc.splitlines()[0]
		elif fulldesc and fulldesc != '':
			fd = fulldesc.splitlines()[0]
		else:
			fd = ''
		global srch
		srch = "multi"
		return srch, fd

	def UNAC(self, string):
		string = normalize('NFD', string)
		string = sub(r"u0026", "&", string)
		string = sub(r"u003d", "=", string)
		string = sub(r'[\u0300-\u036f]', '', string)  # Remove accents
		string = sub(r"[,!?\.\"]", ' ', string)       # Replace punctuation with space
		string = sub(r'\s+', ' ', string)             # Collapse multiple spaces
		return string.strip()

	def PMATCH(self, textA, textB):
		if not textB or textB == '' or not textA or textA == '':
			return 0
		if textA == textB:
			return 100
		if textA.replace(" ", "") == textB.replace(" ", ""):
			return 100
		if len(textA) > len(textB):
			lId = len(textA.replace(" ", ""))
		else:
			lId = len(textB.replace(" ", ""))
		textA = textA.split()
		cId = 0
		for id in textA:
			if id in textB:
				cId += len(id)
		cId = 100 * cId // lId
		return cId


"""
	def PMATCH(self, textA, textB):
		if not textA or not textB:
			return 0
		if textA == textB or textA.replace(" ", "") == textB.replace(" ", ""):
			return 100

		textA = textA.split()
		common_chars = sum(len(word) for word in textA if word in textB)
		max_length = max(len(textA.replace(" ", "")), len(textB.replace(" ", "")))
		match_percentage = (100 * common_chars) // max_length
		return match_percentage
"""
