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

# Standard library imports
from os.path import join, exists
from re import sub
from json import load as json_load

# Enigma2 imports
from Components.Renderer.Renderer import Renderer
from enigma import ePixmap, loadPNG
import gettext

# Local imports
from Plugins.Extensions.Aglare.plugin import ApiKeyManager, config
from .Agp_Utils import POSTER_FOLDER, clean_for_tvdb, logger

# Constants
api_key_manager = ApiKeyManager()
_ = gettext.gettext
cur_skin = config.skin.primary_skin.value.replace('/skin.xml', '')
GENRE_PIC_PATH = f'/usr/share/enigma2/{cur_skin}/genre_pic/'
GENRE_SOURCE = config.plugins.Aglare.genre_source.value
if not POSTER_FOLDER.endswith("/"):
	POSTER_FOLDER += "/"

"""skin configuration

<widget render="AgpGenreX"
	source="session.Event_Now"
	position="44,370"
	size="160,45"
	zPosition="22"
	transparent="1" />


Setup on config plugin
config.plugins.Aglare.genre_source = ConfigOnOff(default=False)

Icons
/usr/share/enigma2/<skin>/genre_pic/

├── 3d.png
├── action.png
├── adult.png
├── adventure.png
├── animation.png
├── arts.png
├── athletics.png
├── ballet.png
├── black-white.png
├── cartoon.png
├── children.png
├── childrens.png
├── cinema.png
├── classic music.png
├── comedy.png
├── cooking.png
├── culture.png
├── detective.png
├── disc.png
├── docu.png
├── documentary.png
├── drama.png
├── economics.png
├── education.png
├── entertainment (10-16).png
├── entertainment (6-14).png
├── equestrian.png
├── expeditions.png
├── expfilm.png
├── fashion.png
├── fine arts.png
├── fitness.png
├── folk.png
├── football.png
├── further education.png
├── gardening.png
├── handicraft.png
├── hobbies.png
├── information.png
├── jazz.png
├── languages.png
├── literature.png
├── live broadcast.png
├── magazine.png
├── magazines.png
├── martial sports.png
├── medicine.png
├── mistery.png
├── motor sport.png
├── motoring.png
├── movie.png
├── music.png
├── musical-opera.png
├── n/a.png
├── nature-animals.png
├── new media.png
├── news.png
├── news.png
├── original language.png
├── performing arts.png
├── popculture.png
├── press.png
├── quiz.png
├── religion.png
├── remarkable people.png
├── rock-pop.png
├── romance.png
├── science.png
├── serie.png
├── serious.png
├── shopping.png
├── show.png
├── social.png
├── social.png
├── special.png
├── sports magazine.png
├── sports.png
├── talk.png
├── team sports.png
├── technology.png
├── tennis.png
├── thriller.png
├── travel.png
├── unpublished.png
├── variety.png
├── water sport.png
├── weather.png
├── western.png
└── winter sport.png

"""

# EPG DVB genre mapping (level1 → tuple of subgenres)
genre_mapping = {
	1: ('N/A', 'News', 'Western', 'Action', 'Thriller', 'Drama', 'Movie', 'Detective', 'Mistery', 'Adventure', 'Science', 'Animation', 'Comedy', 'Serie', 'Romance', 'Serious', 'Adult'),
	2: ('News', 'Weather', 'Magazine', 'Docu', 'Disc', 'Documentary'),
	3: ('Show', 'Quiz', 'Variety', 'Talk'),
	4: ('Sports', 'Special', 'Sports Magazine', 'Football', 'Tennis', 'Team Sports', 'Athletics', 'Motor Sport', 'Water Sport', 'Winter Sport', 'Equestrian', 'Martial Sports'),
	5: ('Childrens', 'Children', 'entertainment (6-14)', 'entertainment (10-16)', 'Information', 'Cartoon'),
	6: ('Music', 'Rock/Pop', 'Classic Music', 'Folk', 'Jazz', 'Musical/Opera', 'Ballet'),
	7: ('Arts', 'Performing Arts', 'Fine Arts', 'Religion', 'PopCulture', 'Literature', 'Cinema', 'ExpFilm', 'Press', 'New Media', 'Culture', 'Fashion'),
	8: ('Social', 'Magazines', 'Economics', 'Remarkable People'),
	9: ('Education', 'Nature/Animals/', 'Technology', 'Medicine', 'Expeditions', 'Social', 'Further Education', 'Languages'),
	10: ('Hobbies', 'Travel', 'Handicraft', 'Motoring', 'Fitness', 'Cooking', 'Shopping', 'Gardening'),
	11: ('Original Language', 'Black & White', 'Unpublished', 'Live Broadcast'),
}


