from Components.Renderer.Renderer import Renderer
from Components.VariableText import VariableText
from enigma import eLabel, eTimer
import os
import re

class AglareECMInfoRenderer(Renderer, VariableText):
    def __init__(self):
        Renderer.__init__(self)
        VariableText.__init__(self)
        self.poll_timer = eTimer()
        self.poll_timer.timeout.get().append(self.poll)
        self.poll_interval = 2000
        self.debug = False
        
    GUI_WIDGET = eLabel
    
    def onShow(self):
        self.poll_timer.start(self.poll_interval)
        self.changed(None)
        
    def onHide(self):
        self.poll_timer.stop()
        
    def poll(self):
        self.changed(None)
        
    def debug_log(self, message):
        if self.debug:
            print(f"[ECMInfoRenderer] {message}")
            
    def get_ecm_data(self):
        ecm_info = {}
        try:
            if not os.path.exists("/tmp/ecm.info"):
                return None
                
            if os.path.getsize("/tmp/ecm.info") <= 0:
                return {}
                
            with open("/tmp/ecm.info", "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    key_mapping = {
                        "caid": ["caid", "ca"],
                        "pid": ["pid", "prog_id"],
                        "prov": ["prov", "provid", "provider_id"],
                        "chid": ["chid", "channel_id"],
                        "reader": ["reader", "readername", "card"],
                        "protocol": ["protocol", "using"],
                        "from": ["from", "address", "server"],
                        "hops": ["hops", "hop"],
                        "ecm time": ["ecm time", "response time", "ecm_time", "time"],
                        "cw0": ["cw0", "cw", "cw 0"],
                        "cw1": ["cw1", "cw 1"],
                        "system": ["system", "card_system"],
                        "provider": ["provider", "provname"]
                    }
                    
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        std_key = None
                        for std, aliases in key_mapping.items():
                            if key in aliases:
                                std_key = std
                                break
                                
                        if std_key is None:
                            std_key = key
                            
                        if std_key == "from":
                            if ":" in value:
                                server, port = value.split(":", 1)
                                ecm_info["server"] = server.strip()
                                ecm_info["port"] = port.strip()
                            else:
                                ecm_info["server"] = value
                        elif std_key in ["cw0", "cw1"]:
                            value = " ".join(value.split())
                            
                        ecm_info[std_key] = value
                        
                    elif " " in line:
                        parts = line.split()
                        key = parts[0].lower()
                        value = " ".join(parts[1:])
                        
                        std_key = None
                        for std, aliases in key_mapping.items():
                            if key in aliases:
                                std_key = std
                                break
                                
                        if std_key is None:
                            std_key = key
                            
                        if std_key in ["cw0", "cw1"]:
                            value = " ".join(value.split())
                            
                        ecm_info[std_key] = value
        except Exception as e:
            self.debug_log(f"Error reading ecm.info: {str(e)}")
        return ecm_info
    
    def format_hex(self, value):
        try:
            if value.startswith("0x"):
                value = value[2:]
            return "%0.4X" % int(value, 16)
        except BaseException:
            return value
            
    def format_provider(self, prov):
        try:
            if prov.startswith("0x"):
                prov = prov[2:]
            return "%0.6X" % int(prov, 16)
        except BaseException:
            return prov
            
    def changed(self, what):
        if self.instance:
            ecm_info = self.get_ecm_data()
            lines = []
            
            if ecm_info is None:
                self.text = "Free to Air"
                return
                
            if not ecm_info:
                self.text = "Waiting for ECM data..."
                return
                
            # Define all possible fields with their labels and keys
            possible_fields = [
                ("System", "system"),
                ("Protocol", "protocol"),
                ("Reader", "reader"),
                ("Address", lambda: ecm_info.get("from", 
                                  f"{ecm_info.get('server','N/A')}:{ecm_info.get('port','')}" 
                                  if ecm_info.get('server') else "N/A")),
                ("CAID", "caid"),
                ("PID", "pid"),
                ("Provider", "prov"),
                ("Provider Name", "provider"),
                ("CHID", "chid"),
                ("Hops", "hops"),
                ("ECM Time", "ecm time"),
                ("CW0", "cw0"),
                ("CW1", "cw1")
            ]
            
            # Only include fields that have valid values
            for label, key in possible_fields:
                try:
                    if callable(key):
                        value = key()
                    else:
                        value = ecm_info.get(key, "N/A")
                        if key in ["caid", "pid"]:
                            value = self.format_hex(value)
                        elif key == "prov":
                            value = self.format_provider(value)
                    
                    # Skip fields with "N/A" or empty values
                    if value in ["N/A", ""]:
                        continue
                        
                    lines.append(f"{label}: {value}")
                except Exception as e:
                    self.debug_log(f"Error processing {label}: {str(e)}")
                    # Don't show lines that caused errors
            
            self.text = "\n".join(lines)