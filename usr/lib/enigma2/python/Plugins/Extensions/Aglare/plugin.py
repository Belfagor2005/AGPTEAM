#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
"""
#########################################################
#                                                       #
#  AGLARE SETUP UTILITY SKIN                            #
#  Version: 5.4                                         #
#  Created by Lululla (https://github.com/Belfagor2005) #
#  License: CC BY-NC-SA 4.0                             #
#  https://creativecommons.org/licenses/by-nc-sa/4.0    #
#                                                       #
#  Last Modified: "15:14 - 20250423"                    #
#                                                       #
#  Credits:                                             #
#  - Original concept by Lululla                        #
#  - TMDB API integration                               #
#  - TVDB API integration                               #
#  - OMDB API integration                               #
#  - FANART API integration                             #
#  - IMDB API integration                               #
#  - ELCINEMA API integration                           #
#  - GOOGLE API integration                             #
#  - PROGRAMMETV integration                            #
#  - MOLOTOV API integration                            #
#  - Fully configurable via AGP Setup Plugin            #
#                                                       #
#  Usage of this code without proper attribution        #
#  is strictly prohibited.                              #
#  For modifications and redistribution,                #
#  please maintain this credit header.                  #
#########################################################
"""

# Standard library
from glob import glob as glob_glob
from os import remove, stat, system as os_system
from os.path import exists, join
from sys import version_info

# Third-party libraries
from PIL import Image

# Enigma2 core
from enigma import ePicLoad, eTimer, loadPic

# Enigma2 Components
from Components.AVSwitch import AVSwitch
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.Progress import Progress
from Components.Sources.StaticText import StaticText
from Components.config import (
	configfile,
	ConfigOnOff,
	NoSave,
	ConfigText,
	ConfigSelection,
	ConfigSubsection,
	ConfigYesNo,
	config,
	getConfigListEntry,
	ConfigClock
)

# Enigma2 Screens
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop

# Enigma2 Tools
from Tools.Directories import fileExists
from Tools.Downloader import downloadWithProgress

# Plugin-local imports
from . import _
from Plugins.Plugin import PluginDescriptor


from urllib.request import Request

version = '5.4'

"""
HELPER
🔑 How the API Key Loading System Works
This plugin uses a dynamic system to load API keys for various external services
(e.g., TMDB, FANART, THETVDB, OMDB, IMDB, ELCINEMA, GOOGLE, PROGRAMMETV, MOLOTOV)
from skin files in the Enigma2 environment.

📁 Configuration Structure
API configurations are defined in a dictionary called API_CONFIG, which contains the following for each API:

skin_file: the expected filename in the skin directory (e.g., tmdbkey)
default_key: fallback key if no file is found
var_name: the variable name to bind the key globally

🔁 Automatic Global Assignment
When the plugin is initialized, it automatically sets global variables for both:

The path to the API key file in the skin directory (e.g., tmdb_skin)
The API key itself, using either the default or the value read from the file

📥 Dynamic Loading from Skin
The function load_api_keys() checks if the skin-specific key files exist,
and if they do, loads their contents and overrides the global default keys.
This allows the plugin to use custom API keys depending on the active skin.

"""

""" assign path """


def isMountedInRW(mount_point):
	with open("/proc/mounts", "r") as f:
		for line in f:
			parts = line.split()
			if len(parts) > 1 and parts[1] == mount_point:
				return True
	return False


path_poster = "/tmp/poster"
patch_backdrop = "/tmp/backdrop"

if exists("/media/usb") and isMountedInRW("/media/usb"):
	path_poster = "/media/usb/poster"
	patch_backdrop = "/media/usb/backdrop"

elif exists("/media/hdd") and isMountedInRW("/media/hdd"):
	path_poster = "/media/hdd/poster"
	patch_backdrop = "/media/hdd/backdrop"

elif exists("/media/mmc") and isMountedInRW("/media/mmc"):
	path_poster = "/media/mmc/poster"
	patch_backdrop = "/media/mmc/backdrop"

""" end assign path """

""" Config and setting maintenance """

config.plugins.Aglare = ConfigSubsection()
config.plugins.Aglare.actapi = ConfigOnOff(default=True)
config.plugins.Aglare.tmdb = ConfigOnOff(default=True)
config.plugins.Aglare.load_tmdb_api = ConfigYesNo(default=False)
config.plugins.Aglare.tmdb_api = ConfigText(default="3c3efcf47c3577558812bb9d64019d65", visible_width=50, fixed_size=False)

config.plugins.Aglare.fanart = ConfigOnOff(default=False)
config.plugins.Aglare.load_fanart_api = ConfigYesNo(default=False)
config.plugins.Aglare.fanart_api = ConfigText(default="6d231536dea4318a88cb2520ce89473b", visible_width=50, fixed_size=False)

