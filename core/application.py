import asyncio
import logging
import threading
import webbrowser
import sys
import os
from tkinter import messagebox

from pystray import Icon, Menu, MenuItem
from PIL import Image

from constants.project import (
    USERNAME, APP_NAME, 
    APP_ICON_PATH, 
    TRACK_CHECK_INTERVAL, UPDATE_INTERVAL,
    LASTFM_USER_URL
)
from utils.string_utils import messenger
from api.lastfm.user.tracking import User
from api.discord.rpc import DiscordRPC

logger = logging.getLogger('app')

class App:
    def __init__(self):
        self.rpc = DiscordRPC()
        self.current_track_name = messenger('no_track')
        self._rpc_connected = False
        self.debug_enabled = logging.getLogger().getEffectiveLevel() == logging.DEBUG
        self.icon_tray = self.setup_tray_icon()
        self.loop = asyncio.new_event_loop()
        self.rpc_thread = threading.Thread(target=self.run_rpc, args=(self.loop,))
        self.rpc_thread.daemon = True
        self.update_event = threading.Event()
        self.cached_track_data = None # Store (current_track, data) for forced updates

    def exit_app(self, icon, item):
        """Stops the system tray icon and exits the application."""
        logger.info("Exiting application.")
        icon.stop()
        sys.exit()

    def toggle_debug(self, icon, item):
        """Toggles between DEBUG and INFO logging levels."""
        self.debug_enabled = not self.debug_enabled
        new_level = logging.DEBUG if self.debug_enabled else logging.INFO
        logging.getLogger().setLevel(new_level)
        
        # Also update for existing handlers if necessary (though usually inherited)
        for handler in logging.getLogger().handlers:
            handler.setLevel(new_level)
            
        logger.info(f"Logging level set to: {'DEBUG' if self.debug_enabled else 'INFO'}")

    def open_profile(self, icon, item):
        """Opens the user's Last.fm profile in the default browser."""
        url = LASTFM_USER_URL.format(username=USERNAME)
        webbrowser.open(url)
        logger.info(f"Opened Last.fm profile: {url}")

    def get_directory(self):
        """Returns the project root directory."""
        if getattr(sys, 'frozen', False):
            # If running as an executable
            return os.path.dirname(sys.executable)
        
        # When running as a script, get the parent of 'core' directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.dirname(current_dir)

    def load_icon(self, directory):
        """Loads the application icon from the assets directory."""
        try:
            return Image.open(os.path.join(directory, APP_ICON_PATH))
        except FileNotFoundError:
            messagebox.showerror(messenger('err'), messenger('err_assets'))
            sys.exit(1)

    def _get_dynamic_discord_status(self, item):
        """Returns the current Discord status text for the menu."""
        is_connected = self.rpc.is_connected
        if is_connected and self.rpc.connection_time:
            time_str = self.rpc.connection_time.strftime("%H:%M")
            status_detail = messenger('connected_with_time', time_str)
        else:
            status_detail = messenger('connected') if is_connected else messenger('disconnected')
        return messenger('discord_status', status_detail)
        
    def toggle_display_option(self, option):
        """Toggles a display option for the Discord RPC."""
        current = getattr(self.rpc, option)
        setattr(self.rpc, option, not current)
        # Force update on next cycle by resetting track
        self.rpc.last_track = None 
        if self.icon_tray:
            self.icon_tray.menu = self.setup_tray_menu()
            
        logger.info(f"Toggled option '{option}' to {not current}. Triggering update.")
        # Trigger immediate update
        # Trigger immediate update
        self.update_event.set()

    def set_small_image_option(self, option):
        """Sets the active small image source (Radio Button behavior)."""
        # Define mutually exclusive options
        options = ['use_custom_profile_image', 'use_default_icon', 'use_lastfm_icon']
        
        if option not in options:
            return

        # Disable all others, enable the selected one
        for opt in options:
            setattr(self.rpc, opt, opt == option)
            
        # Force update
        self.rpc.last_track = None 
        if self.icon_tray:
            self.icon_tray.menu = self.setup_tray_menu()
            
        logger.info(f"Set small image source to '{option}'. Triggering update.")
        self.update_event.set()

    def set_large_image_option(self, show_scrobbles):
        """Sets the mode for large image text (Radio Button behavior)."""
        # If show_scrobbles is True, we show scrobbles. If False, we fall back to Album Name.
        is_changing = self.rpc.show_artist_scrobbles_large != show_scrobbles
        if not is_changing:
            return

        self.rpc.show_artist_scrobbles_large = show_scrobbles
        
        # Force update
        self.rpc.last_track = None 
        if self.icon_tray:
            self.icon_tray.menu = self.setup_tray_menu()
            
        logger.info(f"Set large image mode to {'Scrobbles' if show_scrobbles else 'Album Name'}. Triggering update.")
        self.update_event.set()

    def _get_dynamic_artist_stats(self, item):
        """Returns the current artist scrobble stats for the menu."""
        # logger.debug(f"Menu stats check: Artist={self.rpc.current_artist}, Scrobbles={self.rpc.artist_scrobbles}")
        if self.rpc.current_artist:
            count = self.rpc.artist_scrobbles if self.rpc.artist_scrobbles is not None else "..."
            return messenger('artist_scrobbles', [self.rpc.current_artist, count])
        
        # Fallback if track is detected but stats (artist name) not yet confirmed
        if self.current_track_name != messenger('no_track'):
            return messenger('stats_loading')
        return messenger('stats_idle')

    def setup_tray_menu(self):
        """Creates and returns the tray menu with dynamic items."""
        return Menu(
            MenuItem(messenger('user', USERNAME), self.open_profile),
            MenuItem(lambda item: self.current_track_name, None, enabled=False),
            # Display stats item
            MenuItem(
                self._get_dynamic_artist_stats, 
                None, 
                enabled=False
            ),
            MenuItem(self._get_dynamic_discord_status, None, enabled=False),
            Menu.SEPARATOR,
            
            # Small Image Options
            MenuItem(messenger('menu_small_image_options'), Menu(
                MenuItem(messenger('menu_show_small_image'), lambda item: self.toggle_display_option('show_small_image'), checked=lambda item: self.rpc.show_small_image),
                Menu.SEPARATOR,
                MenuItem(messenger('menu_use_custom_profile_image'), lambda item: self.set_small_image_option('use_custom_profile_image'), checked=lambda item: self.rpc.use_custom_profile_image, enabled=self.rpc.show_small_image),
                MenuItem(messenger('menu_use_default_icon'), lambda item: self.set_small_image_option('use_default_icon'), checked=lambda item: self.rpc.use_default_icon, enabled=self.rpc.show_small_image),
                MenuItem(messenger('menu_use_lastfm_icon'), lambda item: self.set_small_image_option('use_lastfm_icon'), checked=lambda item: self.rpc.use_lastfm_icon, enabled=self.rpc.show_small_image),
                Menu.SEPARATOR,
                MenuItem(messenger('menu_show_username'), lambda item: self.toggle_display_option('show_username'), checked=lambda item: self.rpc.show_username, enabled=self.rpc.show_small_image),
                MenuItem(messenger('menu_show_scrobbles'), lambda item: self.toggle_display_option('show_scrobbles'), checked=lambda item: self.rpc.show_scrobbles, enabled=self.rpc.show_small_image),
                MenuItem(messenger('menu_show_artists'), lambda item: self.toggle_display_option('show_artists'), checked=lambda item: self.rpc.show_artists, enabled=self.rpc.show_small_image),
                MenuItem(messenger('menu_show_loved'), lambda item: self.toggle_display_option('show_loved'), checked=lambda item: self.rpc.show_loved, enabled=self.rpc.show_small_image)
            )),
            
            # Large Image Options
            MenuItem(messenger('menu_large_image_options'), Menu(
                MenuItem(messenger('menu_show_artist_scrobbles'), lambda item: self.set_large_image_option(True), checked=lambda item: self.rpc.show_artist_scrobbles_large),
                MenuItem(messenger('menu_show_album_name'), lambda item: self.set_large_image_option(False), checked=lambda item: not self.rpc.show_artist_scrobbles_large)
            )),
            
            Menu.SEPARATOR,
            MenuItem(messenger('debug_mode'), self.toggle_debug, checked=lambda item: self.debug_enabled),
            MenuItem(messenger('exit'), self.exit_app)
        )

    def setup_tray_icon(self):
        """Sets up the initial system tray icon."""
        directory = self.get_directory()
        icon_img = self.load_icon(directory)
        
        return Icon(
            APP_NAME,
            icon=icon_img,
            title=APP_NAME,
            menu=self.setup_tray_menu()
        )

    def _handle_active_track(self, current_track, data):
        """Handle the case where a track is playing."""
        title, artist, album, artwork, time_remaining = data
        formatted_track = f"{artist} - {title}"
        new_track_display = messenger('now_playing', formatted_track)
        
        # 1. IMMEDIATE UI UPDATE
        self.rpc.enable() 
        
        has_track_changed = self.current_track_name != new_track_display
        has_conn_changed = self._rpc_connected != self.rpc.is_connected
        
        if has_track_changed or has_conn_changed:
            self.current_track_name = new_track_display
            self._rpc_connected = self.rpc.is_connected
            logger.info(f"Status: {self.current_track_name} | Discord: {self._rpc_connected}")
            self.icon_tray.title = f"{APP_NAME}\n{new_track_display}"
        else:
            logger.debug(f"Polling: {formatted_track}")

        # 2. HEAVY DATA UPDATE
        self.rpc.update_status(
            str(current_track),
            str(title),
            str(artist),
            str(album),
            time_remaining,
            USERNAME,
            artwork
        )
        
        # 3. Refresh menu if changed
        if has_track_changed or has_conn_changed:
            self.icon_tray.menu = self.setup_tray_menu()

    def _handle_no_track(self):
        """Handle the case where no track is playing."""
        if self.current_track_name != messenger('no_track') or self._rpc_connected != self.rpc.is_connected:
            self.current_track_name = messenger('no_track')
            self._rpc_connected = self.rpc.is_connected
            logger.info(f"Tray Update: No track detected | Discord: {self._rpc_connected}")
            self.icon_tray.title = f"{APP_NAME}\n{self.current_track_name}"
        self.rpc.disable()

    def run_rpc(self, loop):
        """Runs the RPC updater in a loop."""
        logger.info(messenger('starting_rpc'))
        asyncio.set_event_loop(loop)
        user = User(USERNAME)

        while True:
            # Check if this iteration was triggered by an event (settings change)
            is_forced_update = self.update_event.is_set()
            self.update_event.clear()
            
            try:
                # If forced update and we have cached data, reuse it without polling Last.fm
                if is_forced_update and self.cached_track_data:
                    current_track, data = self.cached_track_data
                else:
                    # Normal poll cycle
                    current_track, data = user.now_playing()
                    if data:
                        self.cached_track_data = (current_track, data)
                
                if data:
                    self._handle_active_track(current_track, data)
                    if self.update_event.wait(TRACK_CHECK_INTERVAL):
                        continue # If event set, restart loop immediately
                else:
                    self._handle_no_track()
                    self.cached_track_data = None
                    if self.update_event.wait(UPDATE_INTERVAL):
                        continue
            except Exception as e:
                logger.error(f"Unexpected error in RPC loop: {e}", exc_info=True)
                if self.update_event.wait(UPDATE_INTERVAL):
                    continue
            
            # Additional small sleep if needed to prevent hot loop in case of errors, 
            # but wait() handles the interval. 
            # Logic: If wait returns True (event set), we continue. 
            # If wait returns False (timeout), loop continues naturally.

    def _on_setup(self, icon):
        """Callback to start backend tasks once the icon is running."""
        # Show a notification safely
        try:
            icon.visible = True
            # Startup notification removed as per request
        except Exception as e:
            logger.warning(f"Failed to set icon visibility: {e}")

        # Start the background thread
        logger.info("Starting RPC background thread...")
        self.rpc_thread.start()

    def run(self):
        """Starts the system tray application."""
        logger.info("Starting system tray icon...")
        try:
            # icon.run is blocking. The setup argument runs a function in a new thread
            # or after initialization depending on the platform.
            self.icon_tray.run(setup=self._on_setup)
        except Exception as e:
            logger.error(f"System tray icon failed to run: {e}", exc_info=True)
        finally:
            logger.info("Application loop finished.")
