# -*- coding: utf-8 -*-

# by 2boom 2011-14
# last update 18.01.2014

from Components.Converter.Converter import Converter
from Components.Element import cached


class AglareFrontendInfo(Converter, object):
    BER = 0
    SNR = 1
    AGC = 2
    LOCK = 3
    SNRdB = 4
    SLOT_NUMBER = 5
    TUNER_TYPE = 6
    SNR_ANALOG = 7
    AGC_ANALOG = 8

    def __init__(self, type):
        Converter.__init__(self, type)
        event_map = {
            "BER": self.BER,
            "SNR": self.SNR,
            "SNRdB": self.SNRdB,
            "AGC": self.AGC,
            "NUMBER": self.SLOT_NUMBER,
            "TYPE": self.TUNER_TYPE,
            "SNR_ANALOG": self.SNR_ANALOG,
            "AGC_ANALOG": self.AGC_ANALOG
        }
        self.type = event_map.get(type, self.LOCK)

    @cached
    def getText(self):
        assert self.type not in (
            self.LOCK, self.SLOT_NUMBER), "the text output of FrontendInfo cannot be used for lock info"
        percent = None
        if self.type == self.BER:
            count = self.source.ber
            return str(count) if count else "N/A"
        elif self.type == self.AGC:
            percent = self.source.agc
        elif self.type == self.SNR:
            percent = self.source.snr
        elif self.type == self.SNRdB:
            if self.source.snr_db:
                return "%3.01f dB" % (self.source.snr_db / 100.0)
            elif self.source.snr:
                return "%3.01f dB" % (
                    0.32 * ((self.source.snr * 100) / 65536.0) / 2)
        elif self.type == self.TUNER_TYPE:
            return self.source.frontend_type or "Unknown"
        return f"{percent * 100 / 65536.0} %" if percent else "N/A"

    @cached
    def getBool(self):
        assert self.type in (
            self.LOCK, self.BER), "the boolean output of FrontendInfo can only be used for lock or BER info"
        if self.type == self.LOCK:
            return self.source.lock or False
        return self.source.ber > 0

    @cached
    def getValue(self):
        assert self.type != self.LOCK, "the value/range output of FrontendInfo cannot be used for lock info"
        _local = 0
        if self.type == self.AGC:
            return self.source.agc or 0
        elif self.type == self.AGC_ANALOG:
            if self.source.agc is None:
                return 50
            _local = int(((self.source.agc * 60) / 65536.0) / 3)
            return max(50, min(60, _local + 50)
                       ) if _local < 10 else _local - 10
        elif self.type == self.SNR:
            return self.source.snr or 0
        elif self.type == self.SNR_ANALOG:
            if self.source.snr is None:
                return 50
            _local = int(((self.source.snr * 60) / 65536.0) / 3)
            return max(50, min(60, _local + 50)
                       ) if _local < 10 else _local - 10
        elif self.type == self.BER:
            return min(self.BER, self.range)
        elif self.type == self.TUNER_TYPE:
            return {"DVB-S": 0, "DVB-C": 1,
                    "DVB-T": 2}.get(self.source.frontend_type, -1)
        elif self.type == self.SLOT_NUMBER:
            return self.source.slot_number or -1

    range = 65536
    value = property(getValue)


# Eg. use example
"""
<screen
    name="FrontendInfoScreen"
    position="center,center"
    size="1280,720"
    title="Frontend Information">

    <!-- Widget per mostrare la qualità del segnale SNR -->
    <widget
        name="snr"
        source="ServiceEvent"
        render="Label"
        position="50,100"
        size="1180,50"
        font="Bold; 26"
        backgroundColor="background"
        transparent="1"
        noWrap="1"
        zPosition="1"
        foregroundColor="green"
        valign="center">
        <convert type="AglareFrontendInfo">SNR</convert>
    </widget>

    <!-- Widget per mostrare il valore AGC -->
    <widget
        name="agc"
        source="ServiceEvent"
        render="Label"
        position="50,160"
        size="1180,50"
        font="Bold; 26"
        backgroundColor="background"
        transparent="1"
        noWrap="1"
        zPosition="1"
        foregroundColor="yellow"
        valign="center">
        <convert type="AglareFrontendInfo">AGC</convert>
    </widget>

    <!-- Widget per mostrare la tipologia di tuner -->
    <widget
        name="tunerType"
        source="ServiceEvent"
        render="Label"
        position="50,220"
        size="1180,50"
        font="Bold; 26"
        backgroundColor="background"
        transparent="1"
        noWrap="1"
        zPosition="1"
        foregroundColor="blue"
        valign="center">
        <convert type="AglareFrontendInfo">TYPE</convert>
    </widget>

    <!-- Widget per mostrare il BER -->
    <widget
        name="ber"
        source="ServiceEvent"
        render="Label"
        position="50,280"
        size="1180,50"
        font="Bold; 26"
        backgroundColor="background"
        transparent="1"
        noWrap="1"
        zPosition="1"
        foregroundColor="red"
        valign="center">
        <convert type="AglareFrontendInfo">BER</convert>
    </widget>

</screen>

"""
