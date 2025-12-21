"""
Decision Models for Director Agent v4.0

Defines the output types and structures used by the Decision Engine
for AI-driven action selection.
"""

from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field
from enum import Enum


class ActionType(str, Enum):
    """Types of actions the Decision Engine can take."""
    RESPOND = "respond"                    # Conversational response
    ASK_QUESTIONS = "ask_questions"        # Need more information
    PROPOSE_PLAN = "propose_plan"          # Propose presentation structure
    GENERATE_STRAWMAN = "generate_strawman"  # Generate slide outline
    REFINE_STRAWMAN = "refine_strawman"    # Modify existing strawman
    INVOKE_TOOLS = "invoke_tools"          # Call content generation tools
    COMPLETE = "complete"                  # Presentation finished


class ExtractedContext(BaseModel):
    """
    Typed model for context extraction - Gemini compatible.

    v4.0.10: Replaces Dict[str, Any] which Gemini strips due to
    additionalProperties not being supported. Using explicit typed fields
    ensures Gemini can properly return extracted context values.

    v4.5: Added slide_count, preset mappings for Smart Context Extraction.
    """
    # Core presentation context
    topic: Optional[str] = Field(None, description="The presentation topic extracted from user message")
    audience: Optional[str] = Field(None, description="Target audience mentioned by user")
    duration: Optional[int] = Field(None, description="Duration in minutes if specified")
    purpose: Optional[str] = Field(None, description="Goal: inform, persuade, teach, inspire")
    tone: Optional[str] = Field(None, description="Style: professional, casual, inspiring")

    # Detection flags - set to True when corresponding field is detected
    has_topic: bool = Field(default=False, description="True if user provided a topic")
    has_audience: bool = Field(default=False, description="True if user mentioned audience")
    has_duration: bool = Field(default=False, description="True if user specified duration")
    has_purpose: bool = Field(default=False, description="True if user stated the goal/purpose")

    # v4.5: Explicit slide count (overrides playbook defaults)
    slide_count: Optional[int] = Field(
        None,
        description="Explicit slide count if user specifies (e.g., 'I need 20 slides')"
    )
    has_explicit_slide_count: bool = Field(
        default=False,
        description="True if user explicitly specified a slide count"
    )

    # v4.5: Mapped presets for ContentContext
    # These map user descriptions to our internal presets
    audience_preset: Optional[str] = Field(
        None,
        description="Maps audience to preset: kids_young, kids_older, middle_school, high_school, college, professional, executive, general"
    )
    purpose_preset: Optional[str] = Field(
        None,
        description="Maps purpose to preset: inform, educate, persuade, inspire, entertain, qbr"
    )
    time_preset: Optional[str] = Field(
        None,
        description="Maps duration to preset: lightning (5min), quick (10min), standard (20min), extended (30min), comprehensive (45min)"
    )


class ToolCallRequest(BaseModel):
    """A request to invoke a tool."""
    tool_id: str = Field(..., description="The tool identifier to invoke")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    slide_id: Optional[str] = Field(None, description="Target slide ID if applicable")
    priority: int = Field(default=0, description="Execution priority (higher = first)")

    class Config:
        extra = "allow"


class DecisionOutput(BaseModel):
    """
    Output from the Decision Engine.

    This is what the AI returns when analyzing context and deciding
    what action to take.
    """
    action_type: ActionType = Field(
        ...,
        description="The type of action to take"
    )

    response_text: Optional[str] = Field(
        None,
        description="Text response to send to user (for respond, ask_questions actions)"
    )

    questions: Optional[List[str]] = Field(
        None,
        description="Clarifying questions to ask (for ask_questions action)"
    )

    tool_calls: Optional[List[ToolCallRequest]] = Field(
        None,
        description="Tools to invoke (for invoke_tools action)"
    )

    strawman_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Strawman data for generate_strawman/refine_strawman actions"
    )

    plan_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Plan data for propose_plan action"
    )

    reasoning: str = Field(
        ...,
        description="Explanation of why this action was chosen (for debugging)"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the decision (0.0-1.0)"
    )

    requires_approval: bool = Field(
        default=False,
        description="Whether this action requires explicit user approval"
    )

    # v4.0.10: Typed model for context extraction (Gemini compatible)
    # Replaced Dict[str, Any] which Gemini strips due to additionalProperties not supported
    extracted_context: Optional[ExtractedContext] = Field(
        default=None,
        description="Context extracted from user message. Set topic/audience/duration/purpose/tone fields and corresponding has_* flags when detected."
    )

    class Config:
        extra = "allow"


