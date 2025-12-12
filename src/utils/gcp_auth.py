"""
Google Cloud Platform Authentication Utility - v3.3
===================================================

Uses Application Default Credentials (ADC) pattern for secure authentication.

This module provides a unified authentication layer that works seamlessly in:
- Local Development: Uses `gcloud auth application-default login` credentials
- Production (Railway): Uses service account from GCP_SERVICE_ACCOUNT_JSON env var

Security Benefits:
- No API keys in environment variables
- Rotatable service accounts
- Fine-grained IAM permissions
- Full GCP audit logging
- Fail-fast production validation
"""

import os
import json
import vertexai
from google.oauth2 import service_account
from typing import Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# GCP Configuration
PROJECT_ID = "deckster-xyz"
LOCATION = "us-central1"

# Global state to track initialization
_vertex_ai_initialized = False


def is_production_environment() -> bool:
    """
    Detect if running in production environment (Railway).

    Returns:
        True if in production, False if local development
    """
    # Railway automatically sets RAILWAY_PROJECT_ID variable
    return os.environ.get('RAILWAY_PROJECT_ID') is not None


def initialize_vertex_ai(force_reinit: bool = False) -> None:
    """
    Initialize Vertex AI with Application Default Credentials.

    This function uses a dual-mode authentication strategy:

    **PRODUCTION MODE (Railway):**
    - Requires GCP_SERVICE_ACCOUNT_JSON environment variable
    - Loads service account credentials from JSON string
    - Fails fast if credentials are missing or invalid

    **LOCAL DEVELOPMENT MODE:**
    - Uses gcloud auth application-default login credentials
    - Requires user to have run: gcloud auth application-default login
    - Falls back to ADC resolution

    Args:
        force_reinit: If True, reinitialize even if already initialized

    Raises:
        RuntimeError: If credentials are unavailable or invalid
        ValueError: If GCP_SERVICE_ACCOUNT_JSON is malformed in production
    """
    global _vertex_ai_initialized

    if _vertex_ai_initialized and not force_reinit:
        logger.debug("Vertex AI already initialized, skipping")
        return

    is_production = is_production_environment()
    gcp_json_str = os.environ.get('GCP_SERVICE_ACCOUNT_JSON')

    if gcp_json_str:
        # PRODUCTION MODE: Service Account authentication
        logger.info("🔐 Initializing Vertex AI with service account (Production mode)")
        try:
            credentials_info = json.loads(gcp_json_str)

            # Validate service account JSON structure
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing_fields = [f for f in required_fields if f not in credentials_info]
            if missing_fields:
                raise ValueError(f"Service account JSON missing required fields: {missing_fields}")

            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )

            vertexai.init(
                project=PROJECT_ID,
                location=LOCATION,
                credentials=credentials
            )

            logger.info(f"✓ Vertex AI initialized successfully with service account: {credentials_info.get('client_email')}")
            logger.info(f"  Project: {PROJECT_ID}, Location: {LOCATION}")
            _vertex_ai_initialized = True

        except json.JSONDecodeError as e:
            logger.error(f"FATAL: GCP_SERVICE_ACCOUNT_JSON is not valid JSON: {e}")
            raise RuntimeError(
                "Invalid GCP_SERVICE_ACCOUNT_JSON format. "
                "Ensure you've pasted the complete service account JSON content."
            )
        except Exception as e:
            logger.error(f"FATAL: Failed to initialize Vertex AI with service account: {e}")
            raise RuntimeError(
                f"Cannot initialize Vertex AI with provided service account credentials: {e}"
            )

    elif is_production:
        # PRODUCTION MODE but missing credentials - FAIL FAST
        logger.error("FATAL: Running in production (Railway) but GCP_SERVICE_ACCOUNT_JSON is not set")
        logger.error("Required action: Add GCP_SERVICE_ACCOUNT_JSON to Railway environment variables")
        logger.error("Variable should contain the full JSON content of your service account key file")
        raise RuntimeError(
            "PRODUCTION SECURITY ERROR: GCP_SERVICE_ACCOUNT_JSON must be set in Railway. "
            "Application cannot start without proper credentials."
        )

    else:
        # LOCAL DEVELOPMENT MODE: Application Default Credentials
        logger.info("🔓 Initializing Vertex AI with ADC (Local development mode)")
        logger.info("  Expecting credentials from: gcloud auth application-default login")

        try:
            vertexai.init(project=PROJECT_ID, location=LOCATION)
            logger.info(f"✓ Vertex AI initialized successfully with ADC")
            logger.info(f"  Project: {PROJECT_ID}, Location: {LOCATION}")
            _vertex_ai_initialized = True

        except Exception as e:
            logger.error(f"FATAL: Failed to initialize Vertex AI with ADC: {e}")
            logger.error("")
            logger.error("LOCAL SETUP REQUIRED:")
            logger.error("  1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install")
            logger.error("  2. Run: gcloud auth application-default login")
            logger.error("  3. Run: gcloud config set project deckster-xyz")
            logger.error("  4. Retry starting the application")
            logger.error("")
            raise RuntimeError(
                "Cannot initialize Vertex AI with Application Default Credentials. "
                "Run 'gcloud auth application-default login' first."
            )


def get_vertex_model(model_name: str = "gemini-2.5-flash"):
    """
    Get a Vertex AI GenerativeModel instance.

    Args:
        model_name: Name of the Gemini model to use.
                   Options: gemini-2.5-flash, gemini-2.5-pro, gemini-1.5-flash, etc.

    Returns:
        GenerativeModel instance ready for use

    Raises:
        RuntimeError: If Vertex AI not initialized
    """
    if not _vertex_ai_initialized:
        initialize_vertex_ai()

    from vertexai.generative_models import GenerativeModel

    logger.debug(f"Creating Vertex AI model: {model_name}")
    return GenerativeModel(model_name=model_name)


def get_project_info() -> dict:
    """
    Get current GCP project configuration.

    Returns:
        Dictionary with project_id, location, and initialization status
    """
    return {
        "project_id": PROJECT_ID,
        "location": LOCATION,
        "initialized": _vertex_ai_initialized,
        "is_production": is_production_environment(),
        "has_service_account": bool(os.environ.get('GCP_SERVICE_ACCOUNT_JSON'))
    }


def validate_gcp_setup() -> tuple[bool, str]:
    """
    Validate that GCP authentication is properly configured.

    Returns:
        Tuple of (is_valid, error_message)
        If is_valid is True, error_message will be empty string
    """
    try:
        initialize_vertex_ai()
        return (True, "")
    except Exception as e:
        return (False, str(e))
