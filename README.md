AGP (Advanced Graphics Renderer) - Technical Overview

1. System Overview for PYTHON3
AGP (Advanced Graphics Renderer) is an advanced multimedia information system designed for Enigma2-based set-top boxes (Dreambox, VU+, etc.). 
It provides a fast and configurable way to display:

Posters (movie/TV show covers)
Backdrops (background images)
EPG metadata (event information)
Team/Channel logos

The system is optimized for Python 3 and integrates with multiple online APIs (TMDB, TVDB, Fanart.tv, etc.) to fetch media dynamically.

2. Key Features
2.1 Dynamic Media Fetching
Multiple API Support:

TMDB (The Movie Database)

TVDB (The TV Database)

Fanart.tv

Google Images (fallback)

Smart Caching:

Stores downloaded images locally (/media/hdd/poster, /media/hdd/backdrop)

Auto-cleans old files to save disk space

2.2 High Performance
Threaded Downloads: Prevents UI freezing.

Lazy Loading: Only loads images when needed.

Memory Optimization: Cleans cache periodically (MemClean()).

2.3 Flexible Configuration

Skin-Controlled:

Widgets can be placed anywhere in the skin.

Supports different sizes (185x278, 342x514, etc.).

API Key Management:

Can be set via files (/usr/share/enigma2/<skin>/tmdb_api).

Fallback to default keys if custom ones aren’t provided.

2.4 Scheduled Updates
Auto-Download at Specified Time:


<!-- Example widget configuration -->
<widget 
    source="ServiceEvent" 
    render="AglarePosterX" 
    position="100,100" 
    size="185,278" 
    scan_time="02:00"  <!-- Downloads new posters at 2 AM -->
    service.tmdb="true" <!-- Enable TMDB -->
    service.tvdb="false" <!-- Disable TVDB -->
/>


3. Supported Widgets
3.1 Poster Renderer (AglarePosterX)
Displays poster images for EPG events.

Usage Examples:

<!-- For current event -->
<widget source="session.Event_Now" render="AglarePosterX" position="100,100" size="185,278" />

<!-- For next event -->
<widget source="session.Event_Next" render="AglarePosterX" position="300,100" size="185,278" nexts="1" />

<!-- Custom path -->
<widget source="Event" render="AglarePosterX" position="500,100" size="185,278" path="/media/usb/posters" />


3.2 Backdrop Renderer (AglareBackdropX)
Displays background images (full-screen or custom size).

Usage Examples:

<!-- Fullscreen backdrop -->
<widget source="session.Event_Now" render="AglareBackdropX" position="0,0" size="1280,720" />

<!-- Mini-backdrop for channel list -->
<widget source="ServiceEvent" render="AglareBackdropX" position="1200,600" size="200,120" />

4. Technical Implementation
4.1 Core Components
Component	Description
AgpDownloadThread	Handles API requests & downloads.
PosterAutoDB / BackdropAutoDB	Manages caching & auto-updates.
RequestAgent	Smart HTTP client with retry logic.
MediaStorage	Manages storage paths & disk space.
4.2 Smart Search Logic
Title Cleaning: Removes unwanted text (e.g., S01E02, (2024)).
Fallback Providers: If TMDB fails, tries TVDB → Fanart → Google.
Multi-Language Support: Detects system language (config.osd.language).

5. Credits & Licensing
Developed by: AGP Team (Lululla)

License: CC BY-NC-SA 4.0 (Attribution-NonCommercial-ShareAlike)

Original Concept: Based on digiteng (2021-2022) but heavily enhanced.

⚠️ Usage Restrictions:

Commercial use prohibited without permission.

Modifications must retain credit headers.

6. Performance & Optimization
Fast Rendering: Uses ePixmap for hardware-accelerated image display.

Low Disk Usage: Auto-purges files older than 30 days.

Memory-Friendly: Drops caches (/proc/sys/vm/drop_caches) when needed.

7. Conclusion
AGP is a highly optimized solution for Enigma2 devices that enhances EPG visualization with dynamic media fetching, smart caching, and skin-friendly customization. Its scheduled download feature ensures fresh content without manual intervention, making it ideal for Kodi-like EPG experiences on embedded systems.

For support, visit:
🔗 GitHub Repository

Appendix: Example Configurations
Minimal Poster Widget

<widget source="Event" render="AglarePosterX" position="100,100" size="185,278" />

Advanced Backdrop Widget

<widget 
    source="ServiceEvent" 
    render="AglareBackdropX" 
    position="0,0" 
    size="1280,720" 
    cornerRadius="10" 
    zPosition="-1" 
    scan_time="03:00" 
    service.tmdb="true" 
    service.fanart="true" 
/>

This documentation reflects AGP v3.5.0 (2025).
Last Modified: 2025-04-01
AGP Team © 2025 - All rights reserved.