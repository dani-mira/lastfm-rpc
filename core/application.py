import asyncio
import logging
import threading
import webbrowser
import time
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

    def _get_dynamic_artist_stats(self, item):
        """Returns the current artist scrobble stats for the menu."""
        if self.rpc.current_artist:
            count = self.rpc.artist_scrobbles if self.rpc.artist_scrobbles else "..."
            return messenger('artist_scrobbles', [self.rpc.current_artist, count])
        return "" # Hidden if returning empty string and handled below

    def setup_tray_menu(self):
        """Creates and returns the tray menu with dynamic items."""
        return Menu(
            MenuItem(messenger('user', USERNAME), self.open_profile),
            MenuItem(lambda item: self.current_track_name, None, enabled=False),
            # Use visible=lambda to hide scrobbles when not available
            MenuItem(
                self._get_dynamic_artist_stats, 
                None, 
                enabled=False, 
                visible=lambda item: self.rpc.current_artist is not None
            ),
            MenuItem(self._get_dynamic_discord_status, None, enabled=False),
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

    def run_rpc(self, loop):
        """Runs the RPC updater in a loop."""
        logger.info(messenger('starting_rpc'))
        asyncio.set_event_loop(loop)
        user = User(USERNAME)

        while True:
            try:
                current_track, data = user.now_playing()
                
                if data:
                    title, artist, album, artwork, time_remaining = data
                    formatted_track = f"{artist} - {title}"
                    new_track_display = messenger('now_playing', formatted_track)
                    
                    # 1. First update the status and internal variables
                    self.rpc.enable()
                    self.rpc.update_status(
                        str(current_track),
                        str(title),
                        str(artist),
                        str(album),
                        time_remaining,
                        USERNAME,
                        artwork
                    )

                    # 2. Check if we need to refresh the tray menu or title
                    # We check: track name change OR connection status change OR scrobble count change
                    has_track_changed = self.current_track_name != new_track_display
                    has_conn_changed = self._rpc_connected != self.rpc.is_connected
                    
                    if has_track_changed or has_conn_changed:
                        self.current_track_name = new_track_display
                        self._rpc_connected = self.rpc.is_connected
                        
                        logger.info(f"Status: {self.current_track_name} | Discord: {self._rpc_connected}")
                        
                        # Update tooltip info (safer than replacing the whole menu)
                        self.icon_tray.title = f"{APP_NAME}\n{new_track_display}"
                    else:
                        logger.debug(f"Polling: {formatted_track}")
                    
                    time.sleep(TRACK_CHECK_INTERVAL)
                else:
                    if self.current_track_name != messenger('no_track') or self._rpc_connected != self.rpc.is_connected:
                        self.current_track_name = messenger('no_track')
                        self._rpc_connected = self.rpc.is_connected
                        logger.info(f"Tray Update: No track detected | Discord: {self._rpc_connected}")
                        self.icon_tray.title = f"{APP_NAME}\n{self.current_track_name}"
                    self.rpc.disable()
            except Exception as e:
                logger.error(f"Unexpected error in RPC loop: {e}", exc_info=True)
            time.sleep(UPDATE_INTERVAL)

    def _on_setup(self, icon):
        """Callback to start backend tasks once the icon is running."""
        # Show a notification safely
        try:
            icon.visible = True
            icon.notify(
                messenger('starting_rpc'),
                messenger('user', USERNAME)
            )
        except Exception as e:
            logger.warning(f"Failed to send startup notification: {e}")

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
