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

class App:
    def __init__(self):
        self.rpc = DiscordRPC()
        self.current_track_name = messenger('no_track')
        self.icon_tray = self.setup_tray_icon()
        self.loop = asyncio.new_event_loop()
        self.rpc_thread = threading.Thread(target=self.run_rpc, args=(self.loop,))
        self.rpc_thread.daemon = True

    def exit_app(self, icon, item):
        """Stops the system tray icon and exits the application."""
        logging.info("Exiting application.")
        icon.stop()
        sys.exit()

    def open_profile(self, icon, item):
        """Opens the user's Last.fm profile in the default browser."""
        url = LASTFM_USER_URL.format(username=USERNAME)
        webbrowser.open(url)
        logging.info(f"Opened Last.fm profile: {url}")

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

    def setup_tray_menu(self):
        """Creates and returns the tray menu."""
        return Menu(
            MenuItem(messenger('user', USERNAME), self.open_profile),
            MenuItem(lambda item: self.current_track_name, None, enabled=False),
            MenuItem(messenger('open_profile'), self.open_profile),
            Menu.SEPARATOR,
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
        logging.info(messenger('starting_rpc'))
        asyncio.set_event_loop(loop)
        user = User(USERNAME)

        while True:
            try:
                current_track, data = user.now_playing()
                logging.debug(f"Last.fm Check - Track: {current_track}, Data identified: {data is not None}")
                
                if data:
                    title, artist, album, artwork, time_remaining = data
                    formatted_track = f"{artist} - {title}"
                    new_track_display = messenger('now_playing', formatted_track)
                    
                    if self.current_track_name != new_track_display:
                        self.current_track_name = new_track_display
                        logging.info(f"Status: {self.current_track_name}")
                        # Force menu refresh
                        self.icon_tray.menu = self.setup_tray_menu()
                    
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
                    time.sleep(TRACK_CHECK_INTERVAL)
                else:
                    if self.current_track_name != messenger('no_track'):
                        self.current_track_name = messenger('no_track')
                        logging.info("Tray Update: No track detected")
                        self.icon_tray.menu = self.setup_tray_menu()
                    self.rpc.disable()
            except Exception as e:
                logging.error(f"Unexpected error in RPC loop: {e}", exc_info=True)
            time.sleep(UPDATE_INTERVAL)

    def run(self):
        """Starts the system tray application and RPC thread."""
        self.rpc_thread.start()
        self.icon_tray.run()
