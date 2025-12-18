"""
Models Package for Director Agent v4.0

Contains all Pydantic models for sessions, decisions, and data structures.
"""

from .decision import (
    ActionType,
    ToolCallRequest,
    DecisionOutput,
    DecisionContext,
    ConversationTurn,
    ApprovalDetectionResult,
    StrawmanSlide,
    Strawman,
    PresentationPlan
)

from .session import SessionV4

# Re-export from preserved models
from .agents import (
    Slide,
    PresentationStrawman,
    StateContext,
    ClarifyingQuestions,
    ConfirmationPlan,
    ContentGuidance
)

from .websocket_messages import (
    ChatMessage,
    StatusUpdate,
    SlideUpdate,
    ActionRequest,
    PresentationURL,
    SyncResponse
)

from .layout import (
    LayoutSlot,
    LayoutTemplate,
    LayoutRecommendation,
    CanFitResponse,
    LayoutCapabilities
)

__all__ = [
    # Decision models
    'ActionType',
    'ToolCallRequest',
    'DecisionOutput',
    'DecisionContext',
    'ConversationTurn',
    'ApprovalDetectionResult',
    'StrawmanSlide',
    'Strawman',
    'PresentationPlan',

    # Session model
    'SessionV4',

    # Preserved agent models
    'Slide',
    'PresentationStrawman',
    'StateContext',
    'ClarifyingQuestions',
    'ConfirmationPlan',
    'ContentGuidance',

    # WebSocket messages
    'ChatMessage',
    'StatusUpdate',
    'SlideUpdate',
    'ActionRequest',
    'PresentationURL',
    'SyncResponse',

    # Layout models (v4.0 Layout Service Coordination)
    'LayoutSlot',
    'LayoutTemplate',
    'LayoutRecommendation',
    'CanFitResponse',
    'LayoutCapabilities'
]
