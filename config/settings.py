"""
Settings configuration for Deckster.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # App settings
    APP_ENV: str = Field("development", env="APP_ENV")
    DEBUG: bool = Field(True, env="DEBUG")
    LOG_LEVEL: str = Field("DEBUG", env="LOG_LEVEL")
    
    # API settings
    API_ENABLED: bool = Field(True, env="API_ENABLED")
    API_HOST: str = Field("0.0.0.0", env="API_HOST")
    API_PORT: int = Field(8000, env="PORT")
    
    # Supabase settings
    SUPABASE_URL: Optional[str] = Field(None, env="SUPABASE_URL")
    SUPABASE_ANON_KEY: Optional[str] = Field(None, env="SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_KEY: Optional[str] = Field(None, env="SUPABASE_SERVICE_KEY")

    # v3.3: Google Cloud Platform (Vertex AI) with Application Default Credentials
    GCP_ENABLED: bool = Field(True, env="GCP_ENABLED")
    GCP_PROJECT_ID: str = Field("deckster-xyz", env="GCP_PROJECT_ID")
    GCP_LOCATION: str = Field("us-central1", env="GCP_LOCATION")
    # GCP_SERVICE_ACCOUNT_JSON is only used in production (Railway)
    # For local development, use: gcloud auth application-default login
    GCP_SERVICE_ACCOUNT_JSON: Optional[str] = Field(None, env="GCP_SERVICE_ACCOUNT_JSON")

    # v4.0: AI Model Configuration (Gemini via Vertex AI Only)
    # v4.0 uses a Decision Engine instead of per-stage models
    # Note: Model names should NOT include 'google-vertex:' prefix (added automatically by code)

    # v4.0: Decision Engine model - the main AI that decides what action to take
    GCP_MODEL_DECISION: str = Field("gemini-2.5-flash", env="GCP_MODEL_DECISION")

    # Strawman generation (complex, detailed presentation outline)
    GCP_MODEL_STRAWMAN: str = Field("gemini-2.5-flash", env="GCP_MODEL_STRAWMAN")

    # Legacy v3.x model settings (kept for backward compatibility)
    GCP_MODEL_GREETING: str = Field("gemini-1.5-flash", env="GCP_MODEL_GREETING")
    GCP_MODEL_QUESTIONS: str = Field("gemini-1.5-flash", env="GCP_MODEL_QUESTIONS")
    GCP_MODEL_PLAN: str = Field("gemini-1.5-flash", env="GCP_MODEL_PLAN")
    GCP_MODEL_REFINE: str = Field("gemini-2.0-flash-exp", env="GCP_MODEL_REFINE")
    GCP_MODEL_ROUTER: str = Field("gemini-1.5-flash", env="GCP_MODEL_ROUTER")
    
    # Logging
    LOGFIRE_TOKEN: Optional[str] = Field(None, env="LOGFIRE_TOKEN")
    
    # Streamlined WebSocket Protocol
    USE_STREAMLINED_PROTOCOL: bool = Field(
        default=True,
        description="Enable streamlined WebSocket message protocol"
    )
    
    STREAMLINED_PROTOCOL_PERCENTAGE: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Percentage of sessions to use streamlined protocol (0-100)"
    )
    
    # Layout Architect Settings (Phase 2)
    LAYOUT_ARCHITECT_MODEL: str = Field("gemini-2.5-flash-lite-preview-06-17", env="LAYOUT_ARCHITECT_MODEL")
    LAYOUT_ARCHITECT_TEMPERATURE: float = Field(0.7, env="LAYOUT_ARCHITECT_TEMPERATURE")
    LAYOUT_GRID_WIDTH: int = Field(160, env="LAYOUT_GRID_WIDTH")
    LAYOUT_GRID_HEIGHT: int = Field(90, env="LAYOUT_GRID_HEIGHT")
    LAYOUT_MARGIN: int = Field(8, env="LAYOUT_MARGIN")
    LAYOUT_GUTTER: int = Field(4, env="LAYOUT_GUTTER")
    LAYOUT_WHITE_SPACE_MIN: float = Field(0.3, env="LAYOUT_WHITE_SPACE_MIN")
    LAYOUT_WHITE_SPACE_MAX: float = Field(0.5, env="LAYOUT_WHITE_SPACE_MAX")
    
    # Three-Agent Layout Architect Configuration (Phase 2 - New Architecture)
    THEME_AGENT_MODEL: str = Field("gemini-2.5-flash-lite-preview-06-17", env="THEME_AGENT_MODEL")
    STRUCTURE_AGENT_MODEL: str = Field("gemini-2.5-flash-lite-preview-06-17", env="STRUCTURE_AGENT_MODEL")
    LAYOUT_ENGINE_MODEL: str = Field("gemini-2.5-flash-lite-preview-06-17", env="LAYOUT_ENGINE_MODEL")
    
    # Phase 2B Content-Driven Architecture Configuration
    USE_PHASE_2B_ARCHITECTURE: bool = Field(True, env="USE_PHASE_2B_ARCHITECTURE")
    CONTENT_AGENT_MODEL: str = Field("gemini-2.5-flash-lite-preview-06-17", env="CONTENT_AGENT_MODEL")
    USE_LEGACY_WORKFLOW: bool = Field(False, env="USE_LEGACY_WORKFLOW")

    # v2.0: Deck-Builder Integration
    # v3.4: Updated for v7.5-main (port 8504)
    DECK_BUILDER_ENABLED: bool = Field(True, env="DECK_BUILDER_ENABLED")
    DECK_BUILDER_API_URL: str = Field("http://localhost:8504", env="DECK_BUILDER_API_URL")
    DECK_BUILDER_TIMEOUT: int = Field(30, env="DECK_BUILDER_TIMEOUT")

    # v3.1: Text Service Integration (Stage 6 - Content Generation)
    # v3.4-v1.2: Updated to Text Service v1.2 with 34 platinum variants
    TEXT_SERVICE_ENABLED: bool = Field(True, env="TEXT_SERVICE_ENABLED")
    TEXT_SERVICE_URL: str = Field(
        "https://web-production-5daf.up.railway.app",  # v1.2 Railway deployment
        env="TEXT_SERVICE_URL"
    )
    TEXT_SERVICE_VERSION: str = Field("1.2", env="TEXT_SERVICE_VERSION")
    TEXT_SERVICE_TIMEOUT: int = Field(300, env="TEXT_SERVICE_TIMEOUT")  # Increased for v1.2
    TEXT_SERVICE_VALIDATE_COUNTS: bool = Field(True, env="TEXT_SERVICE_VALIDATE_COUNTS")
    TEXT_SERVICE_PARALLEL_MODE: bool = Field(True, env="TEXT_SERVICE_PARALLEL_MODE")

    # v3.4: Rate Limiting & 429 Error Prevention (Stage 6)
    # Prevents Vertex AI quota exhaustion by controlling API call frequency
    RATE_LIMIT_DELAY_SECONDS: int = Field(2, env="RATE_LIMIT_DELAY_SECONDS")  # Delay between slides
    MAX_VERTEX_RETRIES: int = Field(5, env="MAX_VERTEX_RETRIES")  # Max retry attempts for 429 errors
    VERTEX_RETRY_BASE_DELAY: int = Field(2, env="VERTEX_RETRY_BASE_DELAY")  # Base delay (exponential backoff)

    # v3.4: Illustrator Service Integration (Stage 6 - Visualization Generation)
    # Handles pyramid and future data visualizations (funnel, SWOT, BCG matrix, etc.)
    ILLUSTRATOR_SERVICE_ENABLED: bool = Field(True, env="ILLUSTRATOR_SERVICE_ENABLED")
    ILLUSTRATOR_SERVICE_URL: str = Field(
        "http://localhost:8000",  # Local development (Illustrator v1.0)
        env="ILLUSTRATOR_SERVICE_URL"
    )
    ILLUSTRATOR_SERVICE_TIMEOUT: int = Field(60, env="ILLUSTRATOR_SERVICE_TIMEOUT")  # Pyramid generation ~4s

    # v3.4: Analytics Service Integration (Stage 6 - Chart Generation)
    # Handles L01, L02, L03 analytics layouts with charts + AI observations
    ANALYTICS_SERVICE_ENABLED: bool = Field(True, env="ANALYTICS_SERVICE_ENABLED")
    ANALYTICS_SERVICE_URL: str = Field(
        "https://analytics-v30-production.up.railway.app",  # Railway production
        env="ANALYTICS_SERVICE_URL"
    )
    ANALYTICS_SERVICE_TIMEOUT: int = Field(30, env="ANALYTICS_SERVICE_TIMEOUT")  # Chart generation ~3s

    # v3.4: Unified Variant Registration System (Phase 3.5)
    # Registry-driven variant management for all content generation services
    UNIFIED_VARIANT_SYSTEM_ENABLED: bool = Field(
        False,  # Default: disabled (use existing system)
        env="UNIFIED_VARIANT_SYSTEM_ENABLED",
        description="Enable unified variant registration system for slide classification and routing"
    )
    UNIFIED_VARIANT_SYSTEM_PERCENTAGE: int = Field(
        0,  # Default: 0% rollout
        ge=0,
        le=100,
        env="UNIFIED_VARIANT_SYSTEM_PERCENTAGE",
        description="Percentage of sessions to use unified system (0-100). Only applies if ENABLED=true"
    )
    VARIANT_REGISTRY_PATH: Optional[str] = Field(
        None,  # Default: use config/unified_variant_registry.json
        env="VARIANT_REGISTRY_PATH",
        description="Path to unified variant registry JSON file (optional)"
    )

    # v4.0: Layout Service Coordination (Coordinated Strawman)
    # Enables intelligent layout/variant selection via Layout Service instead of hardcoded L25/L29
    USE_LAYOUT_SERVICE_COORDINATION: bool = Field(
        False,  # Default: disabled (use existing hardcoded path)
        env="USE_LAYOUT_SERVICE_COORDINATION",
        description="Enable Layout Service for intelligent layout/variant selection in strawman generation"
    )
    LAYOUT_SERVICE_URL: str = Field(
        "http://localhost:8504",  # Same as DECK_BUILDER_API_URL (Layout Service v7.5)
        env="LAYOUT_SERVICE_URL"
    )
    LAYOUT_SERVICE_TIMEOUT: int = Field(10, env="LAYOUT_SERVICE_TIMEOUT")

    # v4.0.25: Layout Series Mode (Story-Driven Multi-Service Coordination)
    # Controls which layout series are available for slide generation
    # v4.5.7: Changed default from L_ONLY to C_AND_H to use H1/H2/H3/C1 instead of deprecated L29/L25
    LAYOUT_SERIES_MODE: str = Field(
        "C_AND_H",
        env="LAYOUT_SERIES_MODE",
        description="Which layout series to use: L_ONLY, L_AND_C, C_AND_H, ALL"
    )

    # v4.0.25: Multi-Service Coordination
    # When enabled, story-driven routing can direct slides to Analytics/Diagram/Illustrator services
    USE_MULTI_SERVICE_COORDINATION: bool = Field(
        False,
        env="USE_MULTI_SERVICE_COORDINATION",
        description="Enable story-driven routing to Analytics/Diagram/Illustrator services"
    )

    # v4.0: Text Service Coordination (Phase 1 - Multi-Service Coordination)
    # Enables intelligent variant selection via Text Service coordination endpoints
    # v4.5.2: Enabled by default - Text Service v1.2 supports /recommend-variant endpoint
    USE_TEXT_SERVICE_COORDINATION: bool = Field(
        True,  # Enabled: use Text Service intelligent variant selection
        env="USE_TEXT_SERVICE_COORDINATION",
        description="Enable Text Service /can-handle and /recommend-variant coordination endpoints"
    )
    TEXT_SERVICE_COORDINATION_TIMEOUT: int = Field(
        10,  # Coordination calls should be fast (not content generation)
        env="TEXT_SERVICE_COORDINATION_TIMEOUT"
    )
    TEXT_SERVICE_CONFIDENCE_THRESHOLD: float = Field(
        0.70,  # Minimum confidence to use Text Service recommendation
        ge=0.0,
        le=1.0,
        env="TEXT_SERVICE_CONFIDENCE_THRESHOLD",
        description="Minimum confidence (0-1) required to accept Text Service routing"
    )

    # v4.0: I-Series Generation (Phase 1 - Text Service Image+Text Layouts)
    # Enables I-series layouts (I1-I4) for combined image + text slides
    USE_ISERIES_GENERATION: bool = Field(
        False,  # Default: disabled (use standard content variants)
        env="USE_ISERIES_GENERATION",
        description="Enable I-series (image+text) slide generation for content slides"
    )
    ISERIES_DEFAULT_VISUAL_STYLE: str = Field(
        "professional",  # professional, illustrated, kids
        env="ISERIES_DEFAULT_VISUAL_STYLE",
        description="Default visual style for I-series images: professional, illustrated, kids"
    )
    ISERIES_DEFAULT_CONTENT_STYLE: str = Field(
        "bullets",  # bullets, paragraphs, mixed
        env="ISERIES_DEFAULT_CONTENT_STYLE",
        description="Default content style for I-series text: bullets, paragraphs, mixed"
    )

    # v4.3: Unified Slides API (Text Service v1.2.2)
    # Uses new /v1.2/slides/* endpoints that return spec-compliant responses
    # - Combined generation: C1-text uses 1 LLM call instead of 3 (67% savings)
    # - Structured H-series: H1-structured, H2-section, H3-closing return proper fields
    # - I-series aliases: slide_title, body returned directly (no mapping needed)
    USE_UNIFIED_SLIDES_API: bool = Field(
        False,  # v4.7: DISABLED - C1-text endpoint has errors, use /v1.2/generate instead
        env="USE_UNIFIED_SLIDES_API",
        description="Use Text Service v1.2.2 unified /v1.2/slides/* endpoints for combined generation"
    )

    # v4.5: Theme System (THEME_SYSTEM_DESIGN.md v2.3)
    # Controls how content is styled by Text Service
    # - "inline_styles": CSS embedded in HTML elements (default, works everywhere)
    # - "css_classes": Uses .deckster-t1, .deckster-t4 etc. (requires Layout Service CSS)
    # Phase 2: Switch to "css_classes" when Text Service v1.3.0 is ready
    THEME_STYLING_MODE: str = Field(
        "inline_styles",  # Safe default - works with current Text Service
        env="THEME_STYLING_MODE",
        description="Styling mode for Text Service: 'inline_styles' or 'css_classes'"
    )
    DEFAULT_THEME_ID: str = Field(
        "professional",  # Safe business default
        env="DEFAULT_THEME_ID",
        description="Default theme ID when not specified: professional, executive, educational, children"
    )

    # v4.5.8: CSS Variable Theming (Phase 1)
    # Controls dark/light mode switching via CSS variables
    # When enabled, Director passes theme_mode to Text Service and Layout Service
    ENABLE_THEME_MODE: bool = Field(
        False,  # Default: disabled (use current light-mode behavior)
        env="ENABLE_THEME_MODE",
        description="Enable dark/light mode theming via CSS variables"
    )
    DEFAULT_THEME_MODE: str = Field(
        "light",  # Safe default - light mode
        env="DEFAULT_THEME_MODE",
        description="Default theme mode: 'light' or 'dark'"
    )

    # v4.1: Playbook System
    # Pre-defined presentation structures indexed by (audience, purpose, duration)
    # Three-tier selection: Full match (90%+), Partial match (60-89%), No match (<60%)
    USE_PLAYBOOK_SYSTEM: bool = Field(
        True,  # Enabled by default
        env="USE_PLAYBOOK_SYSTEM",
        description="Enable playbook-based strawman generation for known presentation types"
    )
    PLAYBOOK_FULL_MATCH_THRESHOLD: float = Field(
        0.90,
        ge=0.0,
        le=1.0,
        env="PLAYBOOK_FULL_MATCH_THRESHOLD",
        description="Minimum confidence for full playbook match (use playbook directly)"
    )
    PLAYBOOK_PARTIAL_MATCH_THRESHOLD: float = Field(
        0.60,
        ge=0.0,
        le=1.0,
        env="PLAYBOOK_PARTIAL_MATCH_THRESHOLD",
        description="Minimum confidence for partial match (merge playbook with custom slides)"
    )

    # v4.2: Stage 5 - Strawman Refinement System
    # Enables user feedback loop for refining strawman via chat and direct edits
    # Uses "Diff on Generate" approach: compare with Deck-Builder before content generation
    STRAWMAN_REFINEMENT_ENABLED: bool = Field(
        True,
        env="STRAWMAN_REFINEMENT_ENABLED",
        description="Enable strawman refinement from user chat feedback"
    )
    DIFF_ON_GENERATE_ENABLED: bool = Field(
        True,
        env="DIFF_ON_GENERATE_ENABLED",
        description="Enable diff-on-generate sync with Deck-Builder before content generation"
    )
    GCP_MODEL_REFINE_STRAWMAN: str = Field(
        "gemini-2.5-flash",
        env="GCP_MODEL_REFINE_STRAWMAN",
        description="Model for AI-driven strawman refinement"
    )
    REFINEMENT_MAX_ITERATIONS: int = Field(
        5,
        ge=1,
        le=10,
        env="REFINEMENT_MAX_ITERATIONS",
        description="Maximum refinement iterations before suggesting content generation"
    )

    # v4.2: Stage 6 - Service-Owned Content Generation
    # Delegates title/subtitle generation to content services
    # Director only adds footer/logo (consistent across slides)
    USE_SERVICE_OWNED_CONTENT: bool = Field(
        False,  # Start disabled for backward compatibility
        env="USE_SERVICE_OWNED_CONTENT",
        description="Enable services to generate title/subtitle HTML (Stage 6)"
    )
    USE_TITLE_SUBTITLE_ENDPOINTS: bool = Field(
        True,
        env="USE_TITLE_SUBTITLE_ENDPOINTS",
        description="Use Text Service /api/ai/slide/title and /subtitle endpoints for title generation"
    )
    TITLE_GENERATION_PARALLEL: bool = Field(
        True,
        env="TITLE_GENERATION_PARALLEL",
        description="Generate title/subtitle in parallel with content (when possible)"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env
    
    @property
    def has_ai_service(self) -> bool:
        """Check if at least one AI service is configured."""
        return bool(self.GCP_ENABLED or self.OPENAI_API_KEY or self.ANTHROPIC_API_KEY)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment (Railway)."""
        return os.environ.get('RAILWAY_PROJECT_ID') is not None

    def validate_settings(self) -> None:
        """
        Validate that essential settings are configured.

        v3.3: Updated for Application Default Credentials (ADC) pattern.
        """
        # Check if at least one AI service is configured
        if not self.has_ai_service:
            raise ValueError(
                "No AI service configured. Please either:\n"
                "  1. Enable GCP (GCP_ENABLED=true) and authenticate with Vertex AI\n"
                "     - Local: Run 'gcloud auth application-default login'\n"
                "     - Railway: Set GCP_SERVICE_ACCOUNT_JSON environment variable\n"
                "  2. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in your .env file"
            )

        # v3.3: Validate GCP setup if enabled
        if self.GCP_ENABLED:
            if self.is_production and not self.GCP_SERVICE_ACCOUNT_JSON:
                raise ValueError(
                    "PRODUCTION SECURITY ERROR:\n"
                    "GCP_ENABLED is true but GCP_SERVICE_ACCOUNT_JSON is not set.\n"
                    "Railway production deployments MUST have GCP_SERVICE_ACCOUNT_JSON configured.\n"
                    "Add the service account JSON to Railway environment variables."
                )

            if not self.is_production and not self.GCP_SERVICE_ACCOUNT_JSON:
                # Local development - just log a reminder
                from src.utils.logger import setup_logger
                logger = setup_logger(__name__)
                logger.info("Local development mode: Ensure you've run 'gcloud auth application-default login'")


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# For backward compatibility with existing code
settings = get_settings()