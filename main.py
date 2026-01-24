from core.application import App
from utils.logging_config import setup_logging

# Configure enhanced logging
setup_logging(level=logging.INFO)

if __name__ == "__main__":
    try:
        app = App()
        app.run()
    except Exception as e:
        logging.critical(f"Application failed to start: {e}", exc_info=True)