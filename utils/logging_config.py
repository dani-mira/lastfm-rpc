import logging
import sys
import os

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
    
    # Emojis for each level
    LEVEL_ICONS = {
        'DEBUG': '🐛',
        'INFO': '🚀',
        'WARNING': '⚠️ ',
        'ERROR': '🚨',
        'CRITICAL': '🔥',
    }
    
    RESET = '\033[0m'
    BOLD = '\033[1m'

    def format(self, record):
        # Determine color and icon
        level_color = self.COLORS.get(record.levelname, self.RESET)
        level_icon = self.LEVEL_ICONS.get(record.levelname, '•')
        
        # Format timestamp safely
        time_str = self.formatTime(record, "%H:%M:%S")
        
        # Color certain parts of the message for better scanning
        # 1. Level Name (bold)
        # 2. Main message
        
        log_fmt = (
            f"{self.COLORS['DEBUG']}[{time_str}]{self.RESET} "
            f"{level_color}{self.BOLD}{record.levelname:<8}{self.RESET} "
            f"{level_icon} "
            f"- {record.getMessage()}"
        )
        
        # Handle exceptions if they exist
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        
        if record.exc_text:
            log_fmt += f"\n{self.COLORS['ERROR']}{record.exc_text}{self.RESET}"
            
        return log_fmt

def setup_logging(level=logging.INFO):
    """Configures the enhanced logging for the application."""
    
    # Enable ANSI escape sequences on Windows if possible
    if sys.platform == 'win32':
        os.system('') # This is a trick to enable ANSI support in Windows CMD
    
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Remove existing handlers to avoid double logging
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    # Create console handler with our custom formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter())
    
    logger.addHandler(console_handler)
    
    # Optionally reduce noise from external libraries
    # logging.getLogger("urllib3").setLevel(logging.WARNING)
    # logging.getLogger("pylast").setLevel(logging.WARNING)

    return logger
