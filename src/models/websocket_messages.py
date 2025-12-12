"""
WebSocket Streamlined Message Protocol Models

This module defines the new streamlined message types for WebSocket communication.
Each message type has a single responsibility and maps directly to frontend UI components.
"""

from datetime import datetime, timezone
from typing import List, Optional, Literal, Union, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def format_timestamp(dt: datetime) -> str:
    """
    Format datetime to ISO 8601 with 'Z' suffix for UTC.

    Frontend JavaScript requires 'Z' suffix to correctly parse as UTC.
    Without it, new Date() parses as local time causing timezone bugs.
    """
    if dt.tzinfo is None:
        # Naive datetime - assume UTC, add Z
        return dt.isoformat() + 'Z'
    elif dt.tzinfo == timezone.utc or str(dt.tzinfo) == 'UTC':
        # UTC timezone - replace +00:00 with Z
        return dt.isoformat().replace('+00:00', 'Z')
    else:
        # Other timezone - convert to UTC first, then format
        utc_dt = dt.astimezone(timezone.utc)
        return utc_dt.isoformat().replace('+00:00', 'Z')


class MessageType(str, Enum):
    """Enum for all message types in the streamlined protocol"""
    CHAT_MESSAGE = "chat_message"
    ACTION_REQUEST = "action_request"
    SLIDE_UPDATE = "slide_update"
    STATUS_UPDATE = "status_update"
    PRESENTATION_URL = "presentation_url"  # v2.0: For deck-builder URL responses
    SYNC_RESPONSE = "sync_response"  # v3.4.2: For history sync protocol


class ChatPayload(BaseModel):
    """Payload for chat messages displayed in the chat interface"""
    text: str = Field(..., description="Main message text")
    sub_title: Optional[str] = Field(None, description="Optional subtitle")
    list_items: Optional[List[str]] = Field(None, description="Optional list of items")
    format: Literal["markdown", "plain"] = Field("markdown", description="Text format type")


class Action(BaseModel):
    """Individual action button configuration"""
    label: str = Field(..., description="Button label text")
    value: str = Field(..., description="Action value sent back when clicked")
    primary: bool = Field(False, description="Whether this is the primary action")
    requires_input: bool = Field(False, description="Whether action requires text input")


class ActionPayload(BaseModel):
    """Payload for action request messages"""
    prompt_text: str = Field(..., description="Text prompting user action")
    actions: List[Action] = Field(..., description="List of available actions")


class SlideMetadata(BaseModel):
    """Metadata about the entire presentation"""
    main_title: str = Field(..., description="Main presentation title")
    overall_theme: str = Field(..., description="Overall presentation theme")
    design_suggestions: str = Field(..., description="Design and styling suggestions")
    target_audience: str = Field(..., description="Target audience description")
    presentation_duration: int = Field(..., description="Estimated duration in minutes")
    preview_url: Optional[str] = Field(None, description="Preview URL from deck-builder (Stage 4)")
    preview_presentation_id: Optional[str] = Field(None, description="Presentation ID for Stage 4 downloads and exports")


class SlideData(BaseModel):
    """Individual slide data with all planning fields"""
    slide_id: str = Field(..., description="Unique slide identifier")
    slide_number: int = Field(..., description="Slide position in presentation")
    slide_type: str = Field(..., description="Type of slide (title_slide, content_heavy, etc.)")
    title: str = Field(..., description="Slide title")
    narrative: str = Field(..., description="The story or key message of this slide")
    key_points: List[str] = Field(..., description="Key points for the slide")
    analytics_needed: Optional[str] = Field(None, description="Description of data/charts needed")
    visuals_needed: Optional[str] = Field(None, description="Description of images/graphics needed")
    diagrams_needed: Optional[str] = Field(None, description="Description of diagrams/flows needed")
    structure_preference: Optional[str] = Field(None, description="Layout preference for the slide")
    container_layout: Optional[Dict[str, Any]] = Field(
        None, 
        description="Optional layout hints including arrangement type and container purposes"
    )


