### AGP (Advanced Graphics Renderer)
** Optimized for Aglare FHD Skin**

[![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-red)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Tested on Aglare FHD](https://img.shields.io/badge/Skin-Aglare_FHD-blueviolet)](https://github.com/Belfagor2005/enigma2-plugin-skins-aglare/main/usr/share/enigma2/Aglare-FHD-PLI)
[![Python package](https://github.com/Belfagor2005/AGPTEAM/actions/workflows/pylint.yml/badge.svg)](https://github.com/Belfagor2005/AGPTEAM/actions/workflows/pylint.yml)
[![](https://komarev.com/ghpvc/?username=Belfagor2005)](https://github.com/Belfagor2005/LinuxsatPanel)  

<img src="https://raw.githubusercontent.com/Belfagor2005/enigma2-plugin-skins-aglare/main/usr/share/enigma2/Aglare-FHD-PLI/picon_default.png?raw=true">

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

### EPG EVENT BACKDROP  
**Infobar (skin.xml)**  
```xml
<screen>
<widget source="session.Event_Now" render="AglareBackdropX" position="100,100" size="680,1000" />
<widget source="session.Event_Next" render="AglareBackdropX" position="100,100" size="680,1000" />
<widget source="session.Event_Now" render="AglareBackdropX" position="100,100" size="680,1000" nexts="2" />
<widget source="session.CurrentService" render="AglareBackdropX" position="100,100" size="680,1000" nexts="3" />
</screen>
```

**CHANNELS**  
```xml
<widget source="ServiceEvent" render="AglareBackdropX" position="100,100" size="680,1000" nexts="1" />
<widget source="ServiceEvent" render="AglareBackdropX" position="100,100" size="185,278" nexts="2" />
```

**EPG EVENT EVENTVIEW**  
```xml
<widget source="Event" render="AglareBackdropX" position="100,100" size="680,1000" />
<widget source="Event" render="AglareBackdropX" position="100,100" size="680,1000" nexts="2" />
```

## INFOEVENT DETAILS  
```xml
<widget source="ServiceEvent" render="AgpInfoEvents"
    position="100,400"
    size="600,300"
    font="Regular;18"
    transparent="1"
    zPosition="5"/>
```

**Plugin Setup**  
```python
config.plugins.Aglare.info_display_mode = ConfigSelection(default="auto", choices=[
    ("auto", _("Automatic")),
    ("tmdb", _("TMDB Only")),
    ("omdb", _("OMDB Only")),
    ("off", _("Off"))
])
```

## PARENTAL RATING  
```xml
<widget render="AgpParentalX"
    source="session.Event_Now"
    position="637,730"
    size="50,50"
    zPosition="3"
    transparent="1"
    alphatest="blend"/>
```

**File Structure**  
```
/usr/share/enigma2/<skin>/parental/
├── FSK_0.png
├── FSK_6.png
├── FSK_12.png
├── FSK_16.png
├── FSK_18.png
└── FSK_UN.png
```
**Plugin Setup**  
```python
config.plugins.Aglare.info_parental_mode = ConfigSelection(default="auto", choices=[
	("auto", _("Automatic")),
	("tmdb", _("TMDB Only")),
	("omdb", _("OMDB Only")),
	("off", _("Off"))
])
```

## GENRE MOVIE  
```xml
<widget render="AgpGenreX"
    source="session.Event_Now"
    position="44,370"
    size="160,45"
    zPosition="22"
    transparent="1" />
```

**File Structure**  
```
Icons
/usr/share/enigma2/<skin>/genre_pic/

├── action.png
├── adventure.png
├── animation.png
├── comedy.png
├── crime.png
├── documentary.png
├── drama.png
├── fantasy.png
├── general.png
├── history.png
├── hobbies.png
├── horror.png
├── kids.png
├── music.png
├── mystery.png
├── news.png
├── romance.png
├── science.png
├── sports.png
├── talk.png
├── thriller.png
├── tvmovie.png
├── war.png
└── western.png
```

**Plugin Setup**  
```python
config.plugins.Aglare.genre_source = ConfigOnOff(default=False)
```

## STAR RATING  
```xml
<widget source="ServiceEvent" render="AgpStarX"
	position="1011,50"
	size="316,27"
	pixmap="skin_default/starsbar_empty.png"
	alphatest="blend"
	transparent="1"
	zPosition="20"/>

<widget source="ServiceEvent" render="AgpStarX"
	position="1011,50"
	size="316,27"
	pixmap="skin_default/starsbar_filled.png"
	alphatest="blend"
	transparent="1"
	zPosition="22"/>
```

**File Structure**  
```
/usr/share/enigma2/<skin>/skin_default/
├── starsbar_empty.png
└── starsbar_filled.png
```

**Plugin Setup**  
```python
config.plugins.Aglare.rating_source = ConfigOnOff(default=False)
```


## EMC*X POSTER (poster local movie)
```xml
<widget source="Service" render="AgpXEMC"
	position="1703,583"
	size="200,300"
	cornerRadius="20"
	zPosition="22"
/>
```

**Plugin Setup**  
```python
config.plugins.Aglare.xemc_poster = ConfigOnOff(default=False)
```


## Aglare-Specific Setup  
1. **API Keys**  
   ```bash
   echo "your_api_key" > /usr/share/enigma2/<your_skin>/tmdb_api
   chmod 644 /usr/share/enigma2/<your_skin>/tmdb_api
   ```
   
**Required API Files**  
```
/usr/share/enigma2/<your_skin>/
├── tmdb_api
├── omdb_api
├── thetvdb_api
└── fanart_api
```

## Troubleshooting  
**Issue**: Images not loading  
```bash
chmod 755 /usr/share/enigma2/AglareFHD
chown root:root /usr/share/enigma2/AglareFHD/tmdb_api
```

**Solution**: Remove Png  
```
Open Plugin Setup and remove all png
```

## Scheduled Downloads  
**Configuration**  
| Value      | Behavior              | Recommended For  |
|------------|-----------------------|-----------------|
| `00:00`    | Midnight update       | 24/7 receivers  |
| `04:30`    | Post-EPG refresh      | Fresh EPG data  |
| `disable`  | Manual mode           | Low-power devices |

```python
# Default system-wide setting
SCAN_TIME = "02:00"  # Global fallback
```

## Performance  
**Cache System**: Auto-purges files >30 days old  
**Memory Management**: Drops kernel caches automatically  


~ 


### AGLARE PLUGIN SETUP CONFIGURATIONS

The Aglare plugin offers numerous configuration options to customize the behavior of the renderers and external services. Below are the main options available.

## 🖼️ **Download Poster/Backdrop**

Configure the immediate or automatic download of posters and backdrops. You can enable the "Download Now" option to download immediately or set up automatic download based on the EPG.

- **Download Now Poster**  
  Enable immediate download of the poster.  
  `config.plugins.Aglare.download_now_poster`
  
- **Download Now Backdrop**  
  Enable immediate download of the backdrop.  
  `config.plugins.Aglare.download_now_backdrop`

- **Automatic Poster Download**  
  Enable automatic download of posters based on the EPG.  
  `config.plugins.Aglare.pstdown`
  
- **Automatic Backdrop Download**  
  Enable automatic download of backdrops based on the EPG.  
  `config.plugins.Aglare.bkddown`

## 🔑 **APIs and Keys**

Aglare supports integration with several APIs to fetch content information. Each API can be enabled/disabled individually.

- **Enable APIs**  
  Enable the use of APIs to retrieve content information.  
  `config.plugins.Aglare.actapi`

- **Available APIs**  
  - **TMDB**  
    Enable/disable the TMDB API.  
    `config.plugins.Aglare.tmdb`
  - **OMDB**  
    Enable/disable the OMDB API.  
    `config.plugins.Aglare.omdb`
  - **TheTVDB**  
    Enable/disable the TheTVDB API.  
    `config.plugins.Aglare.thetvdb`
  - **Fanart**  
    Enable/disable the Fanart API.  
    `config.plugins.Aglare.fanart`
  - **Other APIs**  
    - **Elcinema**  
      Enable/disable Elcinema.  
      `config.plugins.Aglare.elcinema`
    - **Google**  
      Enable/disable Google.  
      `config.plugins.Aglare.google`
    - **IMDB**  
      Enable/disable IMDB.  
      `config.plugins.Aglare.imdb`
    - **Molotov**  
      Enable/disable Molotov.  
      `config.plugins.Aglare.molotov`
    - **Programmetv**  
      Enable/disable Programmetv.  
      `config.plugins.Aglare.programmetv`

- **API Keys**  
  Set the API key for each service:
  - **TMDB API**  
    `config.plugins.Aglare.tmdb_api`
  - **OMDB API**  
    `config.plugins.Aglare.omdb_api`
  - **TheTVDB API**  
    `config.plugins.Aglare.thetvdb_api`

## ⭐ **Additional Features**

- **Rating Stars**  
  Enable the display of rating stars for events.  
  `config.plugins.Aglare.rating_source`
  
- **Parental Icons**  
  Display parental guidance icons for each event.  
  `config.plugins.Aglare.info_parental_mode`

- **Event Information Display**  
  Enable the display of extended event information, including plot, cast, and other metadata.  
  `config.plugins.Aglare.info_display_mode`
  
- **Genre Icons**  
  Enable the display of icons representing event genres (e.g., action, comedy, drama).  
  `config.plugins.Aglare.genre_source`

- **Enhanced Movie Center Poster**  
  Enable the display of posters from the local movie folder.  
  `config.plugins.Aglare.xemc_poster`

## 🗄️ **Cache**

Caching can be enabled to improve performance when downloading events.

- **Enable Cache**  
  Enable or disable caching during event downloads.  
  `config.plugins.Aglare.cache`

## 🧹 **PNG Management**

You can remove all PNG files from the local folder (poster and backdrop).

- **Remove PNG**  
  Remove all PNG files from the folder.  
  `config.plugins.Aglare.png`

## 🕒 **Scan Time**

Set the scan times for automatic poster and backdrop downloads.

- **Poster Scan Time**  
  Set the scan time for automatic poster downloads.  
  `config.plugins.Aglare.pscan_time`
  
- **Backdrop Scan Time**  
  Set the scan time for automatic backdrop downloads.  
  `config.plugins.Aglare.bscan_time`

---


> 💡 **Pro Tip**: Use RAM disk for slow devices  
```python
if os.path.exists("/tmp/AGP"):
    POSTER_FOLDER = "/tmp/AGP"
```

## Credits  
**Developer**: Lululla  
**License**: CC BY-NC-SA 4.0  
**Based on**: digiteng (2021)  
**Discussion on Forum**
https://www.linuxsat-support.com/thread/160662-agp-renderers-now-available-for-all/


> 📌 **Developer Note**:  
> Maintain zPosition 2-5 for AGP components. Commercial use prohibited. Modifications must retain credits.
```