config.plugins.Aglare.thetvdb = ConfigOnOff(default=False)
config.plugins.Aglare.load_thetvdb_api = ConfigYesNo(default=False)
config.plugins.Aglare.thetvdb_api = ConfigText(default="a99d487bb3426e5f3a60dea6d3d3c7ef", visible_width=50, fixed_size=False)

config.plugins.Aglare.omdb = ConfigOnOff(default=False)
config.plugins.Aglare.load_omdb_api = ConfigYesNo(default=False)
config.plugins.Aglare.omdb_api = ConfigText(default="4ca6ea60", visible_width=50, fixed_size=False)

config.plugins.Aglare.elcinema = ConfigOnOff(default=False)
config.plugins.Aglare.google = ConfigOnOff(default=False)
config.plugins.Aglare.imdb = ConfigOnOff(default=False)
config.plugins.Aglare.programmetv = ConfigOnOff(default=False)
config.plugins.Aglare.molotov = ConfigOnOff(default=False)

config.plugins.Aglare.pstdown = ConfigOnOff(default=False)
config.plugins.Aglare.bkddown = ConfigOnOff(default=False)
config.plugins.Aglare.pscan_time = ConfigClock(default=(0, 0))  # 00:00
config.plugins.Aglare.bscan_time = ConfigClock(default=(2, 0))  # 02:00

config.plugins.Aglare.png = NoSave(ConfigYesNo(default=False))

config.plugins.Aglare.colorSelector = ConfigSelection(default='color0', choices=[
	('color0', _('Default')),
	('color1', _('Black')),
	('color2', _('Brown')),
	('color3', _('Green')),
	('color4', _('Magenta')),
	('color5', _('Blue')),
	('color6', _('Red')),
	('color7', _('Purple')),
	('color8', _('Dark Green'))])
config.plugins.Aglare.FontStyle = ConfigSelection(default='basic', choices=[
	('basic', _('Default')),
	('font1', _('HandelGotD')),
	('font2', _('KhalidArtboldRegular')),
	('font3', _('BebasNeue')),
	('font4', _('Greta')),
	('font5', _('Segoe UI light')),
	('font6', _('MV Boli'))])
config.plugins.Aglare.skinSelector = ConfigSelection(default='base', choices=[
	('base', _('Default'))])
config.plugins.Aglare.InfobarStyle = ConfigSelection(default='infobar_base1', choices=[
	('infobar_base1', _('Default')),
	('infobar_base2', _('Style2')),
	('infobar_base3', _('Style3')),
	('infobar_base4', _('Style4'))])
config.plugins.Aglare.InfobarPosterx = ConfigSelection(default='infobar_posters_posterx_off', choices=[
	('infobar_posters_posterx_off', _('OFF')),
	('infobar_posters_posterx_on', _('ON'))])
config.plugins.Aglare.InfobarXtraevent = ConfigSelection(default='infobar_posters_xtraevent_off', choices=[
	('infobar_posters_xtraevent_off', _('OFF')),
	('infobar_posters_xtraevent_on', _('ON')),
	('infobar_posters_xtraevent_info', _('Backdrop'))])
config.plugins.Aglare.InfobarDate = ConfigSelection(default='infobar_no_date', choices=[
	('infobar_no_date', _('Infobar_NO_Date')),
	('infobar_date', _('Infobar_Date'))])
config.plugins.Aglare.InfobarWeather = ConfigSelection(default='infobar_no_weather', choices=[
	('infobar_no_weather', _('Infobar_NO_Weather')),
	('infobar_weather', _('Infobar_Weather'))])
config.plugins.Aglare.SecondInfobarStyle = ConfigSelection(default='secondinfobar_base1', choices=[
	('secondinfobar_base1', _('Default')),
	('secondinfobar_base2', _('Style2')),
	('secondinfobar_base3', _('Style3')),
	('secondinfobar_base4', _('Style4'))])
config.plugins.Aglare.SecondInfobarPosterx = ConfigSelection(default='secondinfobar_posters_posterx_off', choices=[
	('secondinfobar_posters_posterx_off', _('OFF')),
	('secondinfobar_posters_posterx_on', _('ON'))])
config.plugins.Aglare.SecondInfobarXtraevent = ConfigSelection(default='secondinfobar_posters_xtraevent_off', choices=[
	('secondinfobar_posters_xtraevent_off', _('OFF')),
	('secondinfobar_posters_xtraevent_on', _('ON'))])
config.plugins.Aglare.ChannSelector = ConfigSelection(default='channellist_no_posters', choices=[
	('channellist_no_posters', _('ChannelSelection_NO_Posters')),
	('channellist_no_posters_no_picon', _('ChannelSelection_NO_Posters_NO_Picon')),
	('channellist_backdrop_v', _('ChannelSelection_BackDrop_V')),
	('channellist_backdrop_h', _('ChannelSelection_BackDrop_H')),
	('channellist_1_poster', _('ChannelSelection_1_Poster')),
	('channellist_4_posters', _('ChannelSelection_4_Posters')),
	('channellist_6_posters', _('ChannelSelection_6_Posters')),
	('channellist_big_mini_tv', _('ChannelSelection_big_mini_tv'))])
