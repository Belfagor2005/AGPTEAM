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
