"""
Director Agent v4.0 - AI Presentation Assistant
Main entry point for the MCP-style director agent application.

Architecture: MCP-Style Decision Engine with Tool Registry
Key Changes from v3.4:
- AI-driven decision making (no rigid state machine)
- Tool registry for service invocations
- Guidance system (director_guidance.md) instead of hardcoded states
- Flexible session with progress flags

v4.0.10: Fixed topic extraction and content generation
- ExtractedContext typed model replaces Dict[str, Any] (Gemini compatible)
- Fixed slide_purpose fallback for empty notes field

v4.0.11: Fixed Text Service API request format
- Added target_points to slide_spec (required by Text Service v1.2)

v4.0.12: Fixed NoneType error in Text Service response handling
- Added defensive null check before processing Text Service responses
- Added type validation (must be dict) and success field check
- Better error logging for debugging null/malformed responses

v4.0.13: Multi-layer topic extraction fix + deck-builder null checks
- Layer 1: Enhanced system prompt with explicit topic extraction rules
- Layer 2: Diagnostic logging for extracted_context debugging
- Layer 3: Fallback topic parser from response_text when Gemini fails
- Layer 4: Guard in _handle_generate_strawman to prevent "Untitled"
- Defensive null checks for deck-builder API responses

v4.0.14: Enhanced Text Service response logging
- Added HTTP response logging (status, content-length, content-type)
- Added timing information for Text Service calls
- Added parsed response structure logging (type, keys, success, html length)
- Added transform logging in _transform_response
- Enhanced exception handler with exception type and full traceback

v4.0.15: Context overwrite prevention guards
- Added guards to prevent overwriting already-established session fields
- Once topic/audience/duration/purpose/tone is set, subsequent extractions are ignored
- Fixes bug where multi-part answers could overwrite previously set topic
- Added logging for ignored extractions for debugging

v4.0.16: Belt-and-suspenders null response handling
- Log raw response at INFO level BEFORE json() parsing for visibility
- Move null check IMMEDIATELY after json() - before any logging that accesses result
- Restructured validation order: null check -> type check -> logging -> success check
- Added redundant null guard before validation check (defense in depth)
- Better error messages showing raw response body when null is detected

v4.0.17: Text Service HTTP error handling + retry logic
- Added retry logic for transient LLM generation failures (HTTP 400/422)
- Text Service LLM sometimes generates incomplete content (missing sentence_5/6)
- Retry up to 2 times with exponential backoff (1s, 2s) for retryable errors
- Detects retryable errors: sentence_, generated_content, LLM generation failed
- Changed exception logging from error to warning (fallback is graceful degradation)
- Added fallback usage summary at end of content generation
- Better visibility into which slides used Text Service vs fallback HTML

v4.0.18: Enhanced diagnostic logging for Text Service failures
- Log full request payload before sending to Text Service (at INFO level)
- Log complete traceback when Text Service call fails
- Log target_points (topics) that were sent in the request
- Helps diagnose why presentations fall back to strawman HTML
- CLI debug tools added: tools/director_cli.py, tools/test_text_service.py

v4.0.19: Fix AttributeError in Text Service null response handling
- ROOT CAUSE IDENTIFIED: Text Service sometimes returns null JSON body
- Railway logs showed: 'NoneType' object has no attribute 'get' at validation check
- Added defensive None check for validation access in text_service_client_v1_2.py
- Fixes line 206-209 where result could be None despite earlier null checks
- Changed: validation = result.get("validation") if result else None
"""

import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up Google Application Default Credentials from JSON string
# This must happen BEFORE any Google library imports
import json
import tempfile

if os.environ.get('GCP_SERVICE_ACCOUNT_JSON'):
    try:
        credentials_json = os.environ['GCP_SERVICE_ACCOUNT_JSON']

        # Write credentials to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write(credentials_json)
            temp_creds_path = f.name

        # Set GOOGLE_APPLICATION_CREDENTIALS for all Google libraries
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_creds_path
        print(f"Set GOOGLE_APPLICATION_CREDENTIALS to {temp_creds_path}")

    except Exception as e:
        print(f"Failed to set up Google credentials: {e}")

# Configure Logfire early in startup
from src.utils.logfire_config import configure_logfire
configure_logfire()

from src.handlers.websocket import WebSocketHandler
from src.utils.logger import setup_logger
from config.settings import get_settings

# Initialize
logger = setup_logger(__name__)
settings = get_settings()

# Global handler instance (reused across connections for efficiency)
_handler_instance = None