class SlideUpdatePayload(BaseModel):
    """Payload for slide update messages"""
    operation: Literal["full_update", "partial_update"] = Field(..., description="Update type")
    metadata: SlideMetadata = Field(..., description="Presentation metadata")
    slides: List[SlideData] = Field(..., description="List of slides to update")
    affected_slides: Optional[List[str]] = Field(None, description="IDs of affected slides for partial updates")


class StatusLevel(str, Enum):
    """Status levels for status updates"""
    IDLE = "idle"
    THINKING = "thinking"
    GENERATING = "generating"
    COMPLETE = "complete"
    ERROR = "error"


class StatusPayload(BaseModel):
    """Payload for status update messages"""
    status: StatusLevel = Field(..., description="Current status level")
    text: str = Field(..., description="Status message text")
    progress: Optional[int] = Field(None, description="Progress percentage (0-100)")
    estimated_time: Optional[int] = Field(None, description="Estimated time remaining in seconds")


class PresentationURLPayload(BaseModel):
    """Payload for presentation URL messages (v2.0 deck-builder)"""
    url: str = Field(..., description="Full URL to the generated presentation")
    presentation_id: str = Field(..., description="Unique presentation identifier")
    slide_count: int = Field(..., description="Number of slides in the presentation")
    message: str = Field(..., description="Human-readable success message")


class SyncResponsePayload(BaseModel):
    """
    Payload for sync response messages (v3.4.2 history sync protocol).

    This is sent when frontend requests to skip history replay via skip_history=true.
    Allows frontend to control whether Director sends full history on reconnect.
    """
    action: Literal["skip_history", "send_history", "send_delta"] = Field(
        ...,
        description="Sync action taken: skip_history (frontend has cache), send_history (full replay), send_delta (partial sync)"
    )
    message_count: int = Field(
        ...,
        description="Number of messages in Director's history (for frontend verification)"
    )
    current_state: str = Field(
        ...,
        description="Current session state (e.g., GENERATE_STRAWMAN, REFINE_STRAWMAN)"
    )
    has_strawman: bool = Field(
        False,
        description="Whether session has a strawman/presentation"
    )
    presentation_url: Optional[str] = Field(
        None,
        description="Current presentation URL if available"
    )


class BaseMessage(BaseModel):
    """Base message envelope for all message types"""
    message_id: str = Field(..., description="Unique message identifier")
    session_id: str = Field(..., description="Session identifier")
    timestamp: datetime = Field(default_factory=utc_now, description="Message timestamp (UTC)")
    type: MessageType = Field(..., description="Message type discriminator")
    role: Literal["user", "assistant"] = Field("assistant", description="Message sender role (user or assistant)")

    class Config:
        use_enum_values = True
        json_encoders = {
            # CRITICAL: Use Z suffix for UTC timestamps
            # Frontend JavaScript requires 'Z' to parse as UTC, not local time
            datetime: lambda v: format_timestamp(v)
        }


class ChatMessage(BaseMessage):
    """Chat message for conversational content"""
    type: Literal[MessageType.CHAT_MESSAGE] = MessageType.CHAT_MESSAGE
    payload: ChatPayload
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_001",
                "session_id": "session_abc",
                "timestamp": "2024-01-01T10:00:00Z",
                "type": "chat_message",
                "payload": {
                    "text": "Hello! I'm Deckster. What presentation would you like to create?",
                    "format": "markdown"
                }
            }
        }


class ActionRequest(BaseMessage):
    """Action request message for user interactions"""
    type: Literal[MessageType.ACTION_REQUEST] = MessageType.ACTION_REQUEST
    payload: ActionPayload
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_002",
                "session_id": "session_abc",
                "timestamp": "2024-01-01T10:01:00Z",
                "type": "action_request",
                "payload": {
                    "prompt_text": "Does this look correct?",
                    "actions": [
                        {"label": "Accept", "value": "accept_plan", "primary": True},
                        {"label": "Modify", "value": "reject_plan", "primary": False}
                    ]
                }
            }
        }


