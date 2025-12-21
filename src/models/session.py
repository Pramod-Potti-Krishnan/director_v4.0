"""
Session Model for Director Agent v4.0

Flexible session model that uses progress flags and generic context
instead of rigid state-specific fields.

Key differences from v3.4:
- No `current_state` field (replaced by progress flags)
- Generic `context` dict for flexible data storage
- Progress flags indicate what has been accomplished

v4.2: Added branding field for per-presentation footer/logo configuration.
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from pydantic import BaseModel, Field

# Avoid circular import - only import for type checking
if TYPE_CHECKING:
    from src.models.presentation_config import PresentationBranding


class SessionV4(BaseModel):
    """
    Session model for v4.0 MCP-style architecture.

    Uses flexible context storage instead of state-specific fields.
    Progress is tracked via boolean flags, not state names.
    """

    # Identifiers
    id: str
    user_id: str

    # Progress flags (replaces current_state)
    has_topic: bool = Field(default=False, description="User has provided a topic")
    has_audience: bool = Field(default=False, description="Audience is defined")
    has_duration: bool = Field(default=False, description="Duration is specified")
    has_purpose: bool = Field(default=False, description="Purpose/goal is clear")
    has_plan: bool = Field(default=False, description="Plan has been proposed and accepted")
    has_strawman: bool = Field(default=False, description="Strawman has been generated")
    has_explicit_approval: bool = Field(default=False, description="User approved generation")
    has_content: bool = Field(default=False, description="Content has been generated")
    is_complete: bool = Field(default=False, description="Presentation is complete")

    # Generic context storage (replaces state-specific fields)
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible context storage for any session data"
    )

    # Conversation history (preserved from v3.4)
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)

    # Key session data (extracted from context for quick access)
    initial_request: Optional[str] = Field(None, description="Original user request")
    topic: Optional[str] = Field(None, description="Presentation topic")
    audience: Optional[str] = Field(None, description="Target audience")
    duration: Optional[int] = Field(None, description="Duration in minutes")
    purpose: Optional[str] = Field(None, description="Presentation goal")
    tone: Optional[str] = Field(None, description="Desired tone/style")

    # Presentation data
    strawman: Optional[Dict[str, Any]] = Field(None, description="Current strawman")
    generated_slides: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Generated slide content"
    )
    presentation_id: Optional[str] = Field(None, description="Deck builder presentation ID")
    presentation_url: Optional[str] = Field(None, description="Preview URL")

    # v4.2: Per-presentation branding configuration
    branding: Optional[Dict[str, Any]] = Field(
        None,
        description="Branding configuration (footer/logo) as dict for Supabase compatibility"
    )

    # v4.5: Theme System (THEME_SYSTEM_DESIGN.md v2.3)
    theme_id: Optional[str] = Field(
        default="professional",
        description="Theme identifier (professional, executive, educational, children)"
    )
    content_context: Optional[Dict[str, Any]] = Field(
        None,
        description="ContentContext for audience-aware generation (built at strawman stage)"
    )

    # v4.5: Smart Context Extraction
    requested_slide_count: Optional[int] = Field(
        None,
        description="Explicit slide count if user specified (e.g., 'I need 20 slides')"
    )
    audience_preset: Optional[str] = Field(
        None,
        description="Mapped audience preset: kids_young, middle_school, high_school, college, professional, executive, general"
    )
    purpose_preset: Optional[str] = Field(
        None,
        description="Mapped purpose preset: inform, educate, persuade, inspire, entertain, qbr"
    )
    time_preset: Optional[str] = Field(
        None,
        description="Mapped time preset: lightning, quick, standard, extended, comprehensive"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        extra = "allow"

    def set_context(self, key: str, value: Any) -> None:
        """Set a context value."""
        self.context[key] = value
        self.updated_at = datetime.utcnow()

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        return self.context.get(key, default)

    def clear_context(self, keys: Optional[List[str]] = None) -> None:
        """
        Clear context values.

        Args:
            keys: Specific keys to clear (clears all if None)
        """
        if keys is None:
            self.context = {}
        else:
            for key in keys:
                self.context.pop(key, None)
        self.updated_at = datetime.utcnow()

    def reset_progress(self) -> None:
        """Reset all progress flags (for new presentation)."""
        self.has_topic = False
        self.has_audience = False
        self.has_duration = False
        self.has_purpose = False
        self.has_plan = False
        self.has_strawman = False
        self.has_explicit_approval = False
        self.has_content = False
        self.is_complete = False
        self.updated_at = datetime.utcnow()

    def clear_for_new_presentation(self) -> None:
        """Clear session for starting a new presentation."""
        self.reset_progress()
        self.clear_context()
        self.initial_request = None
        self.topic = None
        self.audience = None
        self.duration = None
        self.purpose = None
        self.tone = None
        self.strawman = None
        self.generated_slides = None
        self.presentation_id = None
        self.presentation_url = None
        self.branding = None  # v4.2: Clear branding for new presentation
        # Keep conversation history for context
        self.updated_at = datetime.utcnow()

    def get_branding(self) -> Optional["PresentationBranding"]:
        """
        Get branding configuration as PresentationBranding model.

        v4.2: Converts dict to PresentationBranding for type safety.
        """
        if not self.branding:
            return None

        from src.models.presentation_config import PresentationBranding
        return PresentationBranding(**self.branding)

    def set_branding(self, branding: "PresentationBranding") -> None:
        """
        Set branding configuration from PresentationBranding model.

        v4.2: Converts to dict for Supabase storage.
        """
        self.branding = branding.dict()
        self.updated_at = datetime.utcnow()

    def get_decision_context(self) -> Dict[str, Any]:
        """
        Get context formatted for DecisionEngine.

        Returns a dict with all relevant session state.
        """
        return {
            "user_message": "",  # Set by caller
            "has_topic": self.has_topic,
            "has_audience": self.has_audience,
            "has_duration": self.has_duration,
            "has_purpose": self.has_purpose,
            "has_plan": self.has_plan,
            "has_strawman": self.has_strawman,
            "has_explicit_approval": self.has_explicit_approval,
            "has_content": self.has_content,
            "is_complete": self.is_complete,
            "initial_request": self.initial_request,
            "topic": self.topic,
            "audience": self.audience,
            "duration": self.duration,
            "purpose": self.purpose,
            "tone": self.tone,
            "strawman": self.strawman,
            "generated_slides": self.generated_slides,
            "presentation_id": self.presentation_id,
            "presentation_url": self.presentation_url,
            "conversation_history": self.conversation_history[-10:]  # Last 10 turns
        }

    def to_supabase_dict(self) -> Dict[str, Any]:
        """Convert to dict for Supabase storage.

        v4.2.1: Excludes 'branding' field until column is added to Supabase table.
        v4.5: Excludes Smart Context Extraction fields until columns are added.
        """
        data = self.dict()
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        # v4.2.1: Remove branding until column exists in dr_sessions_v4 table
        # TODO: Remove this line after running: ALTER TABLE dr_sessions_v4 ADD COLUMN branding JSONB DEFAULT NULL;
        data.pop('branding', None)
        # v4.5: Remove Smart Context Extraction fields until columns exist
        # TODO: Remove these lines after running the following SQL:
        # ALTER TABLE dr_sessions_v4 ADD COLUMN requested_slide_count INTEGER DEFAULT NULL;
        # ALTER TABLE dr_sessions_v4 ADD COLUMN audience_preset TEXT DEFAULT NULL;
        # ALTER TABLE dr_sessions_v4 ADD COLUMN purpose_preset TEXT DEFAULT NULL;
        # ALTER TABLE dr_sessions_v4 ADD COLUMN time_preset TEXT DEFAULT NULL;
        data.pop('requested_slide_count', None)
        data.pop('audience_preset', None)
        data.pop('purpose_preset', None)
        data.pop('time_preset', None)
        return data

    @classmethod
    def from_supabase(cls, data: Dict[str, Any]) -> "SessionV4":
        """Create from Supabase row data."""
        # Handle datetime conversion
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
        return cls(**data)


# Compatibility alias for migration
Session = SessionV4