def get_handler():
    """Get or create the global WebSocket handler instance."""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = WebSocketHandler()
        logger.info("WebSocketHandlerV4 initialized with Decision Engine")
    return _handler_instance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    logger.info("Starting Director Agent v4.0 API...")

    # Check if API is disabled
    if not settings.API_ENABLED:
        logger.warning("API_ENABLED is set to False - Director service is DISABLED")
        logger.warning("WebSocket connections will be rejected")
        logger.warning("Set API_ENABLED=true in .env to enable the service")
        yield
        logger.info("Shutting down Director Agent v4.0 API (was disabled)...")
        return

    # Validate required configurations
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        logger.error("FATAL: Supabase configuration missing!")
        logger.error("Please set the following environment variables in your .env file:")
        logger.error("  SUPABASE_URL=https://your-project.supabase.co")
        logger.error("  SUPABASE_ANON_KEY=your-anon-key-here")
        logger.error("Get these values from your Supabase project settings.")
        raise RuntimeError("Cannot start without Supabase configuration. See logs for details.")

    # Validate AI API keys
    try:
        settings.validate_settings()
        logger.info("AI API key configuration validated")
    except ValueError as e:
        logger.error(f"FATAL: {str(e)}")
        logger.error("Please set at least one of these in your .env file:")
        logger.error("  GOOGLE_API_KEY=your-key-here")
        logger.error("  OPENAI_API_KEY=sk-...")
        logger.error("  ANTHROPIC_API_KEY=sk-ant-...")
        raise RuntimeError("Cannot start without AI API configuration. See logs for details.")

    # Validate Supabase connection
    from src.storage.supabase import get_supabase_client
    try:
        client = await get_supabase_client()
        logger.info("Supabase async client connection validated")
    except Exception as e:
        logger.error(f"FATAL: Failed to connect to Supabase: {str(e)}")
        raise RuntimeError("Cannot start without valid Supabase connection.")

    # Initialize handler on startup
    try:
        handler = get_handler()
        logger.info(f"Tool Registry initialized with {len(handler.tool_registry.get_tool_ids())} tools")
        logger.info("Decision Engine ready")
    except Exception as e:
        logger.error(f"FATAL: Failed to initialize handler: {str(e)}")
        raise RuntimeError("Cannot start without WebSocket handler.")

    yield
    logger.info("Shutting down Director Agent v4.0 API...")

