import datetime
import logging

from api.lastfm.user.library import get_library_data
from api.lastfm.user.profile import get_user_data
from pypresence.presence import Presence
from pypresence import exceptions
from utils.url_utils import url_encoder
from constants.project import (
    CLIENT_ID, 
    DAY_MODE_COVER, NIGHT_MODE_COVER,
    RPC_LINE_LIMIT, RPC_XCHAR,
    LASTFM_TRACK_URL_TEMPLATE, YT_MUSIC_SEARCH_TEMPLATE
)

logger = logging.getLogger('rpc')

class DiscordRPC:
    def __init__(self):
        """
        Initializes the DiscordRPC class.
        
        Sets up the state variables. The actual Presence object is initialized
        when enable() is called.
        """
        self.RPC = None
        self._enabled = False
        self._disabled = True
        self.start_time = None
        self.last_track = None
        self.connection_time = None
        self.current_artist = None
        self.artist_scrobbles = 0

    @property
    def is_connected(self):
        """Returns whether the RPC is currently connected and active."""
        return self._enabled and not self._disabled

    def _connect(self):
        """
        Establishes a connection to Discord.
        """
        if not self._enabled:
            try:
                if self.RPC is None:
                    self.RPC = Presence(CLIENT_ID)
                
                self.RPC.connect()
                self.connection_time = datetime.datetime.now()
                logger.info('Connected with Discord')
                self._enabled = True
                self._disabled = False
            except exceptions.DiscordNotFound:
                logger.warning('Discord not found, will retry in next cycle')
            except Exception as e:
                logger.error(f'Error connecting to Discord: {e}')

    def _disconnect(self):
        """
        Disconnects from Discord.
        
        Clears the current RPC state, closes the connection, and updates state variables.
        """
        if not self._disabled and self.RPC:
            self.RPC.clear()  # Clear the current RPC state
            self.RPC.close()  # Close the connection to Discord
            self.connection_time = None
            logger.info('Disconnected from Discord due to inactivity on Last.fm')
            self._disabled = True
            self._enabled = False

    def enable(self):
        """
        Connects to Discord if not already connected.
        
        Checks if the connection to Discord is not already enabled. If not, it 
        establishes the connection.
        """
        self._connect()

    def disable(self):
        """
        Disconnects from Discord.
        
        Checks if the connection to Discord is not already disabled. If not, 
        it clears the current RPC state and closes the connection.
        """
        self._disconnect()

    def _format_image_text(self, lines, limit, xchar):
        """Processes and formats text for RPC images while strictly preserving comments."""
        logger.debug(f"Format Text: {list(lines.keys())}")
        result_text = ''
        
        for line_key in lines:
            line = f'{lines[line_key]} '
            if line_key in ['theme', 'artist_scrobbles', 'first_time']:
                # Processing logic for large image lines
                if len(lines) == 1: 
                    result_text = line
                else:
                    """
                    line_suffix = "" if len(line) > 20 else (line_limit - len(line) - sum(_.isupper() for _ in line))*xchar
                    rpc_large_image_text += f'{line}{line_suffix} '
                    """
                    result_text += f'{line}{(limit - len(line) - sum(c.isupper() for c in line))*xchar} '
            else:
                # Processing logic for small image lines
                line_suffix = "" if len(line) > 20 else (limit - len(line) - sum(c.isupper() for c in line))*xchar
                result_text += f'{line}{line_suffix} '
        
        # if the text is too long, cut it
        if len(result_text) > 128:
            result_text = result_text.replace(xchar, '')
            
        return result_text

    def _prepare_artwork_status(self, artwork, artist_count, library_data):
        """Handles artwork fallback and library scrobble counts."""
        large_image_lines = {}
        
        # artwork
        if artwork is None:
            # if there is no artwork, use the default one
            now = datetime.datetime.now()
            #day: false, night: true
            is_day = now.hour >= 18 or now.hour < 9 
            artwork = DAY_MODE_COVER if is_day else NIGHT_MODE_COVER
            large_image_lines['theme'] = f"{'Night' if is_day else 'Day'} Mode Cover"

        if artist_count:
            # if the artist is in the library
            track_count = library_data["track_count"]
            large_image_lines["artist_scrobbles"] = f'Scrobbles: {artist_count}/{track_count}' if track_count else f'Scrobbles: {artist_count}'
        else:
            large_image_lines['first_time'] = 'First time listening!'
            
        return artwork, large_image_lines

    def _prepare_buttons(self, username, artist, title, album):
        """
        Compiles the RPC buttons.
        
        Alternative button templates for future use:
        - Spotify: {"label": "Search on Spotify", "url": str(SPOTIFY_SEARCH_TEMPLATE.format(query=url_encoder(album)))}
        - track_url: {"label": "View Track", "url": str(f"https://www.last.fm/music/{url_encoder(artist)}/{url_encoder(title)}")}
        - user_url: {"label": "View Last.fm Profile", "url": str(LASTFM_USER_URL.format(username=username))}
        """
        return [
            {"label": "View Track", "url": str(LASTFM_TRACK_URL_TEMPLATE.format(username=username, artist=url_encoder(artist), title=url_encoder(title)))},
            {"label": "Search on YouTube Music", "url": str(YT_MUSIC_SEARCH_TEMPLATE.format(query=url_encoder(album)))}
        ]

    def update_status(self, track, title, artist, album, time_remaining, username, artwork):
        # logger.debug(f"Update: track={track}, title={title}, artist={artist}, album={album}, time={time_remaining}")

        if len(title) < 2:
            title = title + ' '

        if self.last_track == track and self.current_artist is not None:
            # if the track is the same as the last track AND we already have stats, don't update
            return

        # Pre-process status flags
        album_bool = album is not None
        time_remaining_bool = time_remaining > 0
        if time_remaining_bool:
            time_remaining = float(str(time_remaining)[0:3])

        logger.info(f'Album: {album} | Time Remaining: {time_remaining_bool} - {time_remaining} | Now Playing: {track}')

        self.start_time = datetime.datetime.now().timestamp()
        self.last_track = track
        track_artist_album = f'{artist} - {album}'

        # 1. Fetch Data
        user_data = get_user_data(username)
        if not user_data:
            logger.error(f"User data not found for {username}")
            return
        
        logger.info(f"User data found for {username}")
        logger.debug(f"User data: {user_data}")

        library_data = get_library_data(username, artist, title)
        if not library_data:
            logger.error(f"Library data not found for {username}")
            return
        
        logger.info(f"Library data found for {username}")
        logger.debug(f"Library data: {library_data}")

        # 2. Prepare Display Data
        rpc_buttons = self._prepare_buttons(username, artist, title, album)


        # Unpack User Info
        user_display_name = user_data["display_name"]
        scrobbles, artists, loved_tracks = user_data["header_status"] # unpacking
        artist_count = library_data["artist_count"]

        small_image_lines = {
            'name':         f"{user_display_name} (@{username})",
            "scrobbles":    f'Scrobbles: {scrobbles}',
            "artists":      f'Artists: {artists}',
            "loved_tracks": f'Loved Tracks: {loved_tracks}'}

        # Handle artwork and large image lines via helper
        artwork, large_image_lines = self._prepare_artwork_status(artwork, artist_count, library_data)

        # Call the helper for text processing
        rpc_small_image_text = self._format_image_text(small_image_lines, RPC_LINE_LIMIT, RPC_XCHAR)
        rpc_large_image_text = self._format_image_text(large_image_lines, RPC_LINE_LIMIT, RPC_XCHAR)

        self.current_artist = artist
        self.artist_scrobbles = artist_count

        update_assets = {
            'details': title,
            'buttons': rpc_buttons,
            'small_image': user_data["avatar_url"],
            'small_text': rpc_small_image_text,
            'large_text': rpc_large_image_text,
            # situation-dependent assets
            'large_image': 'artwork' if not time_remaining_bool and not album_bool else artwork,
            'state': track_artist_album if time_remaining_bool and not album_bool else artist,
            'end': time_remaining + self.start_time if time_remaining_bool else None}

        # logging
        state = 'with album' if album_bool else 'without album'
        time_state = 'time' if time_remaining_bool else 'no time'
        logger.debug(f'Update state: {state}, {time_state}')

        if self.RPC:
            try:
                self.RPC.update(**update_assets)
            except Exception as e:
                logger.error(f'Error updating RPC: {e}')
