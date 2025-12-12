"""
Agent-specific models for Deckster.
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class UserIntent(BaseModel):
    """Classified user intent from router - directional intents that imply next state."""
    intent_type: Literal[
        "Submit_Initial_Topic",           # → ASK_CLARIFYING_QUESTIONS
        "Submit_Clarification_Answers",   # → CREATE_CONFIRMATION_PLAN
        "Accept_Plan",                    # → GENERATE_STRAWMAN
        "Reject_Plan",                    # → CREATE_CONFIRMATION_PLAN (loop)
        "Accept_Strawman",                # → END/Complete
        "Submit_Refinement_Request",      # → REFINE_STRAWMAN
        "Change_Topic",                   # → ASK_CLARIFYING_QUESTIONS (reset)
        "Change_Parameter",               # → CREATE_CONFIRMATION_PLAN (regen)
        "Ask_Help_Or_Question"            # → No state change
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    # Make it a simple optional string to avoid additionalProperties warning with Gemini
    # The router can encode complex info as JSON string if needed
    extracted_info: Optional[str] = Field(default=None)


class StateContext(BaseModel):
    """Context for state-driven agent processing."""
    current_state: Literal[
        "PROVIDE_GREETING",
        "ASK_CLARIFYING_QUESTIONS",
        "CREATE_CONFIRMATION_PLAN",
        "GENERATE_STRAWMAN",
        "REFINE_STRAWMAN",
        "LAYOUT_GENERATION",  # Phase 2: Layout Architect state
        "CONTENT_GENERATION"  # v3.1: Stage 6 - Text Service content generation
    ]
    user_intent: Optional[UserIntent] = None
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    session_data: Dict[str, Any] = Field(default_factory=dict)


class ClarifyingQuestions(BaseModel):
    """Output for ASK_CLARIFYING_QUESTIONS state."""
    type: Literal["ClarifyingQuestions"] = "ClarifyingQuestions"
    questions: List[str] = Field(min_length=3, max_length=5)


class ConfirmationPlan(BaseModel):
    """Output for CREATE_CONFIRMATION_PLAN state."""
    type: Literal["ConfirmationPlan"] = "ConfirmationPlan"
    summary_of_user_request: str
    key_assumptions: List[str]
    proposed_slide_count: int = Field(ge=2, le=30)  # Allow as few as 2 slides for short presentations


class ContentGuidance(BaseModel):
    """
    Content generation guidance for specialized text generators (v3.4).

    Provides semantic and structural metadata to guide content generation
    for the 13 specialized slide types in Text Service v1.1.
    """
    content_type: str = Field(
        description="Primary content category: 'narrative', 'data', 'quote', 'comparison', 'process', etc."
    )
    visual_complexity: str = Field(
        description="Visual layout complexity: 'simple', 'moderate', 'complex'"
    )
    content_density: str = Field(
        description="Information density: 'minimal', 'balanced', 'dense'"
    )
    tone_indicator: str = Field(
        description="Presentation tone: 'professional', 'inspirational', 'analytical', 'conversational', etc."
    )
    data_type: Optional[str] = Field(
        default=None,
        description="Type of data if applicable: 'metrics', 'statistics', 'comparisons', 'timeline', etc."
    )
    emphasis_hierarchy: List[str] = Field(
        default_factory=list,
        description="Ordered list of content elements by importance (e.g., ['main_message', 'supporting_data', 'details'])"
    )
    relationship_to_previous: Optional[str] = Field(
        default=None,
        description="How this slide relates to previous content: 'continuation', 'contrast', 'deep_dive', 'new_section', etc."
    )
    generation_instructions: str = Field(
        description="Specific instructions for content generator (e.g., 'emphasize quantitative impact', 'use conversational tone')"
    )
    pattern_rationale: str = Field(
        description="Explanation of why this slide_type was chosen and how content should be structured"
    )


class Slide(BaseModel):
    """Simplified slide model focused on content guidance."""
    slide_number: int
    slide_id: str = Field(description="Unique identifier like 'slide_001'")
    title: str

    # Slide type classification
    slide_type: Literal[
        "title_slide",
        "section_divider",
        "content_heavy",
        "visual_heavy",
        "data_driven",
        "diagram_focused",
        "mixed_content",
        "conclusion_slide"
    ]

    # v3.4: 15-type taxonomy classification for specialized generators
    # v3.4-pyramid: Extended to support Illustrator Service visualizations
    # v3.4-analytics: Extended to support Analytics Service v3 charts
    slide_type_classification: Optional[str] = Field(
        default=None,
        description="Classified slide type from 15-type taxonomy (3 hero + 10 content + 2 visualizations). "
                    "Hero types: title_slide, section_divider, closing_slide. "
                    "Content types: bilateral_comparison, sequential_3col, impact_quote, metrics_grid, "
                    "matrix_2x2, grid_3x3, asymmetric_8_4, hybrid_1_2x2, single_column, styled_table. "
                    "Visualization types: pyramid (Illustrator Service), analytics (Analytics Service v3). "
                    "Used to route to specialized Text Service v1.2, Illustrator Service, or Analytics Service endpoints."
    )

    # v3.4: Content generation guidance for specialized generators
    content_guidance: Optional[ContentGuidance] = Field(
        default=None,
        description="Semantic and structural guidance for content generation. "
                    "Provides context to specialized text generators about tone, density, emphasis, etc."
    )

    # v3.4-pyramid: Visualization configuration for Illustrator Service
    visualization_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration for visualization generation (Illustrator Service). "
                    "For pyramid slides: {'num_levels': 3-6, 'target_points': ['Point 1', 'Point 2', ...], "
                    "'topic': 'Pyramid Topic', 'tone': 'professional'}. "
                    "Future: funnel, SWOT, BCG matrix configurations. "
                    "Only populated when slide_type_classification is a visualization type (e.g., 'pyramid')."
    )

    # v3.4-analytics: Analytics/Chart configuration for Analytics Service v3
    analytics_type: Optional[str] = Field(
        default=None,
        description="Type of analytics chart to generate. "
                    "Supported types: revenue_over_time, quarterly_comparison, market_share, "
                    "yoy_growth, kpi_metrics. "
                    "Only populated when slide_type_classification is 'analytics'."
    )
    analytics_data: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Chart data points for Analytics Service. "
                    "List of dicts with keys like 'label', 'value', etc. "
                    "Example: [{'label': 'Q1', 'value': 100}, {'label': 'Q2', 'value': 120}]. "
                    "v3.8.0: Data is now OPTIONAL - Analytics Service can generate synthetic data if not provided."
    )
    chart_id: Optional[str] = Field(
        default=None,
        description="Specific chart type to use for analytics visualization (v3.8.0). "
                    "18 chart types supported: 14 Chart.js (line, bar_vertical, bar_horizontal, pie, doughnut, "
                    "scatter, bubble, radar, polar_area, area, bar_grouped, bar_stacked, area_stacked, mixed) "
                    "+ 4 D3.js (d3_treemap, d3_sunburst, d3_choropleth_usa, d3_sankey). "
                    "REQUIRED for analytics slides to enable synthetic data generation. "
                    "Director AI selects based on content pattern and narrative."
    )

    # v3.1: Pre-selected layout ID (assigned during GENERATE_STRAWMAN)
    layout_id: Optional[str] = Field(
        default=None,
        description="Pre-selected deck-builder layout ID (L01-L24). "
                    "Assigned during GENERATE_STRAWMAN based on slide characteristics "
                    "and used in all subsequent stages (REFINE_STRAWMAN, CONTENT_GENERATION)."
    )

    # v3.2: AI reasoning for layout selection
    layout_selection_reasoning: Optional[str] = Field(
        default=None,
        description="Explanation of why this layout was selected by AI semantic matching"
    )

    # v3.4-v1.2: Random variant selection from Text Service v1.2
    variant_id: Optional[str] = Field(
        default=None,
        description="Randomly selected variant from Text Service v1.2's 34 platinum variants. "
                    "Examples: 'matrix_2x3', 'grid_3x3_icons', 'comparison_3col'. "
                    "Selected with equal probability from available variants for slide type."
    )

    # v3.4-v1.2: Director-generated titles with strict character limits
    generated_title: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Director-generated slide title (max 50 chars). "
                    "Used as INPUT to Text Service v1.2 for context and as slide_title in Layout Builder."
    )
    generated_subtitle: Optional[str] = Field(
        default=None,
        max_length=90,
        description="Director-generated slide subtitle (max 90 chars). "
                    "Used as subtitle in Layout Builder L25 slides."
    )

    # v3.5-visual-styles: Visual style configuration for hero slides
    visual_style: Optional[Literal["professional", "illustrated", "kids"]] = Field(
        default=None,
        description=(
            "Visual style for hero slide images. Only applicable to hero slides (L29). "
            "Options: professional (photorealistic), illustrated (Ghibli-style), kids (vibrant/playful). "
            "Assigned in GENERATE_STRAWMAN based on user preference or AI defaults. "
            "Passed to Text Service v1.2 /hero/*-with-image endpoints."
        )
    )
    use_image_background: bool = Field(
        default=False,
        description=(
            "Whether to use AI-generated image background for hero slides. "
            "Title slides: ALWAYS True (user requirement). "
            "Section slides: Only for decks >10 slides AND (user request OR creative theme). "
            "Closing slides: Based on preference (default: True for memorable impact). "
            "Determines routing to /hero/*-with-image vs /hero/* endpoints."
        )
    )

    # Core content
    narrative: str = Field(description="The story or key message of this slide")
    key_points: List[str]
    
    # Open-ended guidance for future agents
    analytics_needed: Optional[str] = Field(
        default=None, 
        description="Description of any data, charts, or analytics for this slide"
    )
    visuals_needed: Optional[str] = Field(
        default=None, 
        description="Description of images, icons, or visual elements that would help"
    )
    diagrams_needed: Optional[str] = Field(
        default=None, 
        description="Description of any process flows, hierarchies, or relationships to visualize"
    )
    tables_needed: Optional[str] = Field(
        default=None,
        description="Description of any comparison tables, data grids, or structured information to display"
    )
    structure_preference: Optional[str] = Field(
        default=None, 
        description="High-level layout preference like 'two-column' or 'visual-centered'"
    )
    
    # Optional
    speaker_notes: Optional[str] = None
    
    # For backward compatibility
    @property
    def visual_suggestions(self) -> Optional[List[str]]:
        """Backward compatible property for visual suggestions."""
        suggestions = []
        if self.visuals_needed:
            suggestions.append(self.visuals_needed)
        if self.analytics_needed:
            suggestions.append(self.analytics_needed)
        if self.diagrams_needed:
            suggestions.append(self.diagrams_needed)
        if self.tables_needed:
            suggestions.append(self.tables_needed)
        return suggestions if suggestions else None


class PresentationStrawman(BaseModel):
    """Simplified presentation strawman structure."""
    type: Literal["PresentationStrawman"] = "PresentationStrawman"
    # Core elements
    main_title: str
    overall_theme: str  # e.g., "Informative and data-driven"
    slides: List[Slide]
    
    # Simplified metadata
    design_suggestions: str = Field(
        description="Overall design theme like 'Modern professional with blue tones'"
    )
    target_audience: str = Field(
        description="Who will be viewing this presentation"
    )
    presentation_duration: int = Field(
        description="Expected duration in minutes"
    )

    # v3.4-v1.2: Director-generated footer text
    footer_text: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Common footer text across all slides (max 20 chars). "
                    "Used as presentation_name in Layout Builder L25 slides."
    )

    # v3.4: Preview URL from deck-builder (added dynamically)
    preview_url: Optional[str] = Field(
        default=None,
        description="Deck-builder preview URL (v3.4 fix). "
                    "Stored as attribute but strawman object returned instead of dict."
    )
    preview_presentation_id: Optional[str] = Field(
        default=None,
        description="Deck-builder presentation ID for preview"
    )

    # v3.5-visual-styles: User visual style preferences from Stage 2
    visual_style_preference: Optional[Literal["professional", "illustrated", "kids"]] = Field(
        default=None,
        description=(
            "User's preferred visual style from Stage 2 clarifying questions. "
            "Options: professional (default), illustrated (Ghibli-style), kids (bright/playful). "
            "If None, AI assigns appropriate style based on audience and theme."
        )
    )
    use_images_for_sections: bool = Field(
        default=False,
        description=(
            "Whether to use images for section divider slides (user preference). "
            "Note: Section dividers not needed in small decks (≤10 slides). "
            "For decks >10 slides, AI may enable for creative themes even if False."
        )
    )
    use_images_for_closing: bool = Field(
        default=True,
        description="Whether to use images for closing slide (default: True for memorable impact)"
    )

    # Computed properties
    @property
    def total_slides(self) -> int:
        return len(self.slides)