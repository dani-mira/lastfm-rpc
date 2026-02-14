import logging
from utils.logging_config import setup_logging
from constants.project import USERNAME, API_KEY, API_SECRET, APP_LANG

# Configure enhanced logging
setup_logging(level=logging.INFO)

def check_config():
    """Checks if the configuration is complete. If not, opens the GUI."""
    if not all([USERNAME, API_KEY, API_SECRET]) or (USERNAME and "<" in str(USERNAME)):
        logging.warning("Configuration incomplete or placeholder detected. Opening settings...")
        from utils.gui import ConfigGUI
        import yaml
        import sys

        def save_and_exit(new_config):
            try:
                with open("config.yaml", "w", encoding="utf-8") as f:
                    yaml.dump(new_config, f, default_flow_style=False)
                logging.info("Configuration saved successfully. Please restart the application to apply changes.")
                # We exit here because constants are already loaded with old/empty values
                sys.exit(0)
            except Exception as e:
                logging.error(f"Failed to save configuration: {e}")
                return False

        gui = ConfigGUI((USERNAME, API_KEY, API_SECRET, APP_LANG), save_and_exit)
        gui.run()
        return False
    return True

if __name__ == "__main__":
    if check_config():
        from core.application import App
        try:
            app = App()
            app.run()
        except Exception as e:
            logging.critical(f"Application failed to start: {e}", exc_info=True)