class SlideUpdate(BaseMessage):
    """Slide update message for presentation content"""
    type: Literal[MessageType.SLIDE_UPDATE] = MessageType.SLIDE_UPDATE
    payload: SlideUpdatePayload
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_003",
                "session_id": "session_abc",
                "timestamp": "2024-01-01T10:02:00Z",
                "type": "slide_update",
                "payload": {
                    "operation": "full_update",
                    "metadata": {
                        "main_title": "AI in Healthcare: Transforming Patient Care",
                        "overall_theme": "Data-driven and persuasive",
                        "design_suggestions": "Modern professional with blue color scheme",
                        "target_audience": "Healthcare executives",
                        "presentation_duration": 15
                    },
                    "slides": [
                        {
                            "slide_id": "slide_001",
                            "slide_number": 1,
                            "slide_type": "title_slide",
                            "title": "AI in Healthcare: Transforming Patient Care",
                            "narrative": "Setting the stage for how AI is revolutionizing healthcare delivery",
                            "key_points": ["Revolutionizing diagnostics", "Improving patient outcomes", "Reducing costs"],
                            "analytics_needed": None,
                            "visuals_needed": "**Goal:** Create an impactful opening visual. **Content:** A modern healthcare facility with AI elements. **Style:** Professional, futuristic, blue tones.",
                            "diagrams_needed": None,
                            "structure_preference": "Full-Bleed Visual"
                        }
                    ]
                }
            }
        }


class StatusUpdate(BaseMessage):
    """Status update message for progress indication"""
    type: Literal[MessageType.STATUS_UPDATE] = MessageType.STATUS_UPDATE
    payload: StatusPayload

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_004",
                "session_id": "session_abc",
                "timestamp": "2024-01-01T10:03:00Z",
                "type": "status_update",
                "payload": {
                    "status": "generating",
                    "text": "Creating your presentation...",
                    "progress": 45,
                    "estimated_time": 10
                }
            }
        }


class PresentationURL(BaseMessage):
    """Presentation URL message for v2.0 deck-builder responses"""
    type: Literal[MessageType.PRESENTATION_URL] = MessageType.PRESENTATION_URL
    payload: PresentationURLPayload

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_005",
                "session_id": "session_abc",
                "timestamp": "2024-01-01T10:04:00Z",
                "type": "presentation_url",
                "payload": {
                    "url": "https://web-production-f0d13.up.railway.app/p/abc-123",
                    "presentation_id": "abc-123",
                    "slide_count": 9,
                    "message": "Your presentation is ready! View it at: https://..."
                }
            }
        }


class SyncResponse(BaseMessage):
    """
    Sync response message for history sync protocol (v3.4.2).

    Sent when frontend requests skip_history=true on WebSocket connect.
    Allows frontend to avoid receiving duplicate messages it already has cached.
    """
    type: Literal[MessageType.SYNC_RESPONSE] = MessageType.SYNC_RESPONSE
    payload: SyncResponsePayload

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_sync_001",
                "session_id": "session_abc",
                "timestamp": "2024-01-01T10:00:00Z",
                "type": "sync_response",
                "role": "assistant",
                "payload": {
                    "action": "skip_history",
                    "message_count": 12,
                    "current_state": "REFINE_STRAWMAN",
                    "has_strawman": True,
                    "presentation_url": "https://example.com/p/abc-123"
                }
            }
        }


# Union type for all message types
StreamlinedMessage = Union[ChatMessage, ActionRequest, SlideUpdate, StatusUpdate, PresentationURL, SyncResponse]


def create_chat_message(
    session_id: str,
    text: str,
    message_id: Optional[str] = None,
    sub_title: Optional[str] = None,
    list_items: Optional[List[str]] = None,
    format: Literal["markdown", "plain"] = "markdown",
    role: Literal["user", "assistant"] = "assistant",
    timestamp: Optional[str] = None
) -> ChatMessage:
    """
    Helper function to create a chat message.

    Args:
        role: Message sender role. Defaults to "assistant".
        timestamp: Optional ISO format timestamp string. If provided, overrides default timestamp.
                   This is critical for preserving original message timestamps during session restoration.
    """
    import uuid

    msg = ChatMessage(
        message_id=message_id or f"msg_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        role=role,
        payload=ChatPayload(
            text=text,
            sub_title=sub_title,
            list_items=list_items,
            format=format
        )
    )

    # Override default timestamp if original timestamp provided (for historical messages)
    if timestamp:
        # Handle timestamps with or without Z suffix
        ts = timestamp.rstrip('Z')  # Remove Z if present for fromisoformat
        parsed = datetime.fromisoformat(ts)
        # Ensure it's UTC-aware
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        msg.timestamp = parsed

    return msg


