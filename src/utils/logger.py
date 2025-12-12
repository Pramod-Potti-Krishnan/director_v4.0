"""
Logging configuration for Deckster using Logfire.
"""
from typing import Optional

# Try to configure Logfire once at module import
LOGFIRE_CONFIGURED = False

try:
    import logfire
    from config.settings import get_settings
    
    settings = get_settings()
    
    if settings.LOGFIRE_TOKEN:
        try:
            # Try to configure Logfire
            # Suppress the project URL output by redirecting stdout and stderr temporarily
            import sys
            import io
            import os
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            # Also suppress via environment variable if supported
            os.environ['LOGFIRE_CONSOLE_NO_SHOW'] = '1'
            try:
                logfire.configure(token=settings.LOGFIRE_TOKEN, console=False)
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            LOGFIRE_CONFIGURED = True
        except Exception as config_error:
            # Logfire configuration failed, silently disable
            LOGFIRE_CONFIGURED = False
    else:
        # No LOGFIRE_TOKEN configured, logging disabled
        LOGFIRE_CONFIGURED = False
        
except Exception as e:
    # Logfire import/setup failed, silently disable
    LOGFIRE_CONFIGURED = False


class LogfireLogger:
    """Wrapper to make Logfire work like standard Python logging."""
    
    def __init__(self, name: str):
        self.name = name
    
    def info(self, message, *args, **kwargs):
        # Handle % formatting if args provided
        if args:
            message = message % args
        logfire.info(f"[{self.name}] {message}", **kwargs)
    
    def warn(self, message, *args, **kwargs):
        if args:
            message = message % args
        logfire.warn(f"[{self.name}] {message}", **kwargs)
    
    def warning(self, message, *args, **kwargs):
        # Alias for warn
        self.warn(message, *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        if args:
            message = message % args
        logfire.error(f"[{self.name}] {message}", **kwargs)
    
    def debug(self, message, *args, **kwargs):
        if args:
            message = message % args
        logfire.debug(f"[{self.name}] {message}", **kwargs)
    
    def critical(self, message, *args, **kwargs):
        if args:
            message = message % args
        logfire.error(f"[{self.name}] CRITICAL: {message}", **kwargs)
    
    def exception(self, message, *args, **kwargs):
        if args:
            message = message % args
        logfire.error(f"[{self.name}] EXCEPTION: {message}", **kwargs)
    
    def setLevel(self, level):
        # No-op for compatibility
        pass


class StandardLogger:
    """Standard Python logger when Logfire is not configured."""

    def __init__(self, name: str):
        import logging
        import os
        self.logger = logging.getLogger(name)

        # Read LOG_LEVEL from environment, default to INFO
        log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        self.logger.setLevel(log_level)

        # Add console handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(log_level)  # Set handler level too
            formatter = logging.Formatter(
                '[%(levelname)s %(name)s] %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def info(self, message, *args, **kwargs):
        self.logger.info(message, *args, **{k: v for k, v in kwargs.items() if k != 'exc_info'})
    
    def warn(self, message, *args, **kwargs):
        self.logger.warning(message, *args, **{k: v for k, v in kwargs.items() if k != 'exc_info'})
    
    def warning(self, message, *args, **kwargs):
        self.logger.warning(message, *args, **{k: v for k, v in kwargs.items() if k != 'exc_info'})
    
    def error(self, message, *args, **kwargs):
        exc_info = kwargs.pop('exc_info', False)
        self.logger.error(message, *args, exc_info=exc_info, **kwargs)
    
    def debug(self, message, *args, **kwargs):
        self.logger.debug(message, *args, **{k: v for k, v in kwargs.items() if k != 'exc_info'})
    
    def critical(self, message, *args, **kwargs):
        self.logger.critical(message, *args, **{k: v for k, v in kwargs.items() if k != 'exc_info'})
    
    def exception(self, message, *args, **kwargs):
        self.logger.exception(message, *args, **{k: v for k, v in kwargs.items() if k != 'exc_info'})
    
    def setLevel(self, level):
        self.logger.setLevel(level)


def setup_logger(name: str, level: Optional[str] = None):
    """
    Set up a logger using Logfire or standard Python logging if not configured.
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (used for standard logger)
        
    Returns:
        LogfireLogger or StandardLogger instance
    """
    if LOGFIRE_CONFIGURED:
        return LogfireLogger(name)
    else:
        return StandardLogger(name)


# Create a default logger for the package
logger = setup_logger(__name__)