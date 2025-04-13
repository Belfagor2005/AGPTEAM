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


isz = "185,278"
screenwidth = getDesktop(0).size()
if screenwidth.width() <= 1280:
	isz = isz.replace(isz, "185,278")
elif screenwidth.width() <= 1920:
	isz = isz.replace(isz, "342,514")
else:
	isz = isz.replace(isz, "780,1170")


'''
isz = "w780"
"backdrop_sizes": [
  "w300",
  "w780",
  "w1280",
  "original"
],
"logo_sizes": [
  "w45",
  "w92",
  "w154",
  "w185",
  "w300",
  "w500",
  "original"
],
"poster_sizes": [
  "w92",
  "w154",
  "w185",
  "w342",
  "w500",
  "w780",
  "original"
],
"profile_sizes": [
  "w45",
  "w185",
  "h632",
  "original"
],
"still_sizes": [
  "w92",
  "w185",
  "w300",
  "original"
]
## Add Supported Image Sizes (in Pixels)
# API NAME  =   WEB NAME           MIN Pixel    MAX Pixel     Aspect Ratio
# poster    = Poster ............  500 x 750   2000 x 3000   1.50    (1x1.5)
# poster    = Poster TV Season ..  400 x 578   2000 x 3000   1.50    (1x1.5)
# backdrop  = Backdrop .......... 1280 x 720   3840 x 2160   1.77778 (16x9)
# still     = Backdrop Episode ..  400 x 225   3840 x 2160   1.77778 (16x9)
# profile   = Person Profile ....  300 x 450   2000 x 3000   1.50    (1x1.5)
# Logo PNG  = Production/Networks  500 x 1     2000 x 2000   n/a
# Logo SVG  = Production/Networks  500 x 1     Vector File   n/a
'''


