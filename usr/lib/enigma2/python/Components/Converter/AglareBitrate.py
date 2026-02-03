# based on version by areq 2015-12-13 http://areq.eu.org/
# mod by Fhroma version 12.10.2018
# improved version

from __future__ import absolute_import
from enigma import (
    eConsoleAppContainer,
    eTimer,
    iServiceInformation,
)
from Components.Console import Console
from Components.Converter.Converter import Converter
from Components.Element import cached
import six
from datetime import datetime
from os import path

DBG = False
DEBUG_FILE = '/tmp/AglareComponents.log'
BITRATE_PATH = '/usr/bin/bitrate'

# Cached image type
_image_type = None
_append_to_file = False


def agb_debug(my_text=None, append=True, debug_file=DEBUG_FILE):
    global _append_to_file
    if not debug_file or not my_text:
        return

    try:
        mode = 'a' if _append_to_file and append else 'w'
        _append_to_file = True

        with open(debug_file, mode) as f:
            f.write(f'{datetime.now()}\t{my_text}\n')

        # Rotate log if too big
        if path.getsize(debug_file) > 100000:
            with open(debug_file, 'r+') as f:
                lines = f.readlines()
                f.seek(0)
                f.writelines(lines[10:])
                f.truncate()
    except Exception as e:
        try:
            with open(debug_file, 'a') as f:
                f.write(f'Exception: {e}\n')
        except BaseException:
            pass


def isImageType(img_name=''):
    global _image_type

    if _image_type is None:
        # First try to detect from feed config
        feed_conf = '/etc/opkg/all-feed.conf'
        if path.exists(feed_conf):
            try:
                with open(feed_conf, 'r') as f:
                    content = f.read().lower()
                    if 'vti' in content:
                        _image_type = 'vti'
                    elif 'code.vuplus.com' in content:
                        _image_type = 'vuplus'
                    elif 'openpli-7' in content:
                        _image_type = 'openpli7'
                    elif 'openatv' in content:
                        _image_type = 'openatv'
                        if '/5.3/' in content:
                            _image_type += '5.3'
            except BaseException:
                pass

        # Fallback to directory detection
        if _image_type is None:
            if path.exists(
                    '/usr/lib/enigma2/python/Plugins/SystemPlugins/VTIPanel/'):
                _image_type = 'vti'
            elif path.exists('/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/'):
                _image_type = 'openatv'
            elif path.exists('/usr/lib/enigma2/python/Blackhole'):
                _image_type = 'blackhole'
            elif path.exists('/etc/init.d/start_pkt.sh'):
                _image_type = 'pkt'
            else:
                _image_type = 'unknown'

    return img_name.lower() == _image_type.lower()


class AglareBitrate(Converter, object):
    def __init__(self, type):
        Converter.__init__(self, type)
        self.clear_values()
        self.is_running = False
        self.is_suspended = False
        self.my_console = Console()
        self.container = eConsoleAppContainer()
        self.container.appClosed.append(self.app_closed)
        self.container.dataAvail.append(self.data_avail)

        # Setup timers
        self.start_timer = eTimer()
        self.start_timer.callback.append(self.start)
        self.start_timer.start(100, True)

        self.run_timer = eTimer()
        self.run_timer.callback.append(self.run_bitrate)

        # Ensure bitrate executable has proper permissions
        if path.exists(BITRATE_PATH):
            self.my_console.ePopen(f'chmod 755 {BITRATE_PATH}')

    @cached
    def getText(self):
        if DBG:
            agb_debug(f"[AglareBitrate:getText] vcur {self.vcur}")
        return f'{self.vcur} Kb/s' if self.vcur > 0 else ''

    text = property(getText)

    def doSuspend(self, suspended):
        if DBG:
            agb_debug(
                f"[AglareBitrate:suspended] >>> self.is_suspended={
                    self.is_suspended}, suspended={suspended}")

        if not suspended:
            self.is_suspended = False
            self.start_timer.start(100, True)
        else:
            self.start_timer.stop()
            self.is_suspended = True
            self.my_console.ePopen('killall -9 bitrate', self.clear_values)

    def start(self):
        if not self.is_running:
            if self.source.service:
                if DBG:
                    agb_debug("[AglareBitrate:start] initiate run_timer")
                self.is_running = True
                self.run_timer.start(100, True)
            else:
                if DBG:
                    agb_debug(
                        "[AglareBitrate:start] wait 100ms for self.source.service")
                self.start_timer.start(100, True)

    def run_bitrate(self):
        if DBG:
            agb_debug("[AglareBitrate:run_bitrate] >>>")

        # Default values
        adapter = 0
        demux = 0

        # Get stream data if available
        try:
            stream = self.source.service.stream()
            if stream:
                if DBG:
                    agb_debug(
                        "[AglareBitrate:run_bitrate] Collecting stream data...")
                stream_data = stream.getStreamingData()
                if stream_data:
                    demux = max(stream_data.get('demux', 0), 0)
                    adapter = max(stream_data.get('adapter', 0), 0)
        except Exception as e:
            if DBG:
                agb_debug(
                    f"[AglareBitrate:run_bitrate] Exception collecting stream data: {e}")

        # Get service info
        try:
            info = self.source.service.info()
            vpid = info.getInfo(iServiceInformation.sVideoPID)
            apid = info.getInfo(iServiceInformation.sAudioPID)
        except Exception as e:
            if DBG:
                agb_debug(
                    f"[AglareBitrate:run_bitrate] Exception collecting service info: {e}")
            return

        if vpid >= 0 and apid >= 0:
            if isImageType('vti'):
                cmd = f'killall -9 bitrate > /dev/null 2>&1; nice bitrate {demux} {vpid} {vpid}'
            else:
                cmd = f'killall -9 bitrate > /dev/null 2>&1; nice bitrate {adapter} {demux} {vpid} {vpid}'

            if DBG:
                agb_debug(f'[AglareBitrate:run_bitrate] starting "{cmd}"')
            self.container.execute(cmd)

    def clear_values(self, *args):
        if DBG:
            agb_debug("[AglareBitrate:clear_values] >>>")

        self.is_running = False
        self.vmin = self.vmax = self.vavg = self.vcur = 0
        self.amin = self.amax = self.aavg = self.acur = 0
        self.remaining_data = ''
        self.data_lines = []
        Converter.changed(self, (self.CHANGED_POLL,))

    def app_closed(self, retval):
        if DBG:
            agb_debug(
                f"[AglareBitrate:app_closed] >>> retval={retval}, is_suspended={
                    self.is_suspended}")

        if self.is_suspended:
            self.clear_values()
        else:
            self.run_timer.start(100, True)

    def data_avail(self, data):
        if DBG:
            agb_debug(
                f"[AglareBitrate:data_avail] >>> data '{data}'\n\tself.remaining_data='{
                    self.remaining_data}'")

        # Handle string encoding
        data_str = self.remaining_data + \
            (str(data) if six.PY2 else str(data, 'utf-8', 'ignore'))
        lines = data_str.split('\n')

        # Store incomplete line for next time
        self.remaining_data = lines[-1] if lines[-1] else ''
        lines = lines[:-1] if lines[-1] else lines

        self.data_lines.extend(lines)

        if len(self.data_lines) >= 2:
            try:
                self.vmin, self.vmax, self.vavg, self.vcur = map(
                    int, self.data_lines[0].split())
                self.amin, self.amax, self.aavg, self.acur = map(
                    int, self.data_lines[1].split())
            except ValueError:
                pass

            self.data_lines = []
            Converter.changed(self, (self.CHANGED_POLL,))
