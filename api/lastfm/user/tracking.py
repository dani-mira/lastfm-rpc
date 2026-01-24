import logging

import pylast
from constants.project import API_KEY, API_SECRET, TRANSLATIONS, DEFAULT_COOLDOWN

logger = logging.getLogger('lastfm')

network = pylast.LastFMNetwork(API_KEY, API_SECRET)

class User:
    def __init__(self, username, cooldown=DEFAULT_COOLDOWN):
        self.username = username
        self.lastfm_user = network.get_user(username)
        self.cooldown = cooldown

    def _get_current_track(self):
        try:
            return self.lastfm_user.get_now_playing()
        except pylast.WSError as e:
            if "Invalid API key" in str(e):
                logger.critical("CRITICAL: Invalid API Key. Please update config.yaml with a valid key from Last.fm.")
                import os
                os._exit(1)
            logger.error(f"{TRANSLATIONS['pylast_ws_error'].format(self.cooldown)} | Details: {e}")
        except pylast.NetworkError:
            logger.error(TRANSLATIONS['pylast_network_error'])
        except pylast.MalformedResponseError:
            logger.error(TRANSLATIONS['pylast_malformed_response_error'])
        return None

    def _get_track_info(self, current_track):
        title, artist, album, artwork, time_remaining = None, None, None, None, 0
        try:
            title = current_track.get_title()
            artist = current_track.get_artist()
            album = current_track.get_album()
            if album:
                artwork = album.get_cover_image()
            time_remaining = current_track.get_duration()
        except pylast.WSError as e:
            logger.error(f'pylast.WSError: {e}')
        except pylast.NetworkError:
            logger.error(TRANSLATIONS['pylast_network_error'])
        return title, artist, album, artwork, time_remaining

    def now_playing(self):
        current_track = self._get_current_track()
        if current_track:
            return current_track, self._get_track_info(current_track)
        else:
            logger.debug(TRANSLATIONS['no_song'].format(self.cooldown))
            return current_track, None