class AgpDownloadThread(Thread):
	def __init__(self):
		Thread.__init__(self)
		self.checkMovie = ["film", "movie", "фильм", "кино", "ταινία",
						   "película", "cinéma", "cine", "cinema",
						   "filma"]
		self.checkTV = ["serial", "series", "serie", "serien", "série",
						"séries", "serious", "folge", "episodio",
						"episode", "épisode", "l'épisode", "ep.",
						"animation", "staffel", "soap", "doku", "tv",
						"talk", "show", "news", "factual",
						"entertainment", "telenovela", "dokumentation",
						"dokutainment", "documentary", "informercial",
						"information", "sitcom", "reality", "program",
						"magazine", "mittagsmagazin", "т/с", "м/с",
						"сезон", "с-н", "эпизод", "сериал", "серия",
						"actualité", "discussion", "interview", "débat",
						"émission", "divertissement", "jeu", "magasine",
						"information", "météo", "journal", "sport",
						"culture", "infos", "feuilleton", "téléréalité",
						"société", "clips", "concert", "santé",
						"éducation", "variété"]

	def search_tmdb(self, dwn_poster, title, shortdesc, fulldesc, channel=None):
		try:
			self.dwn_poster = dwn_poster
			title_safe = title
			self.title_safe = title_safe.replace('+', ' ')
			url = f"https://api.themoviedb.org/3/search/multi?api_key={tmdb_api}&language={lng}&query={self.title_safe}"
			data = None
			retries = Retry(total=1, backoff_factor=1)
			adapter = HTTPAdapter(max_retries=retries)
			http = Session()
			http.mount("http://", adapter)
			http.mount("https://", adapter)
			# headers = {'User-Agent': getRandomUserAgent()}
			headers = {"User-Agent": choice(AGENTS)}
			response = http.get(url, headers=headers, timeout=(10, 20), verify=False)
			response.raise_for_status()
			if response.status_code == codes.ok:
				try:
					data = response.json()
				except ValueError as e:
					print(e)
					data = None
				self.downloadData2(data)
				return True, "Download avviato con successo"
			else:
				return False, f"Errore durante la ricerca su TMDb: {response.status_code}"
		except Exception as e:
			print('Errore nella ricerca TMDb:', e)
			return False, "Errore durante la ricerca su TMDb"

	def downloadData2(self, data):
		if isinstance(data, bytes):
			data = data.decode('utf-8')
		data_json = data if isinstance(data, dict) else loads(data)
		if 'results' in data_json:
			try:
				for each in data_json['results']:
					media_type = str(each['media_type']) if each.get('media_type') else ''
					if media_type == "tv":
						media_type = "serie"
					if media_type in ['serie', 'movie']:
						year = ""
						if media_type == "movie" and 'release_date' in each and each['release_date']:
							year = each['release_date'].split("-")[0]
						elif media_type == "serie" and 'first_air_date' in each and each['first_air_date']:
							year = each['first_air_date'].split("-")[0]

						title = each.get('name', each.get('title', ''))

						backdrop_path = each.get('backdrop_path')
						poster_path = each.get('poster_path')

						backdrop = "http://image.tmdb.org/t/p/original" + backdrop_path if backdrop_path else ""
						poster = "http://image.tmdb.org/t/p/original" + poster_path if poster_path else ""

						rating = str(each.get('vote_average', 0))
						show_title = title
						if year:
							show_title = "{} ({})".format(title, year)
						if isinstance(poster, str) and poster.strip() != "":
							callInThread(self.savePoster, poster, self.dwn_poster)
							# if exists(self.dwn_poster):
							return True, "[SUCCESS poster: tmdb] title {} [poster{}-backdrop{}] => year{} => rating{} => showtitle{}".format(title, poster, backdrop, year, rating, show_title)
					return False, "[SKIP : tmdb] Not found"
			except Exception as e:
				print('error=', e)
				if exists(self.dwn_poster):
					remove(self.dwn_poster)
				return False, "[ERROR : tmdb]"

	def search_tvdb(self, dwn_poster, title, shortdesc, fulldesc, channel=None):
		try:
			self.dwn_poster = dwn_poster
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
			poster = None
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
					poster = findall(r'<poster>(.*?)</poster>', url_read)
					url_poster = "https://artworks.thetvdb.com/banners/{}".format(poster[0])
					if poster is not None and poster[0]:
						callInThread(self.savePoster, url_poster, self.dwn_poster)
						# if exists(dwn_poster):
						return True, "[SUCCESS : tvdb] {} [{}-{}] => {} => {} => {}".format(self.title_safe, chkType, year, url_tvdbg, url_tvdb, url_poster)
					return False, "[SKIP : tvdb] {} [{}-{}] => {} (Not found)".format(self.title_safe, chkType, year, url_tvdbg)
			else:
				return False, "[SKIP : tvdb] {} [{}-{}] => {} (Not found)".format(self.title_safe, chkType, year, url_tvdbg)

		except Exception as e:
			if exists(dwn_poster):
				remove(dwn_poster)
			return False, "[ERROR : tvdb] {} => {} ({})".format(title, url_tvdbg, str(e))

	def search_fanart(self, dwn_poster, title, shortdesc, fulldesc, channel=None):
		try:
			year = None
			url_maze = ""
			url_fanart = ""
			url_poster = None
			id = "-"
			title_safe = title
			self.title_safe = title_safe.replace('+', ' ')
			chkType, fd = self.checkType(shortdesc, fulldesc)
			try:
				if findall(r'19\d{2}|20\d{2}', self.title_safe):
					year = findall(r'19\d{2}|20\d{2}', fd)[1]
				else:
					year = findall(r'19\d{2}|20\d{2}', fd)[0]
			except:
				year = ''
				pass

			try:
				url_maze = "http://api.tvmaze.com/singlesearch/shows?q={}".format(self.title_safe)
				mj = get(url_maze).json()
				id = (mj['externals']['thetvdb'])
			except Exception as err:
				print('Error:', err)

			try:
				m_type = 'tv'
				url_fanart = "https://webservice.fanart.tv/v3/{}/{}?api_key={}".format(m_type, id, fanart_api)
				fjs = get(url_fanart, verify=False, timeout=5).json()
				try:
					url = (fjs['tvposter'][0]['url'])
				except:
					url = (fjs['movieposter'][0]['url'])

				url_poster = get(url).json()
				if url_poster and url_poster != 'null' or url_poster is not None or url_poster != '':
					callInThread(self.savePoster, url_poster, dwn_poster)
					# if exists(dwn_poster):
					return True, "[SUCCESS poster: fanart] {} [{}-{}] => {} => {} => {}".format(self.title_safe, chkType, year, url_maze, url_fanart, url_poster)
				return False, "[SKIP : fanart] {} [{}-{}] => {} (Not found)".format(self.title_safe, chkType, year, url_fanart)
			except Exception as e:
				print(e)

		except Exception as e:
			if exists(dwn_poster):
				remove(dwn_poster)
			return False, "[ERROR : fanart] {} [{}-{}] => {} ({})".format(self.title_safe, chkType, year, url_fanart, str(e))

	def search_imdb(self, dwn_poster, title, shortdesc, fulldesc, channel=None):
		try:
			self.dwn_poster = dwn_poster
			url_poster = None
			chkType, fd = self.checkType(shortdesc, fulldesc)
			title_safe = title
			self.title_safe = title_safe.replace('+', ' ')
			aka = findall(r'\((.*?)\)', fd)
			if len(aka) > 1 and not aka[1].isdigit():
				aka = aka[1]
			elif len(aka) > 0 and not aka[0].isdigit():
				aka = aka[0]
			else:
				aka = None
			if aka:
				paka = self.UNAC(aka)
			else:
				paka = ''
			year = findall(r'19\d{2}|20\d{2}', fd)
			if len(year) > 0:
				year = year[0]
			else:
				year = ''
			imsg = ''
			url_mimdb = ''
			url_imdb = ''

			if aka and aka != self.title_safe:
				url_mimdb = "https://m.imdb.com/find?q={}%20({})".format(self.title_safe, quoteEventName(aka))
			else:
				url_mimdb = "https://m.imdb.com/find?q={}".format(self.title_safe)
			url_read = get(url_mimdb).text
			rc = compile(r'<img src="(.*?)".*?<span class="h3">\n(.*?)\n</span>.*?\((\d+)\)(\s\(.*?\))?(.*?)</a>', DOTALL)
			url_imdb = rc.findall(url_read)

			if len(url_imdb) == 0 and aka:
				url_mimdb = "https://m.imdb.com/find?q={}".format(self.title_safe)
				url_read = get(url_mimdb).text
				rc = compile(r'<img src="(.*?)".*?<span class="h3">\n(.*?)\n</span>.*?\((\d+)\)(\s\(.*?\))?(.*?)</a>', DOTALL)
				url_imdb = rc.findall(url_read)
			len_imdb = len(url_imdb)
			idx_imdb = 0
			pfound = False

			for imdb in url_imdb:
				imdb = list(imdb)
				imdb[1] = self.UNAC(imdb[1])
				tmp = findall(r'aka <i>"(.*?)"</i>', imdb[4])
				if tmp:
					imdb[4] = tmp[0]
				else:
					imdb[4] = ''
				imdb[4] = self.UNAC(imdb[4])
				imdb_poster = search(r"(.*?)._V1_.*?.jpg", imdb[0])
				if imdb_poster:
					if imdb[3] == '':
						if year and year != '':
							if year == imdb[2]:
								url_poster = "{}._V1_UY278,1,185,278_AL_.jpg".format(imdb_poster.group(1))
								imsg = "Found title : '{}', aka : '{}', year : '{}'".format(imdb[1], imdb[4], imdb[2])
								if self.PMATCH(self.title_safe, imdb[1]) or self.PMATCH(self.title_safe, imdb[4]) or (paka != '' and self.PMATCH(paka, imdb[1])) or (paka != '' and self.PMATCH(paka, imdb[4])):
									pfound = True
									break
							elif not url_poster and (int(year) - 1 == int(imdb[2]) or int(year) + 1 == int(imdb[2])):
								url_poster = "{}._V1_UY278,1,185,278_AL_.jpg".format(imdb_poster.group(1))
								imsg = "Found title : '{}', aka : '{}', year : '+/-{}'".format(imdb[1], imdb[4], imdb[2])
								if self.title_safe == imdb[1] or self.title_safe == imdb[4] or (paka != '' and paka == imdb[1]) or (paka != '' and paka == imdb[4]):
									pfound = True
									break
						else:
							url_poster = "{}._V1_UY278,1,185,278_AL_.jpg".format(imdb_poster.group(1))
							imsg = "Found title : '{}', aka : '{}', year : ''".format(imdb[1], imdb[4])
							if self.title_safe == imdb[1] or self.title_safe == imdb[4] or (paka != '' and paka == imdb[1]) or (paka != '' and paka == imdb[4]):
								pfound = True
								break
				idx_imdb += 1
			if url_poster and pfound:
				callInThread(self.savePoster, url_poster, dwn_poster)
				# if exists(dwn_poster):
				return True, "[SUCCESS url_poster: imdb] {} [{}-{}] => {} [{}/{}] => {} => {}".format(self.title_safe, chkType, year, imsg, idx_imdb, len_imdb, url_mimdb, url_poster)
			return False, "[SKIP : imdb] {} [{}-{}] => {} (No Entry found [{}])".format(self.title_safe, chkType, year, url_mimdb, len_imdb)

		except Exception as e:
			if exists(dwn_poster):
				remove(dwn_poster)
			return False, "[ERROR : imdb] {} [{}-{}] => {} ({})".format(self.title_safe, chkType, year, url_mimdb, str(e))

	def search_programmetv_google(self, dwn_poster, title, shortdesc, fulldesc, channel=None):
		try:
			self.dwn_poster = dwn_poster
			url_ptv = ''
			# headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"}
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
			for posterlst in plst:
				ptv_id += 1
				url_poster = "https://www.programme-tv.net{}".format(posterlst)
				url_poster = sub(r"\\u003d", "=", url_poster)
				url_poster_size = findall(r'([\d]+)x([\d]+).*?([\w\.-]+).jpg', url_poster)
				if url_poster_size and url_poster_size[0]:
					get_title = self.UNAC(url_poster_size[0][2].replace('-', ''))
					if self.title_safe == get_title:
						h_ori = float(url_poster_size[0][1])
						h_tar = float(findall(r'(\d+)', isz)[1])
						ratio = h_ori / h_tar
						w_ori = float(url_poster_size[0][0])
						w_tar = w_ori / ratio
						w_tar = int(w_tar)
						h_tar = int(h_tar)
						url_poster = sub(r'/\d+x\d+/', "/" + str(w_tar) + "x" + str(h_tar) + "/", url_poster)
						url_poster = sub(r'crop-from/top/', '', url_poster)
						callInThread(self.savePoster, url_poster, self.dwn_poster)
						# if exists(dwn_poster):
						return True, "[SUCCESS url_poster: programmetv-google] {} [{}] => Found self.title_safe : '{}' => {} => {} (initial size: {}) [{}]".format(self.title_safe, chkType, get_title, url_ptv, url_poster, url_poster_size, ptv_id)
				return False, "[SKIP : programmetv-google] {} [{}] => Not found [{}] => {}".format(self.title_safe, chkType, ptv_id, url_ptv)

		except Exception as e:
			if exists(dwn_poster):
				remove(dwn_poster)
			return False, "[ERROR : programmetv-google] {} [{}] => {} ({})".format(self.title_safe, chkType, url_ptv, str(e))

	def search_molotov_google(self, dwn_poster, title, shortdesc, fulldesc, channel=None):
		try:
			self.dwn_poster = dwn_poster
			url_mgoo = ''
			# headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"}
			headers = {"User-Agent": choice(AGENTS)}
			chkType, fd = self.checkType(shortdesc, fulldesc)
			title_safe = title
			self.title_safe = title_safe.replace('+', ' ')
			if channel:
				pchannel = self.UNAC(channel).replace(' ', '')
			else:
				pchannel = ''
			poster = None
			pltc = None
			imsg = ''
			url_mgoo = "site:molotov.tv+" + self.title_safe
			if channel and self.title_safe.find(channel.split()[0]) < 0:
				url_mgoo += "+" + quoteEventName(channel)
			url_mgoo = "https://www.google.com/search?q={}&tbm=isch".format(url_mgoo)
			ff = get(url_mgoo, stream=True, headers=headers, cookies={'CONSENT': 'YES+'}).text
			if not PY3:
				ff = ff.encode('utf-8')
			plst = findall(r'https://www.molotov.tv/(.*?)"(?:.*?)?"(.*?)"', ff)
			len_plst = len(plst)
			molotov_id = 0
			molotov_table = [0, 0, None, None, 0]
			partialtitle = 0
			partialchannel = 0
			for pl in plst:
				get_path = "https://www.molotov.tv/" + pl[0]
				get_name = self.UNAC(pl[1])
				get_title = findall(r'(.*?)[ ]+en[ ]+streaming', get_name)
				if get_title:
					get_title = get_title[0]
				else:
					get_title = None
				get_channel = findall(r'(?:streaming|replay)?[ ]+sur[ ]+(.*?)[ ]+molotov.tv', get_name)
				if get_channel:
					get_channel = self.UNAC(get_channel[0]).replace(' ', '')
				else:
					get_channel = findall(r'regarder[ ]+(.*?)[ ]+en', get_name)
					if get_channel:
						get_channel = self.UNAC(get_channel[0]).replace(' ', '')
					else:
						get_channel = None
				partialchannel = self.PMATCH(pchannel, get_channel)
				partialtitle = self.PMATCH(self.title_safe, get_title)
				if partialtitle > molotov_table[0]:
					molotov_table = [partialtitle, partialchannel, get_name, get_path, molotov_id]
				if partialtitle == 100 and partialchannel == 100:
					break
				molotov_id += 1

			if molotov_table[0]:
				ffm = get(molotov_table[3], stream=True, headers=headers).text
				if not PY3:
					ffm = ffm.encode('utf-8')
				pltt = findall(r'"https://fusion.molotov.tv/(.*?)/jpg" alt="(.*?)"', ffm)
				if len(pltt) > 0:
					pltc = self.UNAC(pltt[0][1])
					plst = "https://fusion.molotov.tv/" + pltt[0][0] + "/jpg"
					imsg = "Found title ({}%) & channel ({}%) : '{}' + '{}' [{}/{}]".format(molotov_table[0], molotov_table[1], molotov_table[2], pltc, molotov_table[4], len_plst)
			else:
				plst = findall(r'\],\["https://(.*?)",\d+,\d+].*?"https://.*?","(.*?)"', ff)
				len_plst = len(plst)
				if len_plst > 0:
					for pl in plst:
						if pl[1].startswith("Regarder"):
							pltc = self.UNAC(pl[1])
							partialtitle = self.PMATCH(self.title_safe, pltc)
							get_channel = findall(r'regarder[ ]+(.*?)[ ]+en', pltc)
							if get_channel:
								get_channel = self.UNAC(get_channel[0]).replace(' ', '')
							else:
								get_channel = None
							partialchannel = self.PMATCH(pchannel, get_channel)
							if partialchannel > 0 and partialtitle < 50:
								partialtitle = 50
							plst = "https://" + pl[0]
							molotov_table = [partialtitle, partialchannel, pltc, plst, -1]
							imsg = "Fallback title ({}%) & channel ({}%) : '{}' [{}/{}]".format(molotov_table[0], molotov_table[1], pltc, -1, len_plst)
							break

			if molotov_table[0] == 100 and molotov_table[1] == 100:
				poster = plst
			elif chkType.startswith("movie"):
				imsg = "Skip movie type '{}' [{}%-{}%-{}]".format(pltc, molotov_table[0], molotov_table[1], len_plst)
			elif molotov_table[0] == 100:
				poster = plst
			elif molotov_table[0] >= 50 and molotov_table[1]:
				poster = plst
			elif molotov_table[0] >= 75:
				poster = plst
			elif chkType == '':
				imsg = "Skip unknown type '{}' [{}%-{}%-{}]".format(pltc, molotov_table[0], molotov_table[1], len_plst)
			elif molotov_table[0] >= 25 and molotov_table[1]:
				poster = plst
			elif molotov_table[0] >= 50:
				poster = plst
			else:
				imsg = "Not found '{}' [{}%-{}%-{}]".format(pltc, molotov_table[0], molotov_table[1], len_plst)
			if poster:
				url_poster = sub(r'/\d+x\d+/', "/" + sub(r', ', 'x', isz) + "/", poster)
				callInThread(self.savePoster, poster, dwn_poster)
				# if exists(dwn_poster):
				return True, "[SUCCESS url_poster: molotov-google] {} ({}) [{}] => {} => {} => {}".format(self.title_safe, channel, chkType, imsg, url_mgoo, url_poster)
			return False, "[SKIP : molotov-google] {} ({}) [{}] => {} => {} => {} (jpeg error)".format(self.title_safe, channel, chkType, imsg, url_mgoo, url_poster)
		except Exception as e:
			if exists(dwn_poster):
				remove(dwn_poster)
			return False, "[ERROR : molotov-google] {} [{}] => {} ({})".format(self.title_safe, chkType, url_mgoo, str(e))

	def search_google(self, dwn_poster, title, shortdesc, fulldesc, channel=None):
		try:
			self.dwn_poster = dwn_poster
			# headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"}
			headers = {"User-Agent": choice(AGENTS)}
			chkType, fd = self.checkType(shortdesc, fulldesc)
			poster = None
			url_poster = ''
			year = None
			srch = None
			title_safe = title
			self.title_safe = title_safe.replace('+', ' ')
			year = findall(r'19\d{2}|20\d{2}', fd)
			if len(year) > 0:
				year = year[0]
			else:
				year = None
			if chkType.startswith("movie"):
				srch = chkType[6:]
			elif chkType.startswith("tv"):
				srch = chkType[3:]
			url_google = '"' + self.title_safe + '"'
			if channel and self.title_safe.find(channel) < 0:
				url_google += "+{}".format(quoteEventName(channel))
			if srch:
				url_google += "+{}".format(srch)
			if year:
				url_google += "+{}".format(year)
			url_google = "https://www.google.com/search?q={}&tbm=isch&tbs=sbd:0".format(url_google)
			ff = get(url_google, stream=True, headers=headers, cookies={'CONSENT': 'YES+'}).text

			posterlst = findall(r'\],\["https://(.*?)",\d+,\d+]', ff)
			if len(posterlst) == 0:
				url_google = self.title_safe
				url_google = "https://www.google.com/search?q={}&tbm=isch&tbs=ift:jpg%2Cisz:m".format(url_google)
				ff = get(url_google, stream=True, headers=headers).text
				posterlst = findall(r'\],\["https://(.*?)",\d+,\d+]', ff)

			for pl in posterlst:
				# self.sizeb = False
				url_poster = "https://{}".format(pl)
				url_poster = sub(r"\\u003d", " = ", url_poster)
				callInThread(self.savePoster, url_poster, dwn_poster)
				if exists(dwn_poster):
					poster = pl
					break

			if poster is not None:
				return True, "[SUCCESS poster: google] {} [{}-{}] => {} => {}".format(self.title_safe, chkType, year, url_google, url_poster)
			return False, "[SKIP : google] {} [{}-{}] => {} => {} (Not found)".format(self.title_safe, chkType, year, url_google, url_poster)

		except Exception as e:
			if exists(dwn_poster):
				remove(dwn_poster)
			return False, "[ERROR : google] {} [{}-{}] => {} => {} ({})".format(self.title_safe, chkType, year, url_google, url_poster, str(e))

	def savePoster(self, url, callback):
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
			print("ERROR in module 'download': Error:{} Url:{} Callback:{}".format(str(error), url, callback))

		return callback

	def resizePoster(self, dwn_poster):
		try:
			img = Image.open(dwn_poster)
			width, height = img.size
			ratio = float(width) // float(height)
			new_height = int(isz.split(",")[1])
			new_width = int(ratio * new_height)
			try:
				rimg = img.resize((new_width, new_height), Image.LANCZOS)
			except:
				rimg = img.resize((new_width, new_height), Image.ANTIALIAS)
			img.close()
			rimg.save(dwn_poster)
			rimg.close()
		except Exception as e:
			print("ERROR:{}".format(e))

	def verifyPoster(self, dwn_poster):
		try:
			img = Image.open(dwn_poster)
			img.verify()
			if img.format == "JPEG":
				pass
			else:
				try:
					remove(dwn_poster)
				except:
					pass
				return False
		except Exception as e:
			print(e)
			try:
				remove(dwn_poster)
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
