from utils.reader import load_config, load_translations

# Paths
TRANSLATIONS_DIR = "translations"
ASSETS_DIR = "assets"
APP_ICON_PATH = "assets/last_fm.png"

# These will be updated by reload_constants()
USERNAME = ""
API_KEY = ""
API_SECRET = ""
APP_LANG = "en-US"
TRANSLATIONS = {}

def reload_constants():
    """Re-reads config.yaml and updates the global constants and translations."""
    global USERNAME, API_KEY, API_SECRET, APP_LANG
    USERNAME, API_KEY, API_SECRET, APP_LANG = load_config()
    
    # Update translations in-place to preserve references in other modules
    new_translations = load_translations(APP_LANG, TRANSLATIONS_DIR)
    TRANSLATIONS.clear()
    TRANSLATIONS.update(new_translations)

# Perform initial load
reload_constants()

# Project Info
VERSION = "0.0.3"
GITHUB_ORG = "fastfingertips"
GITHUB_REPO = "lastfm-rpc"
GITHUB_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_ORG}/{GITHUB_REPO}/releases/latest"

# Discord Configuration
CLIENT_ID = '702984897496875072'
APP_NAME = "Last.fm Discord Rich Presence"
RPC_LINE_LIMIT = 26
RPC_XCHAR = ' '

# Timings & Limits (Seconds)
RETRY_INTERVAL = 5
MAX_RETRIES = 10
UPDATE_INTERVAL = 2
TRACK_CHECK_INTERVAL = 5
DEFAULT_COOLDOWN = 6

# Remote Assets
DEFAULT_AVATAR_ID = "818148bf682d429dc215c1705eb27b98"
DEFAULT_AVATAR_URL = f"https://lastfm.freetls.fastly.net/i/u/avatar170s/{DEFAULT_AVATAR_ID}.png"
LASTFM_ICON_URL = "https://www.last.fm/static/images/lastfm_avatar_applemusic.b06eb8ad89be.png"
DAY_MODE_COVER = 'https://i.imgur.com/GOVbNaF.png'
NIGHT_MODE_COVER = 'https://i.imgur.com/kvGS4Pa.png'

# URL Templates & Bases
LASTFM_BASE_URL = "https://www.last.fm"
LASTFM_USER_URL = f"{LASTFM_BASE_URL}/user/{{username}}"
LASTFM_LIBRARY_URL = f"{LASTFM_USER_URL}/library"
LASTFM_TRACK_URL_TEMPLATE = f"{LASTFM_USER_URL}/library/music/{{artist}}/_/{{title}}"

# External Search Templates
YT_MUSIC_SEARCH_TEMPLATE = "https://music.youtube.com/search?q={query}"
SPOTIFY_SEARCH_TEMPLATE = "https://open.spotify.com/search/{query}"