import logging
import sys
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logging():
    """Configure logging for Eva Lite"""
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "eva.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Formatters
    console_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    file_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(console_format)
    file_handler.setFormatter(file_format)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Set specific loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    logging.info("Logging configured successfully")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name"""
    return logging.getLogger(name)


class StructuredLogger:
    """Enhanced logger with structured logging support"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_event(self, level: str, event: str, **kwargs):
        """Log structured event with metadata"""
        timestamp = datetime.utcnow().isoformat()
        log_data = {
            "timestamp": timestamp,
            "event": event,
            **kwargs
        }
        
        message = f"[{event}] " + " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        
        if level.upper() == "DEBUG":
            self.logger.debug(message)
        elif level.upper() == "INFO":
            self.logger.info(message)
        elif level.upper() == "WARNING":
            self.logger.warning(message)
        elif level.upper() == "ERROR":
            self.logger.error(message)
        elif level.upper() == "CRITICAL":
            self.logger.critical(message)
    
    def info(self, message: str, **kwargs):
        self.log_event("INFO", "general", message=message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log_event("ERROR", "error", message=message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log_event("WARNING", "warning", message=message, **kwargs)