config.plugins.Aglare.EventView = ConfigSelection(default='eventview_no_posters', choices=[
	('eventview_no_posters', _('EventView_NO_Posters')),
	('eventview_7_posters', _('EventView_7_Posters'))])

config.plugins.Aglare.VolumeBar = ConfigSelection(default='volume1', choices=[
	('volume1', _('Default')),
	('volume2', _('volume2'))])

config.plugins.Aglare.E2iplayerskins = ConfigSelection(default='OFF', choices=[
	('e2iplayer_skin_off', _('OFF')),
	('e2iplayer_skin_on', _('ON'))])

""" Config and setting maintenance """

""" end assign apikey """
# constants
my_cur_skin = False
cur_skin = config.skin.primary_skin.value.replace('/skin.xml', '')
mvi = '/usr/share/'


# Process order
"""
'tmdb': self.search_tmdb,
'fanart': self.search_fanart,
'thetvdb': self.search_tvdb,
'elcinema': self.search_elcinema,   # no apikey
'google': self.search_google,   # no apikey
'omdb': self.search_omdb,
'imdb': self.search_imdb,   # no apikey
'programmetv': self.search_programmetv_google,  # no apikey
'molotov': self.search_molotov_google,  # no apikey
"""


"""
# fallback not work
"omdb": {
	"skin_file": "omdbkey",
	"default_key": "cb1d9f55",
	"config_entry": config.plugins.Aglare.omdb_api,
	"load_action": config.plugins.Aglare.load_omdb_api
},
"""


class ApiKeyManager:
	"""Loads API keys from skin files or falls back to defaults.
	Args:
		API_CONFIG (dict): Configuration mapping for each API.
	"""

	def __init__(self):
		self.API_CONFIG = {
			"tmdb": {
				"skin_file": "tmdbkey",
				"default_key": "3c3efcf47c3577558812bb9d64019d65",
				"config_entry": config.plugins.Aglare.tmdb_api,
				"load_action": config.plugins.Aglare.load_tmdb_api
			},
			"fanart": {
				"skin_file": "fanartkey",
				"default_key": "6d231536dea4318a88cb2520ce89473b",
				"config_entry": config.plugins.Aglare.fanart_api,
				"load_action": config.plugins.Aglare.load_fanart_api
			},
			"thetvdb": {
				"skin_file": "thetvdbkey",
				"default_key": "a99d487bb3426e5f3a60dea6d3d3c7ef",
				"config_entry": config.plugins.Aglare.thetvdb_api,
				"load_action": config.plugins.Aglare.load_thetvdb_api
			},
			"omdb": {
				"skin_file": "omdbkey",
				"default_key": "cb1d9f55",
				"config_entry": config.plugins.Aglare.omdb_api,
				"load_action": config.plugins.Aglare.load_omdb_api
			}
		}

		self.init_paths()
		self.load_all_keys()

	def init_paths(self):
		"""Initialize skin file paths"""
		for api, cfg in self.API_CONFIG.items():
			setattr(self, f"{api}_skin", f"{mvi}enigma2/{cur_skin}/{cfg['skin_file']}")

	def get_api_key(self, provider):
		"""Retrieve API key for the specified provider."""
		if provider in self.API_CONFIG:
			return self.API_CONFIG[provider]['config_entry'].value
		return None

	def load_all_keys(self):
		"""Upload all API keys from different sources"""
		global my_cur_skin
		if my_cur_skin:
			return

		try:
			# Loading from skin file
			for api, cfg in self.API_CONFIG.items():
				skin_path = f"/usr/share/enigma2/{cur_skin}/{cfg['skin_file']}"
				if fileExists(skin_path):
					with open(skin_path, "r") as f:
						key_value = f.read().strip()
					if key_value:
						cfg['config_entry'].value = key_value

			# Overwriting from default values
			for api, cfg in self.API_CONFIG.items():
				if not cfg['config_entry'].value:
					cfg['config_entry'].value = cfg['default_key']

			my_cur_skin = True

		except Exception as e:
			print(f"Error loading API keys: {str(e)}")
			my_cur_skin = False

	def get_active_providers(self):
		"""Returns active providers based on configuration"""
		return {
			api: (
				getattr(config.plugins.Aglare, api).value and
				bool(cfg['config_entry'].value)
			)
			for api, cfg in self.API_CONFIG.items()
		}

	def handle_load_key(self, api):
		"""Handles loading keys from /tmp"""
		tmp_file = f"/tmp/{api}key.txt"
		cfg = self.API_CONFIG.get(api)

		try:
			if fileExists(tmp_file):
				with open(tmp_file, "r") as f:
					key_value = f.read().strip()

				if key_value:
					cfg['config_entry'].value = key_value
					cfg['config_entry'].save()
					return True, _("Key {} successfully loaded!").format(api.upper())
			return False, _("File {} not found or empty").format(tmp_file)

		except Exception as e:
			return False, _("Error loading: {}").format(str(e))