class ConversationTurn(BaseModel):
    """A single turn in the conversation."""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DecisionContext(BaseModel):
    """
    Context provided to the Decision Engine for making decisions.

    Contains all relevant information about the current session state.
    """
    # User input
    user_message: str = Field(..., description="The current user message")

    # Conversation history
    conversation_history: List[ConversationTurn] = Field(
        default_factory=list,
        description="Previous conversation turns"
    )

    # Session state flags
    has_topic: bool = Field(default=False, description="User has provided a topic")
    has_audience: bool = Field(default=False, description="Audience is defined")
    has_duration: bool = Field(default=False, description="Duration is specified")
    has_purpose: bool = Field(default=False, description="Purpose/goal is clear")
    has_plan: bool = Field(default=False, description="Plan has been proposed and accepted")
    has_strawman: bool = Field(default=False, description="Strawman has been generated")
    has_explicit_approval: bool = Field(default=False, description="User explicitly approved generation")
    has_content: bool = Field(default=False, description="Content has been generated")
    is_complete: bool = Field(default=False, description="Presentation is complete")

    # Session data
    initial_request: Optional[str] = Field(None, description="Original user request")
    topic: Optional[str] = Field(None, description="Presentation topic")
    audience: Optional[str] = Field(None, description="Target audience")
    duration: Optional[int] = Field(None, description="Duration in minutes")
    purpose: Optional[str] = Field(None, description="Presentation goal")
    tone: Optional[str] = Field(None, description="Desired tone/style")

    # Strawman data
    strawman: Optional[Dict[str, Any]] = Field(None, description="Current strawman")
    generated_slides: Optional[List[Dict[str, Any]]] = Field(None, description="Generated slide content")

    # Presentation data
    presentation_id: Optional[str] = Field(None, description="Deck builder presentation ID")
    preview_url: Optional[str] = Field(None, description="Preview URL")

    class Config:
        extra = "allow"


class ApprovalDetectionResult(BaseModel):
    """Result of detecting user approval from message."""
    is_explicit_approval: bool = Field(
        ...,
        description="True if user explicitly approved generation"
    )
    is_soft_approval: bool = Field(
        default=False,
        description="True if user gave soft approval (needs confirmation)"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in approval detection"
    )
    matched_phrase: Optional[str] = Field(
        None,
        description="The phrase that triggered approval detection"
    )


class StrawmanSlide(BaseModel):
    """A single slide in the strawman."""
    # v4.0.3: Removed ge=1 constraint to fix Gemini schema complexity error
    slide_id: str = Field(..., description="Unique slide identifier")
    slide_number: int = Field(..., description="Position in presentation (1-based)")
    title: str = Field(..., description="Slide title")
    subtitle: Optional[str] = Field(default=None, description="Slide subtitle (e.g., supporting context)")
    layout: str = Field(default="L25", description="Layout template ID (L25 content, L29 hero)")
    topics: List[str] = Field(default_factory=list, description="Key topics/points")
    variant_id: Optional[str] = Field(default=None, description="Content variant for generation")
    notes: Optional[str] = Field(default=None, description="v4.5.14: Speaker notes, tone guidance, emphasis points (REQUIRED for all slides)")
    is_hero: bool = Field(default=False, description="Whether this is a hero slide")
    hero_type: Optional[str] = Field(default=None, description="title_slide, section_divider, or closing_slide")

    # v4.0: Multi-Service Coordination fields
    # These are populated by ContentAnalyzer during strawman enhancement
    content_hints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Content analysis hints for service routing (from ContentAnalyzer)"
    )
    suggested_service: Optional[str] = Field(
        default=None,
        description="Recommended service: text, analytics, diagram, illustrator"
    )
    service_confidence: Optional[float] = Field(
        default=None,
        description="Confidence in service recommendation (0-1)"
    )

    # v4.0: I-series layout fields (image + text combined)
    needs_image: bool = Field(
        default=False,
        description="True if content would benefit from I-series layout"
    )
    suggested_iseries: Optional[str] = Field(
        default=None,
        description="Suggested I-series layout (I1, I2, I3, I4) if needs_image is True"
    )

    # v4.0.25: Story-driven multi-service coordination fields
    # These are populated during storyline generation (Step 1)
    slide_type_hint: Optional[str] = Field(
        default=None,
        description="Story-driven type: hero, text, chart, diagram, infographic"
    )
    purpose: Optional[str] = Field(
        default=None,
        description="v4.5.14: What story this slide tells in the narrative (REQUIRED for all slides - AI generates)"
    )

    # v4.0.25: Routing fields (from Step 2: Layout Analysis)
    service: Optional[str] = Field(
        default=None,
        description="Service to handle this slide: text, analytics, diagram, illustrator"
    )
    generation_instructions: Optional[str] = Field(
        default=None,
        description="v4.5.14: Specific instructions for content generation (REQUIRED for all slides - AI generates)"
    )

    # v4.5.3: Semantic grouping for context-aware variant diversity
    semantic_group: Optional[str] = Field(
        default=None,
        description="Group ID for slides that should use the same template (e.g., 'use_cases', 'timeline', 'case_studies'). Slides in the same group share the same variant."
    )


class Strawman(BaseModel):
    """Complete strawman (presentation outline)."""
    # v4.0.3: Removed min_length/max_length constraints to fix Gemini schema complexity error
    # Validation should be done in code if needed (2-30 slides recommended)
    title: str = Field(..., description="Presentation title")
    slides: List[StrawmanSlide] = Field(..., description="List of slides (2-30 recommended)")
    # v4.0.3: Made metadata optional to avoid additionalProperties issues with Gemini
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")

    @property
    def slide_count(self) -> int:
        return len(self.slides)

    def get_slide(self, slide_id: str) -> Optional[StrawmanSlide]:
        """Get a slide by ID."""
        for slide in self.slides:
            if slide.slide_id == slide_id:
                return slide
        return None


class PresentationPlan(BaseModel):
    """High-level presentation plan (before strawman)."""
    summary: str = Field(..., description="Brief summary of the presentation")
    proposed_slide_count: int = Field(..., ge=2, le=30)
    key_assumptions: List[str] = Field(default_factory=list)
    structure_overview: str = Field(..., description="High-level structure description")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in minutes")
