from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Converter.Poll import Poll
from os import popen, statvfs, listdir, path

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']


class AglareReceiverInfo(Poll, Converter):
    HDDTEMP = 0
    LOADAVG = 1
    MEMTOTAL = 2
    MEMFREE = 3
    SWAPTOTAL = 4
    SWAPFREE = 5
    USBINFO = 6
    HDDINFO = 7
    FLASHINFO = 8
    MMCINFO = 9

    def __init__(self, type):
        Converter.__init__(self, type)
        Poll.__init__(self)
        type = type.split(',')
        self.shortFormat = 'Short' in type
        self.fullFormat = 'Full' in type
        self.type = self.get_type_from_string(type)
        self.poll_interval = 5000 if self.type in (
            self.FLASHINFO, self.HDDINFO, self.MMCINFO, self.USBINFO) else 1000
        self.poll_enabled = True

    def get_type_from_string(self, type_list):
        type_mapping = {
            'HddTemp': self.HDDTEMP,
            'LoadAvg': self.LOADAVG,
            'MemTotal': self.MEMTOTAL,
            'MemFree': self.MEMFREE,
            'SwapTotal': self.SWAPTOTAL,
            'SwapFree': self.SWAPFREE,
            'UsbInfo': self.USBINFO,
            'HddInfo': self.HDDINFO,
            'MmcInfo': self.MMCINFO,
        }
        return next((v for k, v in type_mapping.items() if k in type_list), self.FLASHINFO)

    @cached
    def getText(self):
        if self.type == self.HDDTEMP:
            return self.getHddTemp()
        if self.type == self.LOADAVG:
            return self.getLoadAvg()

        entry = self.get_info_entry()
        info = self.get_disk_or_mem_info(entry[0])
        return self.format_text(entry[1], info)

    def get_info_entry(self):
        return {
            self.MEMTOTAL: ('Mem', 'Ram'),
            self.MEMFREE: ('Mem', 'Ram'),
            self.SWAPTOTAL: ('Swap', 'Swap'),
            self.SWAPFREE: ('Swap', 'Swap'),
            self.USBINFO: ('/media/usb', 'USB'),
            self.MMCINFO: ('/media/mmc', 'MMC'),
            self.HDDINFO: ('/media/hdd', 'HDD'),
            self.FLASHINFO: ('/', 'Flash')
        }.get(self.type, ('/', 'Unknown'))

    def get_disk_or_mem_info(self, paths):
        if self.type in (self.USBINFO, self.MMCINFO, self.HDDINFO, self.FLASHINFO):
            return self.getDiskInfo(paths)
        return self.getMemInfo(paths)

    def format_text(self, label, info):
        if info[0] == 0:
            return f'{label}: Not Available'
        if self.shortFormat:
            return f'{label}: {self.getSizeStr(info[0])}, in use: {info[3]}%'
        if self.fullFormat:
            return f'{label}: {self.getSizeStr(info[0])} Free:{self.getSizeStr(info[2])} used:{self.getSizeStr(info[1])} ({info[3]}%)'
        return f'{label}: {self.getSizeStr(info[0])} used:{self.getSizeStr(info[1])} Free:{self.getSizeStr(info[2])}'

    @cached
    def getValue(self):
        result = 0
        if self.type in (self.MEMTOTAL, self.MEMFREE, self.SWAPTOTAL, self.SWAPFREE):
            entry = {
                self.MEMTOTAL: 'Mem', self.MEMFREE: 'Mem',
                self.SWAPTOTAL: 'Swap', self.SWAPFREE: 'Swap'
            }[self.type]
            result = self.getMemInfo(entry)[3]

        elif self.type in (self.USBINFO, self.MMCINFO, self.HDDINFO, self.FLASHINFO):
            path = {
                self.USBINFO: '/media/usb', self.HDDINFO: '/media/hdd',
                self.MMCINFO: '/media/mmc', self.FLASHINFO: '/'
            }[self.type]
            result = self.getDiskInfo(path)[3]
        return result

    text = property(getText)
    value = property(getValue)
    range = 100

    def is_mmc_device(self, mount_point):
        try:
            # 1. Controlla se il percorso contiene parole chiave MMC
            mp_lower = mount_point.lower()
            if any(kw in mp_lower for kw in ['mmc', 'sd', 'card', 'emmc']):
                return True

            # 2. Analizza i dispositivi in /sys/block
            for device in listdir('/sys/block'):
                if device.startswith('mmcblk') and path.ismount(mount_point):
                    device_path = path.join('/dev', device)
                    with open('/proc/mounts') as f:
                        if any(device_path in line and mount_point in line for line in f):
                            return True
        except BaseException:
            pass
        return False

    def getHddTemp(self):
        try:
            return popen('hddtemp -n -q /dev/sda 2>/dev/null').readline().strip() + "°C"
        except BaseException:
            return "N/A"

    def getLoadAvg(self):
        try:
            with open('/proc/loadavg', 'r') as f:
                return f.read(15).strip()
        except BaseException:
            return "N/A"

    def getMemInfo(self, value):
        result = [0, 0, 0, 0]
        try:
            with open('/proc/meminfo', 'r') as fd:
                mem_data = fd.read()

            total = int(mem_data.split(f'{value}Total:')[1].split()[0]) * 1024
            free = int(mem_data.split(f'{value}Free:')[1].split()[0]) * 1024

            if total > 0:
                used = total - free
                percent = (used * 100) / total
                result = [total, used, free, percent]
        except BaseException:
            pass
        return result

    def getDiskInfo(self, path):
        result = [0, 0, 0, 0]
        if self.is_mount_point(path):
            try:
                st = statvfs(path)
                if st and 0 not in (st.f_bsize, st.f_blocks):
                    result[0] = st.f_bsize * st.f_blocks
                    result[2] = st.f_bsize * st.f_bavail
                    result[1] = result[0] - result[2]
                    result[3] = (result[1] * 100) / result[0]
            except BaseException:
                pass
        return result

    def is_mount_point(self, path):
        try:
            with open('/proc/mounts', 'r') as fd:
                for line in fd:
                    parts = line.split()
                    if len(parts) > 1 and parts[1] == path:
                        return True
        except BaseException:
            pass
        return False

    def getSizeStr(self, value, u=0):
        if value <= 0:
            return "0 B"

        while value >= 1024 and u < len(SIZE_UNITS) - 1:
            value /= 1024.0
            u += 1

        return f"{value:.1f} {SIZE_UNITS[u]}" if value >= 10 else f"{value:.2f} {SIZE_UNITS[u]}"

    def doSuspend(self, suspended):
        self.poll_enabled = not suspended
        if not suspended:
            self.downstream_elements.changed((self.CHANGED_POLL,))