api_key_manager = ApiKeyManager()


class AglareSetup(ConfigListScreen, Screen):
	skin = '''
			<screen name="AglareSetup" position="160,220" size="1600,680" title="Aglare-FHD Skin Controler" backgroundColor="back">
				<eLabel font="Regular; 24" foregroundColor="#00ff4A3C" halign="center" position="20,620" size="120,40" text="Cancel" />
				<eLabel font="Regular; 24" foregroundColor="#0056C856" halign="center" position="310,620" size="120,40" text="Save" />
				<eLabel font="Regular; 24" foregroundColor="#00fbff3c" halign="center" position="600,620" size="120,40" text="Update" />
				<eLabel font="Regular; 24" foregroundColor="#00403cff" halign="center" position="860,620" size="120,40" text="Info" />
				<widget name="Preview" position="1057,146" size="498, 280" zPosition="1" />
				<widget name="config" font="Regular; 24" itemHeight="50" position="5,5" scrollbarMode="showOnDemand" size="990,600" />
			</screen>
		'''

	def __init__(self, session):
		self.version = '.Aglare-FHD-PLI'
		Screen.__init__(self, session)
		self.session = session
		self.skinFile = '/usr/share/enigma2/Aglare-FHD-PLI/skin.xml'
		self.previewFiles = '/usr/lib/enigma2/python/Plugins/Extensions/Aglare/sample/'
		self['Preview'] = Pixmap()
		self.onChangedEntry = []
		self.setup_title = ('Aglare-FHD-PLI')
		list = []
		section = '--------------------------( SKIN GENERAL SETUP )-----------------------'
		list.append(getConfigListEntry(section))
		section = '--------------------------( SKIN APIKEY SETUP )-----------------------'
		list.append(getConfigListEntry(section))
		ConfigListScreen.__init__(self, list, session=self.session, on_change=self.changedEntry)
		self["actions"] = ActionMap(
			[
				"OkCancelActions",
				"InputBoxActions",
				"HotkeyActions",
				"VirtualKeyboardActions",
				"NumberActions",
				"InfoActions",
				"ColorActions"
			],
			{
				"left": self.keyLeft,
				"right": self.keyRight,
				"down": self.keyDown,
				"up": self.keyUp,
				"red": self.keyExit,
				"green": self.keySave,
				"yellow": self.checkforUpdate,
				"showVirtualKeyboard": self.KeyText,
				"ok": self.keyRun,
				"info": self.info,
				"blue": self.info,
				"5": self.Checkskin,
				"cancel": self.keyExit
			},
			-1
		)
		self.createSetup()
		self.PicLoad = ePicLoad()
		self.Scale = AVSwitch().getFramebufferScale()
		self.onLayoutFinish.append(self.ShowPicture)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __layoutFinished(self):
		self.setTitle(self.setup_title)

	def passs(self, foo):
		pass

	def KeyText(self):
		from Screens.VirtualKeyBoard import VirtualKeyBoard
		sel = self["config"].getCurrent()
		if sel:
			self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title=self["config"].getCurrent()[0], text=self["config"].getCurrent()[1].value)

	def VirtualKeyBoardCallback(self, callback=None):
		if callback is not None and len(callback):
			self["config"].getCurrent()[1].value = callback
			self["config"].invalidate(self["config"].getCurrent())
		return

	def createSetup(self):
		try:
			self.editListEntry = None
			list = []
			section = '-------------------------( GENERAL SKIN  SETUP )------------------------'
			list.append(getConfigListEntry(section))
			list.append(getConfigListEntry(_('Color Style:'), config.plugins.Aglare.colorSelector))
			list.append(getConfigListEntry(_('Select Your Font:'), config.plugins.Aglare.FontStyle))
			list.append(getConfigListEntry(_('Skin Style:'), config.plugins.Aglare.skinSelector))
			list.append(getConfigListEntry(_('InfoBar Style:'), config.plugins.Aglare.InfobarStyle))
			list.append(getConfigListEntry(_('InfoBar PosterX:'), config.plugins.Aglare.InfobarPosterx))
			list.append(getConfigListEntry(_('InfoBar Xtraevent:'), config.plugins.Aglare.InfobarXtraevent))
			list.append(getConfigListEntry(_('InfoBar Date:'), config.plugins.Aglare.InfobarDate))
			list.append(getConfigListEntry(_('InfoBar Weather:'), config.plugins.Aglare.InfobarWeather))
			list.append(getConfigListEntry(_('SecondInfobar Style:'), config.plugins.Aglare.SecondInfobarStyle))
			list.append(getConfigListEntry(_('SecondInfobar Posterx:'), config.plugins.Aglare.SecondInfobarPosterx))
			list.append(getConfigListEntry(_('SecondInfobar Xtraevent:'), config.plugins.Aglare.SecondInfobarXtraevent))
			list.append(getConfigListEntry(_('ChannelSelection Style:'), config.plugins.Aglare.ChannSelector))
			list.append(getConfigListEntry(_('EventView Style:'), config.plugins.Aglare.EventView))
			list.append(getConfigListEntry(_('VolumeBar Style:'), config.plugins.Aglare.VolumeBar))
			list.append(getConfigListEntry(_('Support E2iplayer Skins:'), config.plugins.Aglare.E2iplayerskins))

			section = '---------------------------( APIKEY SKIN SETUP )------------------------'
			list.append(getConfigListEntry(section))

			list.append(getConfigListEntry("API KEY SETUP:", config.plugins.Aglare.actapi, _("Settings Apikey Server")))

			if config.plugins.Aglare.actapi.value:
				for api in api_key_manager.API_CONFIG:
					upper = api.upper()
					list.append(getConfigListEntry(
						f"{upper}:",
						getattr(config.plugins.Aglare, api),
						_(f"Activate/Deactivate {upper}")
					))

					if getattr(config.plugins.Aglare, api).value:
						cfg = api_key_manager.API_CONFIG[api]
						list.append(getConfigListEntry(
							f"-- Load Key {upper}",
							cfg['load_action'],
							_(f"Load from /tmp/{api}key.txt")
						))
						list.append(getConfigListEntry(
							f"-- Set key {upper}",
							cfg['config_entry'],
							_(f"Personal API key for {upper}")
						))

				list.append(getConfigListEntry("ELCINEMA:", config.plugins.Aglare.elcinema, _("Activate/Deactivate ELCINEMA")))
				list.append(getConfigListEntry("GOOGLE:", config.plugins.Aglare.google, _("Activate/Deactivate GOOGLE")))
				list.append(getConfigListEntry("IMDB:", config.plugins.Aglare.imdb, _("Activate/Deactivate IMDB")))
				list.append(getConfigListEntry("MOLOTOV:", config.plugins.Aglare.molotov, _("Activate/Deactivate MOLOTOV")))
				list.append(getConfigListEntry("PROGRAMMETV:", config.plugins.Aglare.programmetv, _("Activate/Deactivate PROGRAMMETV")))
				section = '------------------------------------------------------------------------'
				list.append(getConfigListEntry(section))
				if config.plugins.Aglare.actapi.value:
					list.append(getConfigListEntry(_('Automatic download of poster'), config.plugins.Aglare.pstdown, _("Download favorite list posters with Epg automatically at startup")))
					if config.plugins.Aglare.pstdown.value is True:
						list.append(getConfigListEntry(_('Set Time our - minute for Poster download'), config.plugins.Aglare.pscan_time, _("Configure time for downloading posters")))
					list.append(getConfigListEntry(_('Automatic download of backdrop'), config.plugins.Aglare.bkddown, _("Download favorite list backdrop with Epg automatically at startup")))
					if config.plugins.Aglare.bkddown.value is True:
						list.append(getConfigListEntry(_('Set Time our - minute for Backdrop download'), config.plugins.Aglare.bscan_time, _("Configure time for downloading backdrop")))

			section = '--------------------------( UTILITY SKIN SETUP )------------------------'
			list.append(getConfigListEntry(section))
			list.append(getConfigListEntry(_('Remove all png (poster - backdrop) (OK)'), config.plugins.Aglare.png, _("This operation remove all png from folder device (Poster-Backdrop)")))

			self["config"].list = list
			self["config"].l.setList(list)
		except KeyError:
			print("keyError")

	def Checkskin(self):
		self.session.openWithCallback(
			self.Checkskin2,
			MessageBox,
			_("[Checkskin] This operation checks if the skin has its components (not guaranteed)...\nDo you really want to continue?"),
			MessageBox.TYPE_YESNO
		)

	def Checkskin2(self, answer):
		if answer:
			from .addons import checkskin
			self.check_module = eTimer()
			check = checkskin.check_module_skin()
			try:
				self.check_module_conn = self.check_module.timeout.connect(check)
			except:
				self.check_module.callback.append(check)
			self.check_module.start(100, True)
			self.openVi()

	def openVi(self, callback=''):
		from .addons.File_Commander import File_Commander
		user_log = '/tmp/my_debug.log'
		if fileExists(user_log):
			self.session.open(File_Commander, user_log)

	def GetPicturePath(self):
		returnValue = self['config'].getCurrent()[1].value
		PicturePath = '/usr/lib/enigma2/python/Plugins/Extensions/Aglare/screens/default.jpg'
		if not isinstance(returnValue, str):
			returnValue = PicturePath
		path = '/usr/lib/enigma2/python/Plugins/Extensions/Aglare/screens/' + returnValue + '.jpg'
		if fileExists(path):
			return convert_image(path)
		else:
			return convert_image(PicturePath)

	def UpdatePicture(self):
		self.onLayoutFinish.append(self.ShowPicture)

	def ShowPicture(self, data=None):
		if self["Preview"].instance:
			size = self['Preview'].instance.size()
			if size.isNull():
				size.setWidth(498)
				size.setHeight(280)

			pixmapx = self.GetPicturePath()
			if not fileExists(pixmapx):
				print("Immagine non trovata:", pixmapx)
				return
			png = loadPic(pixmapx, size.width(), size.height(), 0, 0, 0, 1)
			self["Preview"].instance.setPixmap(png)

	def DecodePicture(self, PicInfo=None):
		ptr = self.PicLoad.getData()
		if ptr is not None:
			self["Preview"].instance.setPixmap(ptr)
			self["Preview"].instance.show()
		return

	def UpdateComponents(self):
		self.UpdatePicture()

	def info(self):
		aboutbox = self.session.open(
			MessageBox,
			_("Setup Aglare Skin\nfor Aglare-FHD-Pli v.%s\n\nby Lululla @2020\n\nSupport forum on linuxsat-support.com\n\nSkinner creator: Odem2014 ") % version,
			MessageBox.TYPE_INFO
		)
		aboutbox.setTitle(_("Setup Aglare Skin Info"))

	def removPng(self):
		self.session.openWithCallback(
			self.removPng2,
			MessageBox,
			_("[RemovePng] This operation will remove all PNGs from the device folder (Poster-Backdrop)...\nDo you really want to continue?"),
			MessageBox.TYPE_YESNO
		)

	def removPng2(self, result):
		if result:
			print('from remove png......')
			removePng()
			print('png are removed')
			aboutbox = self.session.open(MessageBox, _('All png are removed from folder!'), MessageBox.TYPE_INFO)
			aboutbox.setTitle(_('Info...'))

	def keyRun(self):
		sel = self["config"].getCurrent()[1]
		if not sel:
			return

		action_map = {
			config.plugins.Aglare.png: self.handle_png,
			**{
				getattr(config.plugins.Aglare, f"load_{api}_api"):
				lambda x=api: self.handle_api_load(x)
				for api in api_key_manager.API_CONFIG
			},
			**{
				getattr(config.plugins.Aglare, f"{api}_api"): self.KeyText
				for api in api_key_manager.API_CONFIG
			}
		}

		handler = action_map.get(sel)
		if handler:
			handler()

	def handle_api_load(self, api, answer=None):
		cfg = api_key_manager.API_CONFIG[api]
		api_file = f"/tmp/{api}key.txt"
		skin_file = getattr(api_key_manager, f"{api}_skin")

		if answer is None:
			if fileExists(api_file):
				file_info = stat(api_file)
				if file_info.st_size > 0:
					self.session.openWithCallback(
						lambda answer: self.handle_api_load(api, answer),
						MessageBox,
						_("Import key %s from %s?") % (api.upper(), api_file)
					)
				else:
					self.session.open(
						MessageBox,
						_("The file %s is empty.") % api_file,
						MessageBox.TYPE_INFO,
						timeout=4
					)
			else:
				self.session.open(
					MessageBox,
					_("The file %s was not found.") % api_file,
					MessageBox.TYPE_INFO,
					timeout=4
				)
		elif answer:
			try:
				with open(api_file, 'r') as f:
					fpage = f.readline().strip()

				if not fpage:
					raise ValueError(_("Key empty"))

				with open(skin_file, "w") as t:
					t.write(fpage)

				cfg['config_entry'].setValue(fpage)
				cfg['config_entry'].save()

				self.session.open(
					MessageBox,
					_("%s key imported!") % api.upper(),
					MessageBox.TYPE_INFO,
					timeout=4
				)

			except Exception as e:
				self.session.open(
					MessageBox,
					_("Error %s: %s") % (api.upper(), str(e)),
					MessageBox.TYPE_ERROR,
					timeout=4
				)

		self.createSetup()

	def handleKeyActions(self):
		self.createSetup()
		self.ShowPicture()
		sel = self["config"].getCurrent()[1]
		if not sel:
			return

		reset_map = {
			config.plugins.Aglare.png: (config.plugins.Aglare.png, self.handle_png),
			**{
				getattr(config.plugins.Aglare, "load_%s_api" % api):
				(getattr(config.plugins.Aglare, "load_%s_api" % api), self.make_api_handler(api))
				for api in api_key_manager.API_CONFIG
			}
		}
		entry_data = reset_map.get(sel)
		if entry_data:
			config_entry, handler = entry_data
			config_entry.setValue(0)
			config_entry.save()
			handler()

	def make_api_handler(self, api):
		def handler():
			self.handle_api_load(api)
		return handler

	def handle_png(self):
		self.removPng()
		config.plugins.Aglare.png.setValue(0)
		config.plugins.Aglare.png.save()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.handleKeyActions()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.handleKeyActions()

	def keyDown(self):
		self['config'].instance.moveSelection(self['config'].instance.moveDown)
		self.createSetup()
		self.ShowPicture()

	def keyUp(self):
		self['config'].instance.moveSelection(self['config'].instance.moveUp)
		self.createSetup()
		self.ShowPicture()

	def changedEntry(self):
		self.item = self["config"].getCurrent()
		for x in self.onChangedEntry:
			x()

	def getCurrentValue(self):
		if self["config"].getCurrent() and len(self["config"].getCurrent()) > 0:
			return str(self["config"].getCurrent()[1].getText())
		return ""

	def getCurrentEntry(self):
		return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

	def keySave(self):
		if not fileExists(self.skinFile + self.version):
			for x in self['config'].list:
				x[1].cancel()
			self.close()
			return

		for x in self['config'].list:
			if len(x) > 1:
				x[1].save()

		config.plugins.Aglare.save()
		configfile.save()

		def append_skin_file(file_path, skin_lines):
			try:
				with open(file_path, 'r') as skFile:
					skin_lines.extend(skFile.readlines())
			except FileNotFoundError:
				print("File not found:", file_path)

		skin_lines = []

		file_paths = [
			self.previewFiles + 'head-' + config.plugins.Aglare.colorSelector.value + '.xml',
			self.previewFiles + 'font-' + config.plugins.Aglare.FontStyle.value + '.xml',
			self.previewFiles + 'infobar-' + config.plugins.Aglare.InfobarStyle.value + '.xml',
			self.previewFiles + 'infobar-' + config.plugins.Aglare.InfobarPosterx.value + '.xml',
			self.previewFiles + 'infobar-' + config.plugins.Aglare.InfobarXtraevent.value + '.xml',
			self.previewFiles + 'infobar-' + config.plugins.Aglare.InfobarDate.value + '.xml',
			self.previewFiles + 'infobar-' + config.plugins.Aglare.InfobarWeather.value + '.xml',
			self.previewFiles + 'secondinfobar-' + config.plugins.Aglare.SecondInfobarStyle.value + '.xml',
			self.previewFiles + 'secondinfobar-' + config.plugins.Aglare.SecondInfobarPosterx.value + '.xml',
			self.previewFiles + 'secondinfobar-' + config.plugins.Aglare.SecondInfobarXtraevent.value + '.xml',
			self.previewFiles + 'channellist-' + config.plugins.Aglare.ChannSelector.value + '.xml',
			self.previewFiles + 'eventview-' + config.plugins.Aglare.EventView.value + '.xml',
			self.previewFiles + 'vol-' + config.plugins.Aglare.VolumeBar.value + '.xml',
			self.previewFiles + 'e2iplayer-' + config.plugins.Aglare.E2iplayerskins.value + '.xml'
		]

		base_file = 'base.xml'
		if config.plugins.Aglare.skinSelector.value == 'base1':
			base_file = 'base1.xml'
		file_paths.append(self.previewFiles + base_file)
		for path in file_paths:
			append_skin_file(path, skin_lines)
		with open(self.skinFile, 'w') as xFile:
			xFile.writelines(skin_lines)
		restartbox = self.session.openWithCallback(self.restartGUI, MessageBox, _('GUI needs a restart to apply a new skin.\nDo you want to Restart the GUI now?'), MessageBox.TYPE_YESNO)
		restartbox.setTitle(_('Restart GUI now?'))

	def restartGUI(self, answer):
		if answer is True:
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close()

	def checkforUpdate(self):
		try:
			fp = ''
			destr = '/tmp/aglarepliversion.txt'
			req = Request('https://raw.githubusercontent.com/popking159/skins/main/aglarepli/aglarepliversion.txt')
			req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
			fp = urlopen(req)
			fp = fp.read().decode('utf-8')
			print('fp read:', fp)
			with open(destr, 'w') as f:
				f.write(str(fp))
				f.seek(0)
			if fileExists(destr):
				with open(destr, 'r') as cc:
					s1 = cc.readline()
					vers = s1.split('#')[0]
					url = s1.split('#')[1]
					version_server = vers.strip()
					self.updateurl = url.strip()
					cc.close()
					if str(version_server) == str(version):
						message = '%s %s\n%s %s\n\n%s' % (
							_('Server version:'), version_server,
							_('Version installed:'), version,
							_('You have the current version Aglare!')
						)
						self.session.open(MessageBox, message, MessageBox.TYPE_INFO)
					elif version_server > version:
						message = '%s %s\n%s %s\n\n%s' % (
							_('Server version:'),  version_server,
							_('Version installed:'), version,
							_('The update is available!\n\nDo you want to run the update now?')
						)
						self.session.openWithCallback(self.update, MessageBox, message, MessageBox.TYPE_YESNO)
					else:
						self.session.open(MessageBox, _('You have version %s!!!') % version, MessageBox.TYPE_ERROR)
		except Exception as e:
			print('error: ', str(e))

	def update(self, answer):
		if answer is True:
			self.session.open(AglareUpdater, self.updateurl)
		else:
			return

	def keyExit(self):
		self.close()


