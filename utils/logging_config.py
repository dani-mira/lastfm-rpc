import logging
import sys
import os
import platform
from logging.handlers import RotatingFileHandler

class ColoredFormatter(logging.Formatter):
    """Custom logging formatter for vibrant and readable terminal output."""
    
    # ANSI escape codes for colors
    COLORS = {
        'DEBUG': '\033[38;5;244m',    # Steel Grey
        'INFO': '\033[38;5;82m',      # Vibrant Green
        'WARNING': '\033[38;5;214m',   # Orange/Yellow
        'ERROR': '\033[38;5;196m',     # Bright Red
        'CRITICAL': '\033[1;37;41m',   # White on Red background
    }
    
    # Symbols for each level
    LEVEL_SYMBOLS = {
        'DEBUG': '[#]',
        'INFO': '[+]',
        'WARNING': '[!]',
        'ERROR': '[-]',
        'CRITICAL': '[X]',
    }
    
    RESET = '\033[0m'
    BOLD = '\033[1m'

    def format(self, record):
        # Determine color and symbol
        level_color = self.COLORS.get(record.levelname, self.RESET)
        level_symbol = self.LEVEL_SYMBOLS.get(record.levelname, '[•]')
        
        # Format timestamp safely
        time_str = self.formatTime(record, "%H:%M:%S")
        
        # Truncate extremely long messages (like XML dumps) for terminal readability
        message = record.getMessage()
        if len(message) > 500:
            message = message[:500] + "... [TRUNCATED]"
            
        # Color certain parts of the message for better scanning
        log_fmt = (
            f"{self.COLORS['DEBUG']}[{time_str}]{self.RESET} "
            f"{level_color}{self.BOLD}{level_symbol} {record.levelname:<8}{self.RESET} "
            f"{self.COLORS['DEBUG']}[{record.name}]{self.RESET} "
            f"- {message}"
        )
        
        # Handle exceptions if they exist
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        
        if record.exc_text:
            log_fmt += f"\n{self.COLORS['ERROR']}{record.exc_text}{self.RESET}"
            
        return log_fmt

class FileFormatter(logging.Formatter):
    """Detailed formatter for log files, including line numbers and functions."""
    def format(self, record):
        time_str = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        message = record.getMessage()
        # Include filename and line number for easier debugging in file logs
        location = f"{record.filename}:{record.lineno}"
        log_fmt = f"[{time_str}] {record.levelname:<8} [{record.name}] [{location}] {record.funcName}() - {message}"
        
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            log_fmt += f"\n{record.exc_text}"
        return log_fmt

def log_system_info():
    """Logs essential system and application info for debugging."""
    from constants.project import VERSION, APP_NAME
    logger = logging.getLogger('system')
    logger.debug("--- System Information ---")
    logger.debug(f"Application: {APP_NAME} v{VERSION}")
    logger.debug(f"OS: {platform.system()} {platform.release()} ({platform.version()})")
    logger.debug(f"Architecture: {platform.machine()}")
    logger.debug(f"Python Version: {sys.version}")
    logger.debug(f"Executable: {sys.executable}")
    logger.debug(f"Working Directory: {os.getcwd()}")
    logger.debug("--------------------------")

def setup_logging(level=logging.INFO):
    """Configures the enhanced logging for the application."""
    
    # Enable ANSI escape sequences on Windows if possible
    if sys.platform == 'win32':
        os.system('') # This is a trick to enable ANSI support in Windows CMD
    
    logger = logging.getLogger()
    # Support maximum detail for handlers to pick from
    logger.setLevel(logging.DEBUG) 
    
    # Remove existing handlers to avoid double logging
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    # 1. Console Handler (Colored)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    
    # 2. File Handler (Persistent)
    try:
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=5*1024*1024, # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(FileFormatter())
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to initialize file logging: {e}")
    
    # Silence noisy external libraries
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("pylast").setLevel(logging.WARNING)
    logging.getLogger("pypresence").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("pystray").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Log system metadata on startup
    log_system_info()

    return logger
