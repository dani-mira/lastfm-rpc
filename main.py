import logging
from core.application import App

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    app = App()
    app.run()