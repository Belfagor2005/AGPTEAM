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
from requests import get, codes, Session
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import HTTPError, Timeout
from twisted.internet.reactor import callInThread

# Enigma2 specific
from enigma import getDesktop
from Components.config import config

# Local imports
from .Agp_lib import PY3, quoteEventName
from .Agp_apikeys import tmdb_api, thetvdb_api, fanart_api  # , omdb_api
from .Agp_Utils import logger


# ========================
# DISABLE URLLIB3 DEBUG LOGS
# ========================
import logging
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)


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
headers = {"User-Agent": choice(AGENTS)}


isz = "1280,720"
screenwidth = getDesktop(0).size()
if screenwidth.width() <= 1280:
	isz = isz.replace(isz, "1280,720")
elif screenwidth.width() <= 1920:
	isz = isz.replace(isz, "1280,720")
else:
	isz = isz.replace(isz, "1280,720")


'''
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
Tipo              Dimensioni consigliate    Aspetto
Poster              500x750 → 2000x3000     1.5 (2:3)
Poster TV Season    400x578 → 2000x3000     1.5 (2:3)
Backdrop            1280x720 → 3840x2160    1.777 (16:9)
Still (episodio)    400x225 → 3840x2160     1.777 (16:9)
Profile             300x450 → 2000x3000     1.5 (2:3)
Logo PNG            500x1 → 2000x2000       Variabile
Logo SVG            500x1 → vettoriale      Variabile
'''


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
		"""Download backdrop from TMDB with full verification pipeline"""
		self.title_safe = self.UNAC(title.replace("+", " ").strip())
		try:
			if not dwn_backdrop or not self.title_safe:
				return (False, "Invalid input parameters")

			if not self.title_safe:
				return (False, "Invalid title after cleaning")

			# 3. Determine search type
			srch, fd = self.checkType(shortdesc, fulldesc)

			# 4. Build TMDB API URL
			url = f"https://api.themoviedb.org/3/search/{srch}?api_key={tmdb_api}&language={lng}&query={self.title_safe}"

			# 5. Make API request with retries
			retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
			adapter = HTTPAdapter(max_retries=retries)
			http = Session()
			http.mount("http://", adapter)
			http.mount("https://", adapter)
			response = http.get(url, headers=headers, timeout=(10, 20), verify=False)
			response.raise_for_status()

			if response.status_code == codes.ok:
				try:
					data = response.json()
					return self.downloadData2(data, dwn_backdrop)
				except ValueError as e:
					logger.error("TMDb response decode error: " + str(e))
					return False, "Error parsing TMDb response"
			elif response.status_code == 404:
				# Silently handle 404 - no result found
				return False, "No results found on TMDb"
			else:
				return False, "TMDb request error: " + str(response.status_code)

		except HTTPError as e:
			if e.response is not None and e.response.status_code == 404:
				# Suppress 404 HTTP errors
				return False, "No results found on TMDb"
			else:
				logger.error("TMDb HTTP error: " + str(e))
				return False, "HTTP error during TMDb search"

		except Exception as e:
			logger.error("TMDb search error: " + str(e))
			return False, "Unexpected error during TMDb search"

	def downloadData2(self, data, dwn_backdrop):
		if isinstance(data, bytes):
			data = data.decode('utf-8')
		data_json = data if isinstance(data, dict) else loads(data)

		if 'results' in data_json:
			for each in data_json['results']:
				media_type = str(each.get('media_type', ''))
				if media_type == "tv":
					media_type = "serie"
				if media_type not in ['serie', 'movie']:
					continue
				# year = ""
				# if media_type == "movie" and 'release_date' in each and each['release_date']:
					# year = each['release_date'].split("-")[0]
				# elif media_type == "serie" and 'first_air_date' in each and each['first_air_date']:
					# year = each['first_air_date'].split("-")[0]

				title = each.get('name', each.get('title', ''))
				backdrop_path = each.get('backdrop_path')

				if not backdrop_path:  # Se non c'è backdrop, salta
					continue

				backdrop = f"http://image.tmdb.org/t/p/original{backdrop_path}"
				if not backdrop.strip() or backdrop.endswith("/original"):
					continue
				if backdrop.strip():
					callInThread(self.saveBackdrop, backdrop, dwn_backdrop)
					if exists(dwn_backdrop):
						return True, f"[SUCCESS] Backdrop avviato: {title}"
		return False, "[SKIP] No valid result"

	def search_tvdb(self, dwn_backdrop, title, shortdesc, fulldesc, channel=None):
		self.title_safe = title.replace("+", " ")
		try:
			if not exists(dwn_backdrop):
				return (False, "File not created")

			series_nb = -1
			chkType, fd = self.checkType(shortdesc, fulldesc)
			year_match = findall(r"19\d{2}|20\d{2}", fd)
			year = year_match[0] if year_match else ""

			url_tvdbg = "https://thetvdb.com/api/GetSeries.php?seriesname={}".format(self.title_safe)
			url_read = get(url_tvdbg).text

			series_id = findall(r"<seriesid>(.*?)</seriesid>", url_read)
			series_name = findall(r"<SeriesName>(.*?)</SeriesName>", url_read)
			series_year = findall(r"<FirstAired>(19\d{2}|20\d{2})-\d{2}-\d{2}</FirstAired>", url_read)

			for i, iseries_year in enumerate(series_year):
				if not year or year == iseries_year:
					series_nb = i
					break

			backdrop = None
			if series_nb >= 0 and len(series_id) > series_nb and series_id[series_nb]:
				if series_name and len(series_name) > series_nb:
					series_name_clean = self.UNAC(series_name[series_nb])
				else:
					series_name_clean = ""

				if self.PMATCH(self.title_safe, series_name_clean):
					if "thetvdb_api" not in globals():
						return False, "[ERROR : tvdb] API key not defined"

					url_tvdb = "https://thetvdb.com/api/{}/series/{}".format(thetvdb_api, series_id[series_nb])
					url_tvdb += "/{}".format(lng if "lng" in globals() and lng else "en")

					url_read = get(url_tvdb).text
					backdrop = findall(r"<backdrop>(.*?)</backdrop>", url_read)

					if backdrop and backdrop[0]:
						url_backdrop = "https://artworks.thetvdb.com/banners/{}".format(backdrop[0])
						callInThread(self.saveBackdrop, url_backdrop, dwn_backdrop)
						if exists(dwn_backdrop):
							return True, "[SUCCESS : tvdb] {} [{}-{}] => {} => {} => {}".format(
								self.title_safe, chkType, year, url_tvdbg, url_tvdb, url_backdrop
							)

					return False, "[SKIP : tvdb] {} [{}-{}] => {} (Not found)".format(
						self.title_safe, chkType, year, url_tvdbg
					)

			return False, "[SKIP : tvdb] {} [{}-{}] => {} (Not found)".format(
				self.title_safe, chkType, year, url_tvdbg
			)

		except Exception as e:
			return False, "[ERROR : tvdb] {} => {} ({})".format(self.title_safe, url_tvdbg, str(e))

		except HTTPError as e:
			if e.response is not None and e.response.status_code == 404:
				return False, "No results found on tvdb"
			else:
				logger.error("tvdb HTTP error: " + str(e))
				return False, "HTTP error during tvdb search"

	def search_fanart(self, dwn_backdrop, title, shortdesc, fulldesc, channel=None):
		self.title_safe = title.replace("+", " ")
		try:
			if not exists(dwn_backdrop):
				return False, "File not created"

			year = ""
			tvmaze_id = "-"
			chkType, fd = self.checkType(shortdesc, fulldesc)

			# Try to extract the year from the description
			try:
				matches = findall(r"19\d{2}|20\d{2}", fd)
				if matches:
					year = matches[1] if len(matches) > 1 else matches[0]
			except Exception:
				pass

			# Fetch TVMaze ID from the API
			try:
				url_maze = "http://api.tvmaze.com/singlesearch/shows?q={}".format(self.title_safe)
				resp = get(url_maze, timeout=5)
				resp.raise_for_status()
				mj = resp.json()
				tvmaze_id = mj.get("externals", {}).get("thetvdb", "-")
			except Exception as err:
				logger.error("TVMaze error: " + str(err))

			# Fetch Fanart backdrop using TVMaze ID
			try:
				m_type = "tv"
				url_fanart = "https://webservice.fanart.tv/v3/{}/{}?api_key={}".format(m_type, tvmaze_id, fanart_api)
				fjs = get(url_fanart, verify=False, timeout=5).json()
				url = ""

				# Check for show or movie background
				if "showbackground" in fjs and fjs["showbackground"]:
					url = fjs["showbackground"][0]["url"]
				elif "moviebackground" in fjs and fjs["moviebackground"]:
					url = fjs["moviebackground"][0]["url"]

				# Handle if URL is found
				if url:
					callInThread(self.saveBackdrop, url, dwn_backdrop)
					msg = "[SUCCESS backdrop: fanart] {} [{}-{}] => {} => {} => {}".format(
						self.title_safe, chkType, year, url_maze, url_fanart, url
					)
					if exists(dwn_backdrop):
						return True, msg
				else:
					return False, f"[SKIP : fanart] {self.title_safe} [{chkType}-{year}] => {url_fanart} (Not found)"
			except Exception as e:
				logger.error(f"[ERROR : fanart] {self.title_safe} [{chkType}-{year}] => {url_maze} ({str(e)})")
				return False, "[ERROR : fanart] {} [{}-{}] => {} ({})".format(self.title_safe, chkType, year, url_maze, str(e))

		except Exception as e:
			logger.error(f"[ERROR : fanart] {self.title_safe} [{chkType}-{year}] => {str(e)}")
			return False, f"[ERROR : fanart] {self.title_safe} [{chkType}-{year}]"

		except HTTPError as e:
			if e.response and e.response.status_code == 404:
				return False, "No results found on fanart"
			else:
				logger.error("fanart HTTP error: " + str(e))
				return False, "HTTP error during fanart search"

	def search_imdb(self, dwn_backdrop, title, shortdesc, fulldesc, channel=None):
		self.title_safe = title.replace("+", " ")
		try:
			if not exists(dwn_backdrop):
				return False, "File not created"

			chkType, fd = self.checkType(shortdesc, fulldesc)
			aka_list = findall(r"\((.*?)\)", fd)
			aka = next((a for a in aka_list if not a.isdigit()), None)
			paka = self.UNAC(aka) if aka else ""

			# Extract year from description
			year_matches = findall(r"19\d{2}|20\d{2}", fd)
			year = year_matches[0] if year_matches else ""

			url_mimdb = ""
			url_backdrop = ""
			url_imdb = ""

			# Formulate search URL based on AKA (if exists)
			if aka and aka != self.title_safe:
				url_mimdb = "https://m.imdb.com/find?q={}%20({})".format(self.title_safe, quoteEventName(aka))
			else:
				url_mimdb = "https://m.imdb.com/find?q={}".format(self.title_safe)

			# Get IMDb search results
			try:
				url_read = get(url_mimdb).text
				rc = compile(r'<img src="(.*?)".*?<span class="h3">\n(.*?)\n</span>.*?\((\d+)\)(\s\(.*?\))?(.*?)</a>', DOTALL)
				url_imdb = rc.findall(url_read)

				# If no results, retry without AKA
				if not url_imdb and aka:
					url_mimdb = "https://m.imdb.com/find?q={}".format(self.title_safe)
					url_read = get(url_mimdb).text
					url_imdb = rc.findall(url_read)

			except Exception as err:
				logger.error(f"IMDb search error: {err}")
				return False, f"[ERROR : imdb] IMDb search failed: {err}"

			len_imdb = len(url_imdb)
			idx_imdb = 0
			pfound = False

			for imdb in url_imdb:
				imdb = list(imdb)
				imdb[1] = self.UNAC(imdb[1])
				tmp = findall(r'aka <i>"(.*?)"</i>', imdb[4])
				imdb[4] = self.UNAC(tmp[0]) if tmp else self.UNAC(imdb[4])

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
					if year and year == imdb_year:
						imsg = f"Found title: '{imdb_title}', aka: '{imdb_aka}', year: '{imdb_year}'"
						if self.PMATCH(self.title_safe, imdb_title) or self.PMATCH(self.title_safe, imdb_aka) or self.PMATCH(paka, imdb_title) or self.PMATCH(paka, imdb_aka):
							pfound = True
							break
					elif year and (int(year) - 1 == int(imdb_year) or int(year) + 1 == int(imdb_year)):
						imsg = f"Found title: '{imdb_title}', aka: '{imdb_aka}', year: '+/-{imdb_year}'"
						if self.title_safe == imdb_title or self.title_safe == imdb_aka or paka == imdb_title or paka == imdb_aka:
							pfound = True
							break
					elif not year:
						imsg = f"Found title: '{imdb_title}', aka: '{imdb_aka}', year: ''"
						if self.title_safe == imdb_title or self.title_safe == imdb_aka or paka == imdb_title or paka == imdb_aka:
							pfound = True
							break
				idx_imdb += 1

			if url_backdrop and pfound:
				callInThread(self.saveBackdrop, url_backdrop, dwn_backdrop)
				if exists(dwn_backdrop):
					msg = "[SUCCESS url_backdrop: imdb] {} [{}-{}] => {} [{}/{}] => {} => {}".format(
						self.title_safe, chkType, year, imsg, idx_imdb, len_imdb, url_mimdb, url_backdrop
					)
					return True, msg

			return False, "[SKIP : imdb] {} [{}-{}] => {} (No Entry found [{}])".format(self.title_safe, chkType, year, url_mimdb, len_imdb)

		except Exception as e:
			logger.error(f"[ERROR : imdb] {self.title_safe} [{chkType}-{year}] => {url_mimdb} ({str(e)})")
			return False, f"[ERROR : imdb] {self.title_safe} [{chkType}-{year}] => {url_mimdb} ({str(e)})"

		except HTTPError as e:
			if e.response and e.response.status_code == 404:
				return False, "No results found on imdb"
			else:
				logger.error(f"IMDb HTTP error: {str(e)}")
				return False, "HTTP error during imdb search"

	def search_programmetv_google(self, dwn_backdrop, title, shortdesc, fulldesc, channel=None):
		self.title_safe = title.replace('+', ' ')

		try:
			# Check if file exists
			if not exists(dwn_backdrop):
				return False, "File not created"

			url_ptv = ""
			chkType, fd = self.checkType(shortdesc, fulldesc)

			# Skip if it's a movie title
			if chkType.startswith("movie"):
				return False, f"[SKIP : programmetv-google] {self.title_safe} [{chkType}] => Skip movie title"

			# Build Google search URL for programme-tv.net images
			url_ptv = f"site:programme-tv.net+{self.title_safe}"

			# Add channel if provided and not already included in the title
			if channel and self.title_safe.find(channel.split()[0]) < 0:
				url_ptv += "+" + quoteEventName(channel)

			# Create full Google search URL
			url_ptv = f"https://www.google.com/search?q={url_ptv}&tbm=isch&tbs=ift:jpg%2Cisz:m"

			# Make request to Google search
			ff = get(url_ptv, stream=True, headers=headers, cookies={'CONSENT': 'YES+'}).text
			if not PY3:
				ff = ff.encode('utf-8')

			ptv_id = 0
			plst = findall(r'\],\["https://www.programme-tv.net(.*?)",\d+,\d+]', ff)

			# Loop through image results
			for backdroplst in plst:
				ptv_id += 1
				url_backdrop = f"https://www.programme-tv.net{backdroplst}"
				url_backdrop = sub(r"\\u003d", "=", url_backdrop)

				# Extract image size and other details
				url_backdrop_size = findall(r'([\d]+)x([\d]+).*?([\w\.-]+).jpg', url_backdrop)

				if url_backdrop_size and url_backdrop_size[0]:
					get_title = self.UNAC(url_backdrop_size[0][2].replace('-', ''))

					# Match the title with the search result
					if self.title_safe == get_title:
						h_ori = float(url_backdrop_size[0][1])
						h_tar = float(findall(r'(\d+)', isz)[1])
						ratio = h_ori / h_tar
						w_ori = float(url_backdrop_size[0][0])
						w_tar = w_ori / ratio
						w_tar = int(w_tar)
						h_tar = int(h_tar)

						# Adjust the image URL for target size
						url_backdrop = sub(r'/\d+x\d+/', f"/{w_tar}x{h_tar}/", url_backdrop)
						url_backdrop = sub(r'crop-from/top/', '', url_backdrop)

						# Download the image in a separate thread
						callInThread(self.saveBackdrop, url_backdrop, dwn_backdrop)

						# Check if the backdrop was successfully downloaded
						if exists(dwn_backdrop):
							return True, f"[SUCCESS url_backdrop: programmetv-google] {self.title_safe} [{chkType}] => Found title: '{get_title}' => {url_ptv} => {url_backdrop} (initial size: {url_backdrop_size}) [{ptv_id}]"

			# If no image found, return skip message
			return False, f"[SKIP : programmetv-google] {self.title_safe} [{chkType}] => Not found [{ptv_id}] => {url_ptv}"

		except Exception as e:
			# General exception handling
			return False, f"[ERROR : programmetv-google] {self.title_safe} [{chkType}] => {url_ptv} ({str(e)})"

		except HTTPError as e:
			# Handle HTTP errors
			if e.response is not None and e.response.status_code == 404:
				return False, "No results found on programmetv-google"
			else:
				logger.error(f"programmetv-google HTTP error: {str(e)}")
				return False, "HTTP error during programmetv-google search"

	def search_molotov_google(self, dwn_backdrop, title, shortdesc, fulldesc, channel=None):
		self.title_safe = title.replace('+', ' ')

		try:
			# Check if the file exists
			if not exists(dwn_backdrop):
				return False, "File not created"

			url_mgoo = ""
			chkType, fd = self.checkType(shortdesc, fulldesc)

			# Skip if it's a movie title
			if chkType.startswith("movie"):
				return False, f"[SKIP : molotov-google] {self.title_safe} [{chkType}] => Skip movie title"

			# Clean up channel name
			pchannel = self.UNAC(channel).replace(' ', '') if channel else ''

			# Construct the Google search URL
			url_mgoo = f"site:molotov.tv+{self.title_safe}"
			if channel and self.title_safe.find(channel.split()[0]) < 0:
				url_mgoo += "+" + quoteEventName(channel)

			# Perform the Google search
			url_mgoo = f"https://www.google.com/search?q={url_mgoo}&tbm=isch"
			ff = get(url_mgoo, stream=True, headers=headers, cookies={'CONSENT': 'YES+'}).text
			if not PY3:
				ff = ff.encode('utf-8')

			# Search for Molotov images in the results
			plst = findall(r'https://www.molotov.tv/(.*?)"(?:.*?)?"(.*?)"', ff)
			molotov_table = [0, 0, None, None, 0]  # [title match, channel match, title, path, id]

			for pl in plst:
				get_path = f"https://www.molotov.tv/{pl[0]}"
				get_name = self.UNAC(pl[1])
				get_title = findall(r'(.*?)[ ]+en[ ]+streaming', get_name) or None
				get_channel = self.extract_channel(get_name)

				# Match title and channel
				partialtitle = self.PMATCH(self.title_safe, get_title or '')
				partialchannel = self.PMATCH(pchannel, get_channel or '')

				# Update the best match found
				if partialtitle > molotov_table[0]:
					molotov_table = [partialtitle, partialchannel, get_name, get_path, len(molotov_table)]

				# If both title and channel match perfectly, exit early
				if partialtitle == 100 and partialchannel == 100:
					break

			# Handle the result if a match is found
			if molotov_table[0]:
				return self.handle_backdrop_result(molotov_table, headers, dwn_backdrop, 'molotov')
			else:
				# Fallback in case no result found
				return self.handle_fallback(ff, pchannel, self.title_safe, headers, dwn_backdrop)

		except Exception as e:
			# General exception handling
			return False, f"[ERROR : molotov-google] {self.title_safe} => {str(e)}"

		except HTTPError as e:
			# Handle HTTP errors
			if e.response is not None and e.response.status_code == 404:
				return False, "No results found on molotov-google"
			else:
				logger.error(f"molotov-google HTTP error: {str(e)}")
				return False, "HTTP error during molotov-google search"

	def extract_channel(self, get_name):
		get_channel = findall(r'(?:streaming|replay)?[ ]+sur[ ]+(.*?)[ ]+molotov.tv', get_name) or \
			findall(r'regarder[ ]+(.*?)[ ]+en', get_name)
		return self.UNAC(get_channel[0]).replace(' ', '') if get_channel else None

	def handle_backdrop_result(self, molotov_table, headers, dwn_backdrop, platform):
		ffm = get(molotov_table[3], stream=True, headers=headers).text
		if not PY3:
			ffm = ffm.encode('utf-8')

		pltt = findall(r'"https://fusion.molotov.tv/(.*?)/jpg" alt="(.*?)"', ffm)
		if len(pltt) > 0:
			backdrop_url = f"https://fusion.molotov.tv/{pltt[0][0]}/jpg"
			callInThread(self.saveBackdrop, backdrop_url, dwn_backdrop)
			if exists(dwn_backdrop):
				return True, f"[SUCCESS {platform}-google] Found backdrop for {self.title_safe} => {backdrop_url}"
		else:
			return False, f"[SKIP : {platform}-google] No suitable backdrop found."

	def handle_fallback(self, ff, pchannel, title_safe, headers, dwn_backdrop):
		plst = findall(r'\],\["https://(.*?)",\d+,\d+].*?"https://.*?","(.*?)"', ff)
		if plst:
			for pl in plst:
				if pl[1].startswith("Regarder"):
					backdrop_url = f"https://{pl[0]}"
					callInThread(self.saveBackdrop, backdrop_url, dwn_backdrop)
					if exists(dwn_backdrop):
						return True, f"[SUCCESS fallback] Found fallback backdrop for {title_safe} => {backdrop_url}"
		return False, "[SKIP : fallback] No suitable fallback found."

	def search_google(self, dwn_backdrop, title, shortdesc, fulldesc, channel=None):
		self.title_safe = title.replace('+', ' ')
		try:
			if not exists(dwn_backdrop):
				return (False, "File not created")

			chkType, fd = self.checkType(shortdesc, fulldesc)
			year = findall(r'19\d{2}|20\d{2}', fd)
			year = year[0] if year else None
			url_google = f'"{self.title_safe}"'
			if channel and self.title_safe.find(channel) < 0:
				url_google += f"+{quoteEventName(channel)}"
			if chkType.startswith("movie"):
				url_google += f"+{chkType[6:]}"
			if year:
				url_google += f"+{year}"

			def fetch_images(url):
				return get(url, stream=True, headers=headers, cookies={'CONSENT': 'YES+'}).text

			url_google = f"https://www.google.com/search?q={url_google}&tbm=isch&tbs=sbd:0"
			ff = fetch_images(url_google)

			backdroplst = findall(r'\],\["https://(.*?)",\d+,\d+]', ff)

			if not backdroplst:
				url_google = f"https://www.google.com/search?q={self.title_safe}&tbm=isch&tbs=ift:jpg%2Cisz:m"
				ff = fetch_images(url_google)
				backdroplst = findall(r'\],\["https://(.*?)",\d+,\d+]', ff)

			for pl in backdroplst:
				url_backdrop = f"https://{pl}"
				url_backdrop = sub(r"\\u003d", "=", url_backdrop)
				callInThread(self.saveBackdrop, url_backdrop, dwn_backdrop)
				if exists(dwn_backdrop):
					return True, f"[SUCCESS google] Found backdrop for {self.title_safe} => {url_backdrop}"

			return False, f"[SKIP : google] No backdrop found for {self.title_safe}"

		except Exception as e:
			return False, f"[ERROR : google] {self.title_safe} => {str(e)}"

		except HTTPError as e:
			if e.response is not None and e.response.status_code == 404:
				# Suppress 404 HTTP errors
				return False, "No results found on google"
			else:
				logger.error("programmetv-google HTTP error: " + str(e))
				return False, "HTTP error during google search"

	def saveBackdrop(self, url, filepath):
		if not url:
			return False

		if exists(filepath):
			return True

		try:
			headers = {"User-Agent": choice(AGENTS)}
			response = get(url, headers=headers, timeout=(10, 30))
			response.raise_for_status()

			with open(filepath, "wb") as f:
				f.write(response.content)
			return True

		except HTTPError as http_err:
			logger.error("HTTP error saving Backdrop: %s (%s)", str(http_err), url)
		except Timeout as timeout_err:
			logger.error("Timeout error saving Backdrop: %s (%s)", str(timeout_err), url)
		except Exception as e:
			logger.error("Unexpected error saving Backdrop: %s (%s)", str(e), url)

		return False

	def resizeBackdrop(self, dwn_backdrop):
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
			print("ERROR:{}".format(e))

	def verifyBackdrop(self, dwn_backdrop):
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
			print(e)
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
