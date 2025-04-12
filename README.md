# AGP (Advanced Graphics Renderer)
** Optimized for Aglare FHD Skin**

[![Tested on Aglare FHD](https://img.shields.io/badge/Skin-Aglare_FHD-blueviolet)](https://github.com/Belfagor2005/enigma2-plugin-skins-aglare/main/usr/share/enigma2/Aglare-FHD-PLI)

[![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-red)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Python package](https://github.com/Belfagor2005/AGPTEAM/actions/workflows/pylint.yml/badge.svg)](https://github.com/Belfagor2005/AGPTEAM/actions/workflows/pylint.yml)

<img src="https://raw.githubusercontent.com/Belfagor2005/enigma2-plugin-skins-aglare/main/usr/share/enigma2/Aglare-FHD-PLI/picon_default.png?raw=true">

## Verified Integration
**Tested components in Aglare FHD:**
```python
# Aglare-specific paths
POSTER_FOLDER = "/YOUR_DEVICE/posters"
BACKDROP_FOLDER = "/YOUR_DEVICE/backdrops"
```

## Implementation Examples
** Infobar (skin.xml)**
```xml
<widget source="session.Event_Now" render="AglarePosterX" position="100,100" size="185,278" />
<widget source="session.Event_Next" render="AglarePosterX" position="100,100" size="100,150" />
<widget source="session.Event_Now" render="AglarePosterX" position="100,100" size="185,278" nexts="2" />
<widget source="session.CurrentService" render="AglarePosterX" position="100,100" size="185,278" nexts="3" />
</screen>
```
### CHANNELS
```xml
<widget source="ServiceEvent" render="AglarePosterX" position="100,100" size="185,278" />
<widget source="ServiceEvent" render="AglarePosterX" position="100,100" size="185,278" nexts="2" />
```

### EPG EVENT EVENTVIEW
```xml
<widget source="Event" render="AglarePosterX" position="100,100" size="185,278" />
<widget source="Event" render="AglarePosterX" position="100,100" size="185,278" nexts="2" />
```
# or/and put tag -->  path="/media/hdd/poster"

### ADVANCED CONFIGURATIONS:
```xml
<widget source="ServiceEvent" render="AglarePosterX"
       nexts="1"
       position="1202,672"
       size="200,300"
       cornerRadius="20"
       zPosition="95"
       path="/path/to/custom_folder"  <!-- Optional -->
       service.tmdb="true"            <!-- Enable TMDB -->
       service.tvdb="false"           <!-- Disable TVDB -->
       service.imdb="false"           <!-- Disable IMDB -->
       service.fanart="false"         <!-- Disable Fanart -->
       service.google="false"         <!-- Disable Google -->
       scan_time="00:00"              <!-- Set the start time for backdrop download -->
/>
```


### EPG EVENT EVENTVIEW BACKDROP

### Infobar (skin.xml)
```xml
<widget source="session.Event_Now" render="AglareBackdropX" position="100,100" size="680,1000" />
<widget source="session.Event_Next" render="AglareBackdropX" position="100,100" size="680,1000" />
<widget source="session.Event_Now" render="AglareBackdropX" position="100,100" size="680,1000" nexts="2" />
<widget source="session.CurrentService" render="AglareBackdropX" position="100,100" size="680,1000" nexts="3" />
```

### CHANNELS
```xml
<widget source="ServiceEvent" render="AglareBackdropX" position="100,100" size="680,1000" nexts="2" />
<widget source="ServiceEvent" render="AglareBackdropX" position="100,100" size="185,278" nexts="2" />
```

### EPG EVENT EVENTVIEW
```xml
<widget source="Event" render="AglareBackdropX" position="100,100" size="680,1000" />
<widget source="Event" render="AglareBackdropX" position="100,100" size="680,1000" nexts="2" />
```
*or put tag -->  path="/media/hdd/backdrop"

# ADVANCED CONFIGURATIONS
```xml
<widget source="ServiceEvent" render="AglareBackdropX"
       nexts="1"
       position="1202,672"
       size="200,300"
       cornerRadius="20"
       zPosition="95"
       path="/path/to/custom_folder"  <!-- Optional -->
       service.tmdb="true"            <!-- Enable TMDB -->
       service.tvdb="false"           <!-- Disable TVDB -->
       service.imdb="false"           <!-- Disable IMDB -->
       service.fanart="false"         <!-- Disable Fanart -->
       service.google="false"         <!-- Disable Google -->
       scan_time="02:00"              <!-- Set the start time for backdrop download -->
/>
```


### Channel Selection
```python
self["poster"] = Renderer.AglarePosterX(
    position=[15, 200],
    size=[185, 278],
    path="/media/usb/posters",
    nexts="1"  # Show next event
)
```

## Aglare-Specific Setup
1. **API Keys**:  
   Create in `/usr/share/enigma2/AglareFHD/`:
   ```bash
   echo "your_api_key" > tmdb_api
   chmod 644 tmdb_api
   ```

2. **Custom Paths** (in `Agp_Utils.py`):
```python
if cur_skin == "AglareFHD":
    POSTER_FOLDER = "/media/usb/AGP/posters"  # USB for performance
    SCAN_TIME = "00:00"  # After EPG updates
```

## Troubleshooting
**Issue**: Images not loading  
**Solution**: Verify permissions:
```bash
chmod 755 /usr/share/enigma2/AglareFHD
chown root:root /usr/share/enigma2/AglareFHD/tmdb_api
```

**Issue**: Slow HDD performance  
**Solution**: Use RAM disk:
```python
if os.path.exists("/tmp/AGP"):
    POSTER_FOLDER = "/tmp/AGP"  # For slow devices
```

> 📌 **Developer Note**:  
> Aglare FHD uses zPosition 2-5 for AGP components. Avoid conflicts with other renderers.


**Configuration**:
## API Keys Setup
Create files in /usr/share/enigma2/<your_skin>/:

	tmdb_api → Your TMDB API key
	omdb_api → Fanart.tv key
	thetvdb_api → Your TMDB API key
	fanart_api → Fanart.tv key	

Or edit Agp_apikeys.py directly.

# Performance
**Cache System**: Auto-purges files >30 days old

**Memory Management**: Drops kernel caches automatically


## Credits
**Developer**: Lululla

**License**: CC BY-NC-SA 4.0

**Based on**: digiteng (2021) with major enhancements

**Note**: Commercial use prohibited. Modifications must retain credits.