class AglareUpdater(Screen):

	def __init__(self, session, updateurl):
		self.session = session
		skin = '''
			<screen name="AglareUpdater" position="center,center" size="840,260" flags="wfBorder" backgroundColor="background">
				<widget name="status" position="20,10" size="800,70" transparent="1" font="Regular; 40" foregroundColor="foreground" backgroundColor="background" valign="center" halign="left" noWrap="1" />
				<widget source="progress" render="Progress" position="20,120" size="800,20" transparent="1" borderWidth="0" foregroundColor="white" backgroundColor="background" />
				<widget source="progresstext" render="Label" position="209,164" zPosition="2" font="Regular; 28" halign="center" transparent="1" size="400,70" foregroundColor="foreground" backgroundColor="background" />
			</screen>
			'''
		self.skin = skin
		Screen.__init__(self, session)
		self.updateurl = updateurl
		print('self.updateurl', self.updateurl)
		self['status'] = Label()
		self['progress'] = Progress()
		self['progresstext'] = StaticText()
		self.downloading = False
		self.last_recvbytes = 0
		self.error_message = None
		self.download = None
		self.aborted = False
		self.startUpdate()

	def startUpdate(self):
		self['status'].setText(_('Downloading Aglare...'))
		self.dlfile = '/tmp/aglarepli.ipk'
		print('self.dlfile', self.dlfile)
		self.download = downloadWithProgress(self.updateurl, self.dlfile)
		self.download.addProgress(self.downloadProgress)
		self.download.start().addCallback(self.downloadFinished).addErrback(self.downloadFailed)

	def downloadFinished(self, string=""):
		self["status"].setText(_("Installing updates..."))

		package_path = "/tmp/aglarepli.ipk"

		if fileExists(package_path):
			# Install the package
			os_system("opkg install {}".format(package_path))
			os_system("sync")

			# Remove the package
			remove(package_path)
			os_system("sync")

			# Ask user for GUI restart
			restartbox = self.session.openWithCallback(
				self.restartGUI,
				MessageBox,
				_("Aglare update was done!\nDo you want to restart the GUI now?"),
				MessageBox.TYPE_YESNO
			)
			restartbox.setTitle(_("Restart GUI now?"))
		else:
			self["status"].setText(_("Update package not found!"))
			self.session.open(
				MessageBox,
				_("The update file was not found in /tmp.\nUpdate aborted."),
				MessageBox.TYPE_ERROR
			)

	def downloadFailed(self, failure_instance=None, error_message=''):
		text = _('Error downloading files!')
		if error_message == '' and failure_instance is not None:
			error_message = failure_instance.getErrorMessage()
			text += ': ' + error_message
		self['status'].setText(text)
		return

	def downloadProgress(self, recvbytes, totalbytes):
		self['status'].setText(_('Download in progress...'))
		self['progress'].value = int(100 * self.last_recvbytes // float(totalbytes))
		self['progresstext'].text = '%d of %d kBytes (%.2f%%)' % (self.last_recvbytes // 1024, totalbytes // 1024, 100 * self.last_recvbytes // float(totalbytes))
		self.last_recvbytes = recvbytes

	def restartGUI(self, answer=False):
		if answer is True:
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close()


def removePng():
	# Print message indicating the start of PNG and JPG file removal
	print('Removing PNG and JPG files...')
	if exists(path_poster):
		png_files = glob_glob(join(path_poster, "*.png"))
		jpg_files = glob_glob(join(path_poster, "*.jpg"))
		files_to_remove = png_files + jpg_files

		if not files_to_remove:
			print("No PNG or JPG files found in the folder " + path_poster)

		for file in files_to_remove:
			try:
				remove(file)
				print("Removed: " + file)
			except Exception as e:
				print("Error removing " + file + ": " + str(e))
	else:
		print("The folder " + path_poster + " does not exist.")

	if exists(patch_backdrop):
		png_files_backdrop = glob_glob(join(patch_backdrop, "*.png"))
		jpg_files_backdrop = glob_glob(join(patch_backdrop, "*.jpg"))
		files_to_remove_backdrop = png_files_backdrop + jpg_files_backdrop

		if not files_to_remove_backdrop:
			print("No PNG or JPG files found in the folder " + patch_backdrop)
		else:
			for file in files_to_remove_backdrop:
				try:
					remove(file)
					print("Removed: " + file)
				except Exception as e:
					print("Error removing " + file + ": " + str(e))
	else:
		print("The folder " + patch_backdrop + " does not exist.")


def Plugins(**kwargs):
	return PluginDescriptor(
		name='Setup Aglare',
		description=_('Customization tool for Aglare-FHD-PLI Skin'),
		where=PluginDescriptor.WHERE_PLUGINMENU,
		icon='plugin.png',
		fnc=main
	)


def main(session, **kwargs):
	session.open(AglareSetup)


def remove_exif(image_path):
	with Image.open(image_path) as img:
		img.save(image_path, "PNG")


def convert_image(image):
	path = image
	img = Image.open(path)
	img.save(path, "PNG")
	return image