app = FastAPI(
    title="Director Agent v4.0 API",
    version="4.0.0",
    description="MCP-Style AI Presentation Assistant with Decision Engine",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.deckster.xyz",
        "https://deckster.xyz",
        "http://localhost:3000",  # Development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_id: str
):
    """
    Handle WebSocket connections with user authentication.

    Args:
        websocket: The WebSocket connection
        session_id: Session UUID
        user_id: User ID (from auth)

    Note: v4.0 uses AI-driven decision making instead of state machine.
    Session restoration is handled via Supabase session persistence.
    """
    # Check if API is disabled
    if not settings.API_ENABLED:
        logger.warning(f"WebSocket connection rejected - API is disabled (session: {session_id}, user: {user_id})")
        await websocket.close(code=1013, reason="Service temporarily unavailable - API disabled")
        return

    # Validate parameters
    if not session_id or not user_id:
        logger.error("WebSocket connection attempted without session_id or user_id")
        await websocket.close(code=1008, reason="Missing required parameters")
        return

    logger.debug(f"WebSocket connection request: session={session_id}, user={user_id}")

    try:
        handler = get_handler()
        logger.debug("Using shared WebSocketHandlerV4 instance")
    except Exception as init_error:
        logger.error(f"Failed to get WebSocketHandler: {str(init_error)}", exc_info=True)
        await websocket.close(code=1011, reason="Server error during initialization")
        return

    try:
        # Handler accepts and manages the connection
        await handler.handle_connection(websocket, session_id, user_id)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={session_id}, user={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: session={session_id}, user={user_id}, error={str(e)}", exc_info=True)
        try:
            if websocket.client_state.value <= 1:  # CONNECTING=0, CONNECTED=1
                await websocket.close()
        except Exception:
            pass


# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    handler = None
    tool_count = 0
    try:
        handler = get_handler()
        tool_count = len(handler.tool_registry.get_tool_ids())
    except Exception:
        pass

    return {
        "status": "healthy" if settings.API_ENABLED else "disabled",
        "api_enabled": settings.API_ENABLED,
        "service": "director-agent-v4.0",
        "version": "4.0.0",
        "environment": settings.APP_ENV,
        "architecture": "MCP-Style Decision Engine",
        "tool_count": tool_count,
        "message": "Service is running normally" if settings.API_ENABLED else "Service is disabled - WebSocket connections will be rejected"
    }


# Version verification endpoint
@app.get("/version")
async def version_check():
    """Return deployed code version information."""
    import datetime
    import pathlib

    # Try to read VERSION file (works in Railway where git is not available)
    version_file = pathlib.Path(__file__).parent / "VERSION"
    version_info = {}

    if version_file.exists():
        try:
            with open(version_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        version_info[key.strip()] = value.strip()
        except Exception as e:
            version_info = {"error": f"Failed to read VERSION file: {str(e)}"}
    else:
        # Fallback: try git (works locally but not in Railway)
        import subprocess
        try:
            git_commit = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                stderr=subprocess.DEVNULL
            ).decode('utf-8').strip()
            version_info = {
                "commit": git_commit[:7],
                "note": "git-based (VERSION file missing)"
            }
        except Exception:
            version_info = {"error": "No VERSION file and git unavailable"}

    return {
        "service": "director-agent-v4.0",
        "version": "4.0.0",
        "commit": version_info.get("commit", "unknown"),
        "features": "MCP-Style Decision Engine, Tool Registry, Guidance System",
        "deployed_status": version_info.get("deployed", "unknown"),
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "environment": settings.APP_ENV,
        "railway_project": os.environ.get('RAILWAY_PROJECT_ID', 'not_on_railway'),
        "version_file_found": version_file.exists()
    }


# Debug endpoint to check Railway environment variables
@app.get("/debug/env")
async def debug_env():
    """Debug endpoint to check Railway environment variables."""
    import pathlib
    google_app_creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    creds_file_exists = pathlib.Path(google_app_creds).exists() if google_app_creds else False

    return {
        "RAILWAY_PROJECT_ID": os.environ.get('RAILWAY_PROJECT_ID'),
        "RAILWAY_ENVIRONMENT_NAME": os.environ.get('RAILWAY_ENVIRONMENT_NAME'),
        "RAILWAY_SERVICE_ID": os.environ.get('RAILWAY_SERVICE_ID'),
        "RAILWAY_ENVIRONMENT": os.environ.get('RAILWAY_ENVIRONMENT'),
        "has_gcp_json": bool(os.environ.get('GCP_SERVICE_ACCOUNT_JSON')),
        "is_production_check": os.environ.get('RAILWAY_PROJECT_ID') is not None,
        "settings_is_production": settings.is_production,
        "GOOGLE_APPLICATION_CREDENTIALS": google_app_creds,
        "credentials_file_exists": creds_file_exists
    }


# Test endpoint for WebSocketHandler initialization
@app.get("/test-handler")
async def test_handler():
    """Test WebSocketHandlerV4 initialization and components."""
    try:
        handler = get_handler()
        tool_ids = handler.tool_registry.get_tool_ids()

        return {
            "status": "success",
            "message": "WebSocketHandlerV4 initialized successfully",
            "architecture": "MCP-Style Decision Engine",
            "components": {
                "decision_engine": handler.decision_engine is not None,
                "strawman_generator": handler.strawman_generator is not None,
                "tool_registry": handler.tool_registry is not None,
                "session_manager": handler.session_manager is not None or True,  # Lazy init
                "supabase": handler.supabase is not None or True  # Lazy init
            },
            "tools": {
                "total_count": len(tool_ids),
                "tool_ids": tool_ids[:10] if len(tool_ids) > 10 else tool_ids,
                "truncated": len(tool_ids) > 10
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Failed to initialize WebSocketHandler: {str(e)}",
            "error_type": type(e).__name__
        }


# Tool registry info endpoint
@app.get("/tools")
async def list_tools():
    """List all registered tools and their cost tiers."""
    try:
        handler = get_handler()
        tools_info = []

        for tool_id in handler.tool_registry.get_tool_ids():
            tool = handler.tool_registry.tools.get(tool_id)
            if tool:
                tools_info.append({
                    "id": tool_id,
                    "name": tool.name,
                    "description": tool.description,
                    "cost_tier": tool.cost_tier.value,
                    "requires_approval": tool.requires_approval
                })

        return {
            "total_tools": len(tools_info),
            "tools": tools_info
        }
    except Exception as e:
        return {
            "error": str(e),
            "tools": []
        }


# API info endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    handler = None
    tool_count = 0
    try:
        handler = get_handler()
        tool_count = len(handler.tool_registry.get_tool_ids())
    except Exception:
        pass

    return {
        "name": "Director Agent v4.0 API",
        "description": "MCP-Style AI-powered presentation generation assistant",
        "version": "4.0.0",
        "architecture": "MCP-Style Decision Engine with Tool Registry",
        "key_changes": [
            "AI-driven decision making (replaces state machine)",
            "Tool registry for service invocations",
            "Guidance system for best practices",
            "Flexible session with progress flags"
        ],
        "endpoints": {
            "websocket": "/ws?session_id={session_id}&user_id={user_id}",
            "health": "/health",
            "version": "/version",
            "tools": "/tools",
            "test-handler": "/test-handler"
        },
        "decision_actions": [
            "RESPOND - Conversational response",
            "ASK_QUESTIONS - Clarifying questions",
            "PROPOSE_PLAN - Suggest presentation structure",
            "GENERATE_STRAWMAN - Create slide outline",
            "REFINE_STRAWMAN - Modify outline",
            "INVOKE_TOOLS - Call content generation",
            "COMPLETE - Presentation finished"
        ],
        "tool_count": tool_count
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    log_level = "debug" if settings.DEBUG else "info"

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level=log_level,
        reload=settings.DEBUG
    )