def create_action_request(
    session_id: str,
    prompt_text: str,
    actions: List[Dict[str, Any]],
    message_id: Optional[str] = None,
    role: Literal["user", "assistant"] = "assistant"
) -> ActionRequest:
    """Helper function to create an action request"""
    import uuid
    msg = ActionRequest(
        message_id=message_id or f"msg_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        payload=ActionPayload(
            prompt_text=prompt_text,
            actions=[Action(**action) for action in actions]
        )
    )
    msg.role = role
    return msg


def create_slide_update(
    session_id: str,
    operation: Literal["full_update", "partial_update"],
    metadata: Dict[str, Any],
    slides: List[Dict[str, Any]],
    message_id: Optional[str] = None,
    affected_slides: Optional[List[str]] = None,
    role: Literal["user", "assistant"] = "assistant"
) -> SlideUpdate:
    """Helper function to create a slide update"""
    import uuid
    msg = SlideUpdate(
        message_id=message_id or f"msg_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        payload=SlideUpdatePayload(
            operation=operation,
            metadata=SlideMetadata(**metadata),
            slides=[SlideData(**slide) for slide in slides],
            affected_slides=affected_slides
        )
    )
    msg.role = role
    return msg


def create_status_update(
    session_id: str,
    status: StatusLevel,
    text: str,
    message_id: Optional[str] = None,
    progress: Optional[int] = None,
    estimated_time: Optional[int] = None,
    role: Literal["user", "assistant"] = "assistant"
) -> StatusUpdate:
    """Helper function to create a status update"""
    import uuid
    msg = StatusUpdate(
        message_id=message_id or f"msg_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        payload=StatusPayload(
            status=status,
            text=text,
            progress=progress,
            estimated_time=estimated_time
        )
    )
    msg.role = role
    return msg


def create_presentation_url(
    session_id: str,
    url: str,
    presentation_id: str,
    slide_count: int,
    message: str,
    message_id: Optional[str] = None,
    role: Literal["user", "assistant"] = "assistant"
) -> PresentationURL:
    """Helper function to create a presentation URL message (v2.0)"""
    import uuid
    msg = PresentationURL(
        message_id=message_id or f"msg_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        payload=PresentationURLPayload(
            url=url,
            presentation_id=presentation_id,
            slide_count=slide_count,
            message=message
        )
    )
    msg.role = role
    return msg


def create_sync_response(
    session_id: str,
    action: Literal["skip_history", "send_history", "send_delta"],
    message_count: int,
    current_state: str,
    has_strawman: bool = False,
    presentation_url: Optional[str] = None,
    message_id: Optional[str] = None,
    role: Literal["user", "assistant"] = "assistant"
) -> SyncResponse:
    """
    Helper function to create a sync response message (v3.4.2).

    Used by the history sync protocol to inform frontend about sync decision.

    Args:
        session_id: Current session ID
        action: Sync action taken (skip_history, send_history, send_delta)
        message_count: Number of messages in Director's conversation history
        current_state: Current session state (e.g., REFINE_STRAWMAN)
        has_strawman: Whether session has a strawman/presentation
        presentation_url: Current presentation URL if available
        message_id: Optional message ID (auto-generated if not provided)
        role: Message sender role (defaults to assistant)

    Returns:
        SyncResponse message ready to send via WebSocket
    """
    import uuid
    msg = SyncResponse(
        message_id=message_id or f"msg_sync_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        payload=SyncResponsePayload(
            action=action,
            message_count=message_count,
            current_state=current_state,
            has_strawman=has_strawman,
            presentation_url=presentation_url
        )
    )
    msg.role = role
    return msg