"""
Debug Capture Utility for Text Service Request/Response Logging

Saves full requests and responses to files for debugging Director Stage 6.
Files are saved to debug_captures/ directory for inspection.
"""

import json
from datetime import datetime
from pathlib import Path

DEBUG_DIR = Path(__file__).parent.parent.parent / "debug_captures"


def capture_text_service_request(
    session_id: str,
    slide_index: int,
    request: dict,
    response: dict = None,
    error: str = None
) -> Path:
    """
    Save full Text Service request/response to file for debugging.

    Args:
        session_id: The session ID for grouping related captures
        slide_index: The slide index (0-based)
        request: The full request dict sent to Text Service
        response: The response dict from Text Service (optional)
        error: Any error message if the call failed (optional)

    Returns:
        Path to the saved capture file
    """
    DEBUG_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Use first 8 chars of session_id for shorter filenames
    short_session = session_id[:8] if session_id else "unknown"
    filename = f"{timestamp}_{short_session}_slide{slide_index}.json"

    capture = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "slide_index": slide_index,
        "request": request,
        "response": response,
        "error": error
    }

    filepath = DEBUG_DIR / filename
    filepath.write_text(json.dumps(capture, indent=2))

    return filepath


def capture_hero_request(
    session_id: str,
    slide_index: int,
    slide_type: str,
    request: dict,
    response: dict = None,
    error: str = None
) -> Path:
    """
    Save Hero slide (L29) request/response to file for debugging.

    Args:
        session_id: The session ID
        slide_index: The slide index
        slide_type: The hero slide type (title_slide, section_divider, closing_slide)
        request: The full request dict sent to Text Service hero endpoint
        response: The response dict from Text Service (optional)
        error: Any error message if the call failed (optional)

    Returns:
        Path to the saved capture file
    """
    DEBUG_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_session = session_id[:8] if session_id else "unknown"
    filename = f"{timestamp}_{short_session}_hero_{slide_type}_slide{slide_index}.json"

    capture = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "slide_index": slide_index,
        "slide_type": slide_type,
        "endpoint": f"/v1.2/hero/{slide_type}",
        "request": request,
        "response": response,
        "error": error
    }

    filepath = DEBUG_DIR / filename
    filepath.write_text(json.dumps(capture, indent=2))

    return filepath