# Genre mapping compatible with last EPG levels
GENRE_MAP = {
	1: {
		'default': 'general',
		1: 'action', 2: 'thriller', 3: 'drama', 4: 'movie',
		16: 'animation', 35: 'comedy'
	},
	5: {
		'default': 'kids',
		1: 'cartoon'
	},
	12: {
		'default': 'adventure'
	},
	14: {
		'default': 'fantasy'
	},
	16: {
		'default': 'animation'
	},
	18: {
		'default': 'drama'
	},
	27: {
		'default': 'horror'
	},
	28: {
		'default': 'action'
	},
	35: {
		'default': 'comedy'
	},
	36: {
		'default': 'history'
	},
	37: {
		'default': 'western'
	},
	53: {
		'default': 'thriller'
	},
	80: {
		'default': 'crime'
	},
	99: {
		'default': 'documentary'
	},
	878: {
		'default': 'sciencefiction'
	},
	9648: {
		'default': 'mystery'
	},
	10402: {
		'default': 'music'
	},
	10749: {
		'default': 'romance'
	},
	10751: {
		'default': 'family'
	},
	10752: {
		'default': 'war'
	},
	10763: {
		'default': 'news'
	},
	10764: {
		'default': 'reality'
	},
	10765: {
		'default': 'science'
	},
	10766: {
		'default': 'soap'
	},
	10767: {
		'default': 'talk'
	},
	10768: {
		'default': 'warpolitics'
	},
	10769: {
		'default': 'gameshow'
	},
	10770: {
		'default': 'tvmovie'
	},
	10771: {
		'default': 'variety'
	},
	10772: {
		'default': 'familykids'
	}
}


class AgpGenreX(Renderer):
	"""Advanced genre icon renderer with AGP ecosystem integration"""

	GUI_WIDGET = ePixmap

	def __init__(self):
		Renderer.__init__(self)
		self.storage_path = POSTER_FOLDER
		logger.info("AgpGenreX Renderer initialized")

	def changed(self, what):
		"""Handle EPG changes"""
		if what is None or not config.plugins.Aglare.genre_source.value:
			# logger.debug(f"AgpGenreX.changed skipped (what={what}, genre_source={config.plugins.Aglare.genre_source.value})")
			if self.instance:
				self.instance.hide()
			return

		# logger.info(f"AgpGenreX.changed running (what={what})")
		self.delay()

	def delay(self):
		logger.info("AgpGenreX.delay start")
		evName = ""
		eventNm = ""
		genreTxt = ""

		# Fetch event
		self.event = self.source.event
		if not self.event:
			return

		# Clean event name
		evName = self.event.getEventName().strip().replace('ё', 'е')
		eventNm = clean_for_tvdb(evName)
		# logger.info(f"GenreX raw event name: {evName!r}, cleaned: {eventNm!r}")

		# Try JSON metadata
		infos_file = join(self.storage_path, eventNm + ".json")
		# logger.info("GenreX checking for infos_file: %s", infos_file)
		if exists(infos_file):
			try:
				with open(infos_file, "r") as f:
					json_data = json_load(f)
					# logger.info("GenreX from JSON → id=%s name=%s", json_data["genres"][0]["id"], json_data["genres"][0]["name"])
					genre_id = json_data["genres"][0]["id"]
					genreTxt = GENRE_MAP.get(genre_id, {"default": "general"}).get("default", "general")
			except Exception as e:
				logger.error("GenreX JSON error: %s", str(e))
		else:
			logger.debug("GenreX JSON file does not exist: %s", infos_file)

		# Fallback to EPG if needed
		if not genreTxt:
			try:
				gData = self.event.getGenreData()
				logger.info(f"GenreX raw gData: {gData}")
				if gData:
					lvl1 = gData.getLevel1()
					lvl2 = gData.getLevel2()
					# logger.info(f"GenreX EPG levels → level1={lvl1}, level2={lvl2}")

					# Map using genre_mapping tuple by index
					genreTxt = None
					subgenres = genre_mapping.get(lvl1)
					if isinstance(subgenres, tuple) and 0 <= lvl2 < len(subgenres):
						genreTxt = subgenres[lvl2]
						logger.info(f"GenreX mapped genreTxt after EPG → '{genreTxt}'")
				else:
					genreTxt = 'general'
					logger.info("GenreX fallback to 'general'")
					logger.warning("GenreX getGenreData() returned None")

			except Exception as e:
				logger.error(f"GenreX error reading EPG: {e}")

		# Build PNG path
		# logger.info(f"GenreTxt value before generating PNG path: {genreTxt}")
		png_name = sub(r"[^0-9a-z]+", "_", genreTxt.lower()).strip("_") + ".png"
		png_path = join(GENRE_PIC_PATH, png_name)

		# logger.info(f"GenreX: checking PNG file path: {png_path}")  # Log del percorso PNG
		if exists(png_path):
			# logger.info(f"GenreX found PNG file at path: {png_path}")
			self.instance.setPixmap(loadPNG(png_path))
		else:
			generic = join(GENRE_PIC_PATH, "general.png")
			logger.warning(f"Genre image not found at {png_path}. Using default {generic}")
			self.instance.setPixmap(loadPNG(generic))

		self.instance.setScale(1)
		self.instance.show()
