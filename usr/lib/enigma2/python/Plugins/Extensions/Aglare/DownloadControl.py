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

from Screens.MessageBox import MessageBox
from twisted.internet import reactor
import threading
import gettext

_ = gettext.gettext
poster_auto_db = None
backdrop_auto_db = None
poster_lock = threading.Lock()
backdrop_lock = threading.Lock()


def startPosterAutoDB(providers, session=None):
    from Components.Renderer.AglarePosterX import PosterAutoDB
    global poster_auto_db
    with poster_lock:
        try:
            if session and not hasattr(session, 'open'):
                raise AttributeError("No Valid Session for l'UI")

            if poster_auto_db and poster_auto_db.is_alive():
                poster_auto_db.stop()
                poster_auto_db.join(2.0)

            poster_auto_db = PosterAutoDB(providers=providers)
            poster_auto_db.daemon = True
            poster_auto_db.start()
            poster_auto_db._execute_immediate_scan()

        except Exception as e:
            if session:
                reactor.callFromThread(
                    session.open,
                    MessageBox,
                    _("Download error: {}").format(str(e)),
                    MessageBox.TYPE_ERROR
                )
            print(f"PosterAutoDB init error: {str(e)}")
            raise


def startBackdropAutoDB(providers, session=None):
    from Components.Renderer.AglareBackdropX import BackdropAutoDB
    global backdrop_auto_db
    with backdrop_lock:
        try:
            if session and not hasattr(session, 'open'):
                raise AttributeError("No Valid Session for l'UI")

            if backdrop_auto_db and backdrop_auto_db.is_alive():
                backdrop_auto_db.stop()
                backdrop_auto_db.join(2.0)

            backdrop_auto_db = BackdropAutoDB(providers=providers)
            backdrop_auto_db.daemon = True
            backdrop_auto_db.start()
            backdrop_auto_db._execute_immediate_scan()
        except Exception as e:
            print(f"BackdropAutoDB init error: {str(e)}")
            if session:
                reactor.callFromThread(
                    session.open,
                    MessageBox,
                    _("Download error: {}").format(str(e)),
                    MessageBox.TYPE_ERROR
                )
            raise
