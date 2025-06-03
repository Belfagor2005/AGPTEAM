#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import
from datetime import datetime
from os import path
from re import sub
from six import text_type
import unicodedata

try:
    # Python 2 imports
    from urlparse import urljoin, urlparse, urlunparse, urlsplit, urlunsplit, parse_qs, parse_qsl
    from urllib import addinfourl as urllib_addinfourl, quote as urllib_quote, quote_plus as urllib_quote_plus
    from urllib import unquote as urllib_unquote, unquote_plus as urllib_unquote_plus, urlencode as urllib_urlencode
    from urllib import urlopen as urllib_urlopen, urlretrieve as urllib_urlretrieve
    from urllib2 import BaseHandler as urllib2_BaseHandler, build_opener as urllib2_build_opener
    from urllib2 import HTTPCookieProcessor as urllib2_HTTPCookieProcessor, HTTPError as urllib2_HTTPError
    from urllib2 import HTTPHandler as urllib2_HTTPHandler, HTTPRedirectHandler as urllib2_HTTPRedirectHandler
    from urllib2 import HTTPSHandler as urllib2_HTTPSHandler, ProxyHandler as urllib2_ProxyHandler
    from urllib2 import Request as urllib2_Request, URLError as urllib2_URLError, urlopen as urllib2_urlopen
    from urllib2 import install_opener as urllib2_install_opener

except ImportError:
    # Python 3 imports
    from urllib.parse import urljoin, urlparse, urlunparse, urlsplit, urlunsplit, parse_qs, parse_qsl
    from urllib.parse import quote as urllib_quote, quote_plus as urllib_quote_plus
    from urllib.parse import unquote as urllib_unquote, unquote_plus as urllib_unquote_plus, urlencode as urllib_urlencode
    from urllib.request import addinfourl as urllib_addinfourl, build_opener as urllib2_build_opener
    from urllib.request import BaseHandler as urllib2_BaseHandler, HTTPCookieProcessor as urllib2_HTTPCookieProcessor
    from urllib.request import HTTPHandler as urllib2_HTTPHandler, HTTPRedirectHandler as urllib2_HTTPRedirectHandler
    from urllib.request import HTTPSHandler as urllib2_HTTPSHandler, ProxyHandler as urllib2_ProxyHandler
    from urllib.request import Request as urllib2_Request, urlopen as urllib2_urlopen, urlopen as urllib_urlopen
    from urllib.request import urlretrieve as urllib_urlretrieve, install_opener as urllib2_install_opener
    from urllib.error import HTTPError as urllib2_HTTPError, URLError as urllib2_URLError


append2file = False
imageType = None
PYversion = None


def what_python_version():
    import sys
    return sys.version_info[0]

def is_py2():
    global py_version
    if py_version is None:
        if what_python_version() == 3:
            py_version = False
        else:
            py_version = True
    return py_version


def ensure_binary(text, encoding='utf-8', errors='strict'):
    if is_py2():
        return text
    else:
        if isinstance(text, bytes):
            return text
        if isinstance(text, str):
            try:
                return text.encode(encoding, errors)
            except Exception:
                return text.encode(encoding, 'ignore')
    return text


def ensure_str(text, encoding='utf-8', errors='strict'):
    if isinstance(text, str):
        return text
    if isinstance(text, text_type):  # Compatibilità per Python 2 e 3
        try:
            return text.encode(encoding, errors)
        except Exception:
            return text.encode(encoding, 'ignore')
    elif isinstance(text, bytes):
        try:
            return text.decode(encoding, errors)
        except Exception:
            return text.decode(encoding, 'ignore')
    return text


def clear_cache():
    with open("/proc/sys/vm/drop_caches", "w") as f:
        f.write("1\n")


def get_image_type():
    return imageType


def isImageType(img_name=''):
    global imageType
    if imageType is None:
        if path.exists('/etc/opkg/all-feed.conf'):
            with open('/etc/opkg/all-feed.conf', 'r') as file:
                fileContent = file.read().lower()
                if 'vti' in fileContent:
                    imageType = 'vti'
                elif 'code.vuplus.com' in fileContent:
                    imageType = 'vuplus'
                elif 'openpli-7' in fileContent:
                    imageType = 'openpli7'
                elif 'openatv' in fileContent:
                    imageType = 'openatv'
                    if '/5.3/' in fileContent:
                        imageType += '5.3'
    if imageType is None:
        if path.exists('/usr/lib/enigma2/python/Plugins/SystemPlugins/VTIPanel/'):
            imageType = 'vti'
        elif path.exists('/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/'):
            imageType = 'openatv'
        elif path.exists('/usr/lib/enigma2/python/Blackhole'):
            imageType = 'blackhole'
        elif path.exists('/etc/init.d/start_pkt.sh'):
            imageType = 'pkt'
        else:
            imageType = 'unknown'
    return img_name.lower() == imageType.lower()


def agb_debug(mytext=None, append=True, mydebug='/tmp/AglareComponents.log'):
    global append2file

    if not mydebug or not mytext:
        return

    try:
        mode = 'a' if (append2file and append) else 'w'
        append2file = True  # Set global flag on first write

        # Write log entry
        with open(mydebug, mode) as f:
            f.write(f'{datetime.now()}\t{mytext}\n')

        # Rotate if file too large
        if path.getsize(mydebug) > 100000:
            with open(mydebug, 'r+') as f:
                lines = f.readlines()
                f.seek(0)
                f.writelines(lines[10:])  # Keep all but first 10 lines
                f.truncate()

    except Exception as e:
        try:  # Attempt to log the error
            with open(mydebug, 'a') as f:
                f.write(f'{datetime.now()}\tException: {e}\n')
        except:
            print(f'Logging failed: {e}')


def log_missing(
    text: str = None,
    append: bool = True,
    log_file: str = '/tmp/AglareComponents.log',
    max_size_kb: int = 100
) -> None:
    """Log messages with timestamp and automatic log rotation.

    Args:
        text: Message to log
        append: Whether to append to existing log
        log_file: Path to log file
        max_size_kb: Maximum log size in KB before rotation
    """
    if not text or not log_file:
        return

    try:
        # Write log entry
        mode = 'a' if append else 'w'
        with open(log_file, mode) as f:
            f.write(f'{datetime.now()}\t{text}\n')

        # Rotate if file too large (convert KB to bytes)
        if path.getsize(log_file) > max_size_kb * 1024:
            with open(log_file, 'r+') as f:
                lines = f.readlines()
                f.seek(0)
                f.writelines(lines[10:])  # Keep all but first 10 lines
                f.truncate()

    except Exception as e:
        # Try to log the error, fall back to print if that fails
        try:
            with open(log_file, 'a') as f:
                f.write(f'{datetime.now()}\tLOG ERROR: {e}\n')
        except Exception as e:
            print(f'Logging failed: {e}')


def is_inet_working(addr='8.8.8.8', port=53):
    try:
        import socket
        if addr[:1].isdigit():
            addr = socket.gethostbyname(addr)
        socket.setdefaulttimeout(0.5)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((addr, port))
        return True
    except Exception as e:
        print(e)
        pass
    return False


def CHname_2_piconName(serName, iptvStream=False):
    piconName = serName.lower()
    if iptvStream:
        piconName = piconName.replace(' fhd', ' hd').replace(' uhd', ' hd')
    piconName = unicodedata.normalize('NFKD', text_type(piconName, 'utf_8', errors='ignore')).encode('ASCII', 'ignore')
    piconName = sub('[^a-z0-9]', '', piconName.replace('&', 'and').replace('+', 'plus').replace('*', 'star'))
    return piconName
