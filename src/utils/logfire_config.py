"""
Centralized Logfire configuration for Deckster.
"""
import os
import logfire
from typing import Optional

_configured = False

def configure_logfire(force: bool = False) -> bool:
    """
    Configure Logfire with proper error handling.
    
    Args:
        force: Force reconfiguration even if already configured
        
    Returns:
        bool: True if successfully configured
    """
    global _configured
    
    if _configured and not force:
        return True
    
    token = os.getenv("LOGFIRE_TOKEN")
    if not token:
        # Silently disable if no token
        return False
    
    try:
        # Configure with minimal parameters first
        # Suppress the project URL output by redirecting stdout and stderr temporarily
        import sys
        import io
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        # Also suppress via environment variable if supported
        os.environ['LOGFIRE_CONSOLE_NO_SHOW'] = '1'
        try:
            logfire.configure(
                service_name="deckster",
                service_version=os.getenv("APP_VERSION", "dev"),
                console=False  # Suppress the project URL output
            )
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        # Test with a simple log
        logfire.info("Logfire configured successfully")
        _configured = True
        return True
        
    except Exception as e:
        print(f"ERROR: Logfire configuration failed: {e}")
        _configured = False
        return False

def is_configured() -> bool:
    """Check if Logfire is configured."""
    return _configured

def instrument_agents():
    """Instrument PydanticAI agents if Logfire is configured."""
    # First ensure Logfire is configured
    if not is_configured():
        configure_logfire()
    
    if not is_configured():
        return False
    
    try:
        import logfire
        # This single line instruments ALL PydanticAI agents
        logfire.instrument_pydantic_ai()
        logfire.info("PydanticAI instrumentation enabled")
        return True
    except Exception as e:
        # Only log error if we have logfire configured
        if is_configured():
            logfire.error(f"Failed to instrument PydanticAI: {e}")
        return False