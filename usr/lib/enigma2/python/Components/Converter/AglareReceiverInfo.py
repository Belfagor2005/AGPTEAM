from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Converter.Poll import Poll
from os import popen, statvfs, listdir, path

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']


class AglareReceiverInfo(Poll, Converter):
    # Tipi di informazioni (costanti)
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
        
        # Cache per i percorsi di mount
        self.mount_cache = {}
        self.mount_cache_time = 0

    def get_type_from_string(self, type_list):
        """Mappa le stringhe di configurazione ai tipi numerici"""
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
        """Restituisce il testo formattato per la visualizzazione"""
        if self.type == self.HDDTEMP:
            return self.getHddTemp()
        if self.type == self.LOADAVG:
            return self.getLoadAvg()
        
        entry = self.get_info_entry()
        info = self.get_disk_or_mem_info(entry[0])
        return self.format_text(entry[1], info)

    def get_info_entry(self):
        """Restituisce le informazioni sul tipo corrente"""
        return {
            self.MEMTOTAL: (['Mem'], 'Ram'),
            self.MEMFREE: (['Mem'], 'Ram'),
            self.SWAPTOTAL: (['Swap'], 'Swap'),
            self.SWAPFREE: (['Swap'], 'Swap'),
            self.USBINFO: (self.get_mount_points('USB'), 'USB'),
            self.MMCINFO: (self.get_mount_points('MMC'), 'MMC'),
            self.HDDINFO: (['/media/hdd', '/hdd'], 'HDD'),
            self.FLASHINFO: (['/'], 'Flash')
        }.get(self.type, (['/'], 'Unknown'))

    def get_disk_or_mem_info(self, paths):
        """Ottiene le informazioni per dischi o memoria"""
        if self.type in (self.USBINFO, self.MMCINFO, self.HDDINFO, self.FLASHINFO):
            return self.getDiskInfo(paths)
        return self.getMemInfo(paths[0])

    def format_text(self, label, info):
        """Formatta il testo in base alle opzioni"""
        if info[0] == 0:
            return f'{label}: Not Available'
        if self.shortFormat:
            return f'{label}: {self.getSizeStr(info[0])}, in use: {info[3]}%'
        if self.fullFormat:
            return f'{label}: {self.getSizeStr(info[0])} Free:{self.getSizeStr(info[2])} used:{self.getSizeStr(info[1])} ({info[3]}%)'
        return f'{label}: {self.getSizeStr(info[0])} used:{self.getSizeStr(info[1])} Free:{self.getSizeStr(info[2])}'

    @cached
    def getValue(self):
        """Restituisce il valore percentuale per le barre di progresso"""
        if self.type in (self.MEMTOTAL, self.MEMFREE, self.SWAPTOTAL, self.SWAPFREE):
            entry = 'Mem' if self.type in (self.MEMTOTAL, self.MEMFREE) else 'Swap'
            return self.getMemInfo(entry)[3]
        
        if self.type in (self.USBINFO, self.MMCINFO, self.HDDINFO, self.FLASHINFO):
            paths = {
                self.USBINFO: self.get_mount_points('USB'),
                self.MMCINFO: self.get_mount_points('MMC'),
                self.HDDINFO: ['/media/hdd', '/hdd'],
                self.FLASHINFO: ['/']
            }[self.type]
            return self.getDiskInfo(paths)[3]
        
        return 0

    # Proprietà per l'accesso esterno
    text = property(getText)
    value = property(getValue)
    range = 100

    # Funzioni di rilevamento
    def is_mmc_device(self, mount_point):
        """Determina se un punto di mount è un dispositivo MMC"""
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
        except:
            pass
        return False

    def get_mount_points(self, dev_type):
        """Restituisce i punti di mount per un tipo di dispositivo"""
        cache_key = f"{dev_type}_mounts"
        if cache_key in self.mount_cache:
            return self.mount_cache[cache_key]
        
        mount_points = []
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    mount_point = parts[1]
                    
                    if dev_type == 'USB' and ('usb' in mount_point.lower() or '/media/usb' in mount_point):
                        mount_points.append(mount_point)
                    elif dev_type == 'MMC' and self.is_mmc_device(mount_point):
                        mount_points.append(mount_point)
        
        except:
            pass
        
        # Defaults se non trovati
        if not mount_points:
            mount_points = ['/media/mmc'] if dev_type == 'MMC' else ['/media/usb']
        
        self.mount_cache[cache_key] = mount_points
        return mount_points

    # Funzioni di acquisizione dati
    def getHddTemp(self):
        """Ottiene la temperatura dell'HDD"""
        try:
            return popen('hddtemp -n -q /dev/sda 2>/dev/null').readline().strip() + "°C"
        except:
            return "N/A"

    def getLoadAvg(self):
        """Ottiene il carico medio del sistema"""
        try:
            with open('/proc/loadavg', 'r') as f:
                return f.read(15).strip()
        except:
            return "N/A"

    def getMemInfo(self, value):
        """Ottiene le informazioni sulla memoria"""
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
        except:
            pass
        return result

    def getDiskInfo(self, paths):
        """Ottiene le informazioni sul disco"""
        result = [0, 0, 0, 0]
        for pathx in paths:
            try:
                st = statvfs(pathx)
                if st and st.f_blocks > 0:
                    total = st.f_bsize * st.f_blocks
                    free = st.f_bsize * st.f_bavail
                    used = total - free
                    percent = (used * 100) / total
                    return [total, used, free, percent]
            except:
                continue
        return result

    # Funzioni di utilità
    def getSizeStr(self, value, u=0):
        """Formatta le dimensioni in una stringa leggibile"""
        if value <= 0:
            return "0 B"
        
        while value >= 1024 and u < len(SIZE_UNITS) - 1:
            value /= 1024.0
            u += 1
        
        return f"{value:.1f} {SIZE_UNITS[u]}" if value >= 10 else f"{value:.2f} {SIZE_UNITS[u]}"

    def doSuspend(self, suspended):
        """Gestisce la sospensione del polling"""
        self.poll_enabled = not suspended
        if not suspended:
            self.downstream_elements.changed((self.CHANGED_POLL,))
