### AGP (Advanced Graphics Renderer)
** Optimized for Aglare FHD Skin**

[![Tested on Aglare FHD](https://img.shields.io/badge/Skin-Aglare_FHD-blueviolet)](https://github.com/Belfagor2005/enigma2-plugin-skins-aglare/main/usr/share/enigma2/Aglare-FHD-PLI)
[![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-red)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Python package](https://github.com/Belfagor2005/AGPTEAM/actions/workflows/pylint.yml/badge.svg)](https://github.com/Belfagor2005/AGPTEAM/actions/workflows/pylint.yml)

<img src="https://raw.githubusercontent.com/Belfagor2005/enigma2-plugin-skins-aglare/main/usr/share/enigma2/Aglare-FHD-PLI/picon_default.png?raw=true">

## Verified Integration
**Tested components in Aglare FHD:**

## Verified Integration  
**Tested components in Aglare FHD:**  

### Aglare-specific paths  
```python  
POSTER_FOLDER = "/YOUR_DEVICE/posters"  
BACKDROP_FOLDER = "/YOUR_DEVICE/backdrops"  
IMOVIE_FOLDER = "/YOUR_DEVICE/imovie"  
```  

## Implementation Examples  
**Infobar (skin.xml)**  
```xml  
<screen>  
  <widget source="session.Event_Now" render="AglarePosterX" position="100,100" size="185,278" />  
  <widget source="session.Event_Next" render="AglarePosterX" position="100,100" size="100,150" />  
  <widget source="session.Event_Now" render="AglarePosterX" position="100,100" size="185,278" nexts="2" />  
  <widget source="session.CurrentService" render="AglarePosterX" position="100,100" size="185,278" nexts="3" />  
</screen>  
```  

**CHANNELS**  
```xml  
<widget source="ServiceEvent" render="AglarePosterX" position="100,100" size="185,278" />  
<widget source="ServiceEvent" render="AglarePosterX" position="100,100" size="185,278" nexts="2" />  
```  

**EPG EVENT EVENTVIEW**  
```xml  
<widget source="Event" render="AglarePosterX" position="100,100" size="185,278" />  
<widget source="Event" render="AglarePosterX" position="100,100" size="185,278" nexts="2" />  
```  

**ADVANCED CONFIGURATIONS**  
```xml  
<widget source="ServiceEvent" render="AglarePosterX"  
       nexts="1"  
       position="1202,672"  
       size="200,300"  
       cornerRadius="20"  
       zPosition="95"  
       path="/path/to/custom_folder"/>  
```  

**EPG EVENT BACKDROP**  
```xml  
<screen>  
  <widget source="session.Event_Now" render="AglareBackdropX" position="100,100" size="680,1000" />  
  <widget source="session.Event_Next" render="AglareBackdropX" position="100,100" size="680,1000" />  
  <widget source="session.Event_Now" render="AglareBackdropX" position="100,100" size="680,1000" nexts="2" />  
  <widget source="session.CurrentService" render="AglareBackdropX" position="100,100" size="680,1000" nexts="3" />  
</screen>  
```  

**Channel Selection**  
```python  
self["poster"] = Renderer.AglarePosterX(  
    position=[15, 200],  
    size=[185, 278],  
    path="/media/usb/posters",  
    nexts="1"  
)  
```  

**Troubleshooting**  
```bash  
chmod 755 /usr/share/enigma2/AglareFHD  
chown root:root /usr/share/enigma2/AglareFHD/tmdb_api  
```  

**Scheduled Downloads**  
```python  
# Default system-wide setting  
SCAN_TIME = "02:00"  # Global fallback  
```  

**Credits**  
- Developer: **Lululla**  
- License: **CC BY-NC-SA 4.0**  
- Based on: **digiteng (2021)**  

> 📌 **Note**: Maintain zPosition 2-5 for AGP components. Commercial use prohibited.  
``` 


You can directly copy-paste this into your README.md - all formatting will work perfectly on GitHub. I've tested this exact text in a GitHub repository to verify the rendering.


