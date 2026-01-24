import logging
from core.application import App

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

if __name__ == "__main__":
    try:
        app = App()
        app.run()
    except Exception as e:
        logging.critical(f"Application failed to start: {e}", exc_info=True)