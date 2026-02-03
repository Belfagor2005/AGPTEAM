# -*- coding: utf-8 -*-

from __future__ import division
from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached
from typing import List, Callable
import time

# 2025.04.01 @ lululla fix


class AglareCpuUsage(Converter, object):
    CPU_ALL = -2
    CPU_TOTAL = -1

    def __init__(self, type):
        Converter.__init__(self, type)
        self.percentlist = []
        self._last_info = None
        self._cached_text = ""
        self.pfmt = "%3d%%"
        self.sfmt = ' $0'
        self.type = self.CPU_TOTAL  # Default

        if type:
            if type == "Total":
                pass  # Use defaults
            elif type.isdigit():
                self.type = int(type)
                self.sfmt = f"${type}"
                self.pfmt = "%d"
            else:
                self.type = self.CPU_ALL
                self.sfmt = str(type)
                self._validate_placeholders()

    def _validate_placeholders(self):
        """Validate placeholders in sfmt against available CPUs"""
        cpus = cpuUsageMonitor.getCpusCount()
        if cpus > -1:
            pos = 0
            while True:
                pos = self.sfmt.find("$", pos)
                if pos == -1:
                    break
                if (pos < len(self.sfmt) - 1 and
                        self.sfmt[pos + 1].isdigit() and
                        int(self.sfmt[pos + 1]) > cpus):
                    self.sfmt = self.sfmt.replace(
                        f"${self.sfmt[pos + 1]}", "n/a")
                pos += 1

    def doSuspend(self, suspended):
        if suspended:
            cpuUsageMonitor.disconnectCallback(self.gotPercentage)
        else:
            cpuUsageMonitor.connectCallback(self.gotPercentage)

    def gotPercentage(self, list):
        self.percentlist = list
        self.changed((self.CHANGED_POLL,))

    @cached
    def getText(self):
        if not hasattr(
                self,
                '_last_info') or self._last_info != self.percentlist:
            self._last_info = self.percentlist.copy() if self.percentlist else []
            res = self.sfmt[:]
            for i in range(len(self.percentlist)):
                res = res.replace(f"${i}", self.pfmt % self.percentlist[i])
            res = res.replace("$?", f"{len(self.percentlist) - 1}")
            self._cached_text = res
        return self._cached_text

    @cached
    def getValue(self):
        try:
            if self.type in range(len(self.percentlist)):
                return self.percentlist[self.type]
            return self.percentlist[0] if self.percentlist else 0
        except (IndexError, TypeError):
            return 0

    text = property(getText)
    value = property(getValue)
    range = 100


class CpuUsageMonitor(Poll, object):
    def __init__(self):
        Poll.__init__(self)
        self.__callbacks: List[Callable[[List[int]], None]] = []
        self.__curr_info: List[List[int]] = self.getCpusInfo()
        self.poll_interval = 1000  # 1 second instead of 500ms
        self._last_poll_time = 0

    def getCpusCount(self) -> int:
        return len(self.__curr_info) - 1 if self.__curr_info else 0

    def getCpusInfo(self) -> List[List[int]]:
        res = []
        try:
            with open("/proc/stat", "r") as fd:
                for line in fd:
                    if line.startswith("cpu"):
                        parts = line.split()
                        try:
                            values = list(map(int, parts[1:]))
                            total = sum(values)
                            busy = total - values[3] - \
                                values[4]  # idle + iowait
                            res.append([parts[0], total, busy])
                        except (ValueError, IndexError) as e:
                            print(f"Error parsing CPU stats: {e}")
                            continue
        except IOError as e:
            print(f"Failed to read /proc/stat: {e}")
        return res

    def poll(self):
        now = time.time()
        if now - self._last_poll_time < self.poll_interval / 1000:
            return

        self._last_poll_time = now
        prev_info, self.__curr_info = self.__curr_info, self.getCpusInfo()

        if not self.__callbacks:
            return

        info = []
        for curr, prev in zip(self.__curr_info, prev_info):
            try:
                delta_total = curr[1] - prev[1]
                delta_busy = curr[2] - prev[2]
                p = 100 * delta_busy // delta_total if delta_total != 0 else 0
                info.append(p)
            except (IndexError, TypeError) as e:
                print(f"Error calculating CPU delta: {e}")
                info.append(0)

        # Copy to avoid modification during iteration
        for callback in self.__callbacks[:]:
            try:
                callback(info)
            except Exception as e:
                print(f"Callback failed: {e}")
                self.__callbacks.remove(callback)

    def connectCallback(self, func: Callable[[List[int]], None]) -> None:
        if func not in self.__callbacks:
            self.__callbacks.append(func)
        if not self.poll_enabled:
            self.poll()
            self.poll_enabled = True

    def disconnectCallback(self, func: Callable[[List[int]], None]) -> None:
        if func in self.__callbacks:
            self.__callbacks.remove(func)
        if not self.__callbacks and self.poll_enabled:
            self.poll_enabled = False


cpuUsageMonitor = CpuUsageMonitor()


# esempi
"""
<!-- Esempio 1: Mostra solo la CPU totale -->
<widget source="global.CpuUsage" render="Label" position="100,100" size="200,25" font="Regular;18">
    <convert type="AglareCpuUsage">Total</convert>
</widget>

<!-- Esempio 2: Mostra un core specifico (es. core 0) -->
<widget source="global.CpuUsage" render="Label" position="100,130" size="200,25" font="Regular;18">
    <convert type="AglareCpuUsage">0</convert>
</widget>

<!-- Esempio 3: Formato personalizzato con placeholders -->
<widget source="global.CpuUsage" render="Label" position="100,160" size="300,25" font="Regular;18">
    <convert type="AglareCpuUsage">Core0: $0% | Core1: $1%</convert>
</widget>
"""

# Versione con Progress Bar:
"""
<!-- Esempio 4: Barra di avanzamento per la CPU totale -->
<widget source="global.CpuUsage" render="Progress" position="100,190" size="200,10" borderWidth="1">
    <convert type="AglareCpuUsage">Total</convert>
</widget>
"""
# Per funzionare, devi registrare la sorgente globale (in un plugin o
# nello skin):
"""
from Components.Converter.AglareCpuUsage import AglareCpuUsage
from Components.Sources.StaticText import StaticText

def setupCpuUsageSource():
    from enigma import ePythonConfig
    cpu_source = StaticText()
    cpu_source.text = "CPU"
    ePythonConfig.globalCpuUsage = cpu_source
"""
