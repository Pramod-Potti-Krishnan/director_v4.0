"""
WebSocket Handler for Director Agent v4.0

Uses AI-driven Decision Engine instead of rigid state machine.
Preserves connection management and message protocol from v3.4.
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from src.agents.decision_engine import DecisionEngine, StrawmanGenerator
from src.models.decision import (
    DecisionContext, ActionType, ConversationTurn,
    ToolCallRequest
)
from src.models.session import SessionV4
from src.utils.session_manager import SessionManagerV4
from src.utils.deck_builder_client import DeckBuilderClient  # v4.0.5: Preview generation
from src.utils.strawman_transformer import StrawmanTransformer  # v4.0.5: Transform for deck-builder
from src.utils.text_service_client_v1_2 import TextServiceClientV1_2  # v4.0.6: Content generation
from src.tools.registry import register_all_tools, ToolCall
from src.storage.supabase import get_supabase_client
from src.models.websocket_messages import (
    StreamlinedMessage,
    StatusLevel,
    create_chat_message,
    create_status_update,
    create_slide_update,
    create_sync_response,
    create_presentation_url,
    create_action_request  # v4.0.4: For strawman approval buttons
)

from src.utils.logger import setup_logger
logger = setup_logger(__name__)


class WebSocketHandlerV4:
    """
    WebSocket handler using MCP-style Decision Engine.

    Key differences from v3.4:
    - Uses DecisionEngine for AI-driven routing
    - No state machine - decisions based on context
    - Flexible tool invocation via registry
    """

    def __init__(self):
        """Initialize handler components."""
        logger.info("Initializing WebSocketHandlerV4...")

        # Load settings
        from config.settings import get_settings
        self.settings = get_settings()

        # Defer Supabase and SessionManager initialization (lazy init)
        self.supabase = None
        self.session_manager: Optional[SessionManagerV4] = None

        # Initialize Tool Registry
        self.tool_registry = register_all_tools()
        logger.info(f"Tool Registry initialized with {len(self.tool_registry.get_tool_ids())} tools")

        # Initialize Decision Engine with configurable model
        decision_model = self.settings.GCP_MODEL_DECISION
        self.decision_engine = DecisionEngine(
            tool_registry=self.tool_registry,
            model_name=decision_model
        )
        logger.info(f"Decision Engine initialized with model: {decision_model}")

        # Initialize Strawman Generator with configurable model
        strawman_model = self.settings.GCP_MODEL_STRAWMAN
        self.strawman_generator = StrawmanGenerator(
            model_name=strawman_model
        )
        logger.info(f"Strawman Generator initialized with model: {strawman_model}")

        # v4.0.5: Initialize Deck Builder Client for preview generation
        self.deck_builder_client = DeckBuilderClient(
            api_url=self.settings.DECK_BUILDER_API_URL,
            timeout=self.settings.DECK_BUILDER_TIMEOUT
        )
        self.strawman_transformer = StrawmanTransformer()
        logger.info(f"Deck Builder Client initialized: {self.settings.DECK_BUILDER_API_URL}")

        # v4.0.6: Initialize Text Service Client for content generation
        self.text_service_client = TextServiceClientV1_2(
            base_url=self.settings.TEXT_SERVICE_URL,
            timeout=self.settings.TEXT_SERVICE_TIMEOUT
        )
        logger.info(f"Text Service Client initialized: {self.settings.TEXT_SERVICE_URL}")

        # v4.0.6: Explicit approval phrases for content generation bypass
        # v4.0.8: Added button values for action_request handling
        self.explicit_approval_phrases = [
            'generate', 'create it', 'proceed', 'go ahead', 'make it', 'do it',
            'accept_strawman', 'looks perfect'  # v4.0.8: Button values
        ]

        # Connection tracking
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_lock = asyncio.Lock()

        logger.info("WebSocketHandlerV4 initialized successfully")

    async def _ensure_initialized(self):
        """Ensure Supabase and SessionManager are initialized."""
        if self.supabase is None:
            try:
                self.supabase = await get_supabase_client()
                self.session_manager = SessionManagerV4(self.supabase)
                logger.info("Supabase and SessionManagerV4 initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase: {e}")
                raise

    async def handle_connection(self, websocket: WebSocket, session_id: str, user_id: str):
        """
        Handle a WebSocket connection.

        Args:
            websocket: FastAPI WebSocket
            session_id: Session identifier
            user_id: User identifier
        """
        await self._ensure_initialized()

        # Handle duplicate connections
        async with self.connection_lock:
            existing = self.active_connections.get(session_id)
            if existing and existing.client_state == WebSocketState.CONNECTED:
                logger.warning(f"Duplicate connection for session {session_id}, closing old")
                try:
                    await existing.close(code=4000, reason="New connection opened")
                except Exception as e:
                    logger.warning(f"Error closing old connection: {e}")

            self.active_connections[session_id] = websocket

        await websocket.accept()
        logger.info(f"WebSocket connected: session={session_id}, user={user_id}")

        # Get or create session
        session = await self.session_manager.get_or_create(session_id, user_id)

        # Send initial greeting if new session
        if not session.has_topic:
            await self._send_greeting(websocket, session)

        try:
            while True:
                # Receive message
                raw_data = await websocket.receive_text()

                # v3.4 compatibility: Handle raw "ping" string (before JSON parsing)
                if raw_data.strip() == "ping":
                    await websocket.send_text("pong")
                    continue

                data = json.loads(raw_data)

                # Handle JSON ping/pong
                if data.get('type') == 'ping':
                    await websocket.send_json({'type': 'pong', 'timestamp': datetime.utcnow().isoformat()})
                    continue

                # Process user message
                await self._process_message(websocket, session, data)

        except Exception as e:
            logger.error(f"WebSocket error for session {session_id}: {e}")

        finally:
            # Cleanup
            async with self.connection_lock:
                if self.active_connections.get(session_id) == websocket:
                    del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: session={session_id}")

    async def _process_message(
        self,
        websocket: WebSocket,
        session: SessionV4,
        data: Dict[str, Any]
    ):
        """
        Process incoming WebSocket message using Decision Engine.

        Supports both v4.0 and v3.4 message formats for backward compatibility.

        v4.0 format: {"type": "chat_message", "payload": {"content": "..."}}
        v3.4 format: {"type": "user_message", "data": {"text": "..."}}

        Args:
            websocket: WebSocket connection
            session: Current session
            data: Incoming message data
        """
        message_type = data.get('type', 'chat_message')

        # v3.4 compatibility: user_message -> chat_message
        if message_type == 'user_message':
            message_type = 'chat_message'

        # Extract user message based on format
        user_message = ''

        if message_type == 'chat_message':
            # Try v4.0 format first: payload.content
            payload = data.get('payload', {})
            user_message = payload.get('content', payload.get('message', ''))

            # Fallback to v3.4 format: data.text
            if not user_message:
                v34_data = data.get('data', {})
                user_message = v34_data.get('text', '')

        elif message_type == 'action_request':
            # Convert action to message
            payload = data.get('payload', {})
            action = payload.get('action', '')
            user_message = f"[ACTION: {action}] {payload.get('message', '')}"
        else:
            logger.warning(f"Unknown message type: {message_type}")
            return

        # v3.4 compatibility: Validate non-empty input
        if not user_message or not user_message.strip():
            logger.warning(f"Received empty/whitespace user input, ignoring")
            return

        logger.info(f"Processing message: {user_message[:100]}...")

        # Add to conversation history
        await self.session_manager.add_to_history(
            session.id, session.user_id,
            {'role': 'user', 'content': user_message, 'timestamp': datetime.utcnow().isoformat()}
        )

        # Refresh session
        session = await self.session_manager.get_or_create(session.id, session.user_id)

        # v4.0.8: Check for plan acceptance button click - trigger strawman generation
        # This handles the "Yes, let's build it!" button click
        if 'accept_plan' in user_message.lower() and session.has_plan and not session.has_strawman:
            logger.info("Plan acceptance detected - generating strawman (bypassing Decision Engine)")
            from src.models.decision import DecisionOutput
            mock_decision = DecisionOutput(
                action_type=ActionType.GENERATE_STRAWMAN,
                reasoning="User accepted plan via button click",
                confidence=1.0
            )
            await self._execute_decision(websocket, session, mock_decision)
            return

        # v4.0.6: Check for explicit approval with strawman - bypass Decision Engine
        # This ensures content generation works deterministically like v3.4
        if self._is_explicit_approval(user_message) and session.has_strawman and not session.has_content:
            logger.info("Explicit approval detected with strawman - bypassing Decision Engine for content generation")
            await self._handle_content_generation(websocket, session)
            return

        # Build decision context
        context = self._build_decision_context(session, user_message)

        # Get decision from AI
        try:
            decision = await self.decision_engine.decide(context)
            logger.info(f"Decision: action={decision.action_type}, confidence={decision.confidence}")

            # Execute decision
            await self._execute_decision(websocket, session, decision)

        except Exception as e:
            logger.error(f"Decision engine error: {e}")
            await self._send_error(websocket, session, str(e))

    def _build_decision_context(
        self,
        session: SessionV4,
        user_message: str
    ) -> DecisionContext:
        """Build DecisionContext from session state."""
        # Convert conversation history to ConversationTurn format
        history = []
        for msg in session.conversation_history[-10:]:  # Last 10 turns
            history.append(ConversationTurn(
                role=msg.get('role', 'user'),
                content=msg.get('content', ''),
                timestamp=msg.get('timestamp')
            ))

        return DecisionContext(
            user_message=user_message,
            conversation_history=history,
            has_topic=session.has_topic,
            has_audience=session.has_audience,
            has_duration=session.has_duration,
            has_purpose=session.has_purpose,
            has_plan=session.has_plan,
            has_strawman=session.has_strawman,
            has_explicit_approval=session.has_explicit_approval,
            has_content=session.has_content,
            is_complete=session.is_complete,
            initial_request=session.initial_request,
            topic=session.topic,
            audience=session.audience,
            duration=session.duration,
            purpose=session.purpose,
            tone=session.tone,
            strawman=session.strawman,
            generated_slides=session.generated_slides,
            presentation_id=session.presentation_id,
            preview_url=session.presentation_url
        )

    async def _execute_decision(
        self,
        websocket: WebSocket,
        session: SessionV4,
        decision
    ):
        """
        Execute the decision from Decision Engine.

        Args:
            websocket: WebSocket connection
            session: Current session
            decision: DecisionOutput from engine
        """
        # v4.0.1: Always extract and update context from any decision
        # This ensures topic/audience/duration/purpose are captured
        # regardless of which action the AI decides to take
        await self._update_session_from_response(session, decision)

        # Refresh session after update to get latest flags
        session = await self.session_manager.get_or_create(session.id, session.user_id)

        action = decision.action_type

        if action == ActionType.RESPOND:
            await self._handle_respond(websocket, session, decision)

        elif action == ActionType.ASK_QUESTIONS:
            await self._handle_ask_questions(websocket, session, decision)

        elif action == ActionType.PROPOSE_PLAN:
            await self._handle_propose_plan(websocket, session, decision)

        elif action == ActionType.GENERATE_STRAWMAN:
            await self._handle_generate_strawman(websocket, session, decision)

        elif action == ActionType.REFINE_STRAWMAN:
            await self._handle_refine_strawman(websocket, session, decision)

        elif action == ActionType.INVOKE_TOOLS:
            await self._handle_invoke_tools(websocket, session, decision)

        elif action == ActionType.COMPLETE:
            await self._handle_complete(websocket, session, decision)

        else:
            logger.warning(f"Unknown action type: {action}")
            await self._send_chat(websocket, session, "I'm not sure how to handle that. Can you rephrase?")

    async def _handle_respond(self, websocket: WebSocket, session: SessionV4, decision):
        """Handle RESPOND action - send conversational response."""
        response_text = decision.response_text or "I understand. How can I help you further?"
        # Context extraction is done in _execute_decision before this is called
        await self._send_chat(websocket, session, response_text)

    async def _handle_ask_questions(self, websocket: WebSocket, session: SessionV4, decision):
        """Handle ASK_QUESTIONS action - ask clarifying questions."""
        questions = decision.questions or []
        intro = decision.response_text or "To create the best presentation, I have a few questions:"

        # Format as chat message
        message = intro + "\n\n" + "\n".join([f"• {q}" for q in questions])

        await self._send_chat(websocket, session, message)

    async def _handle_propose_plan(self, websocket: WebSocket, session: SessionV4, decision):
        """
        Handle PROPOSE_PLAN action - propose presentation structure.

        v4.0.8: Added action buttons for plan confirmation (like v3.4 Stage 3).
        """
        plan_data = decision.plan_data or {}

        message = decision.response_text or f"""Here's my proposed plan for your presentation:

**Summary:** {plan_data.get('summary', 'Your presentation')}

**Proposed Slides:** {plan_data.get('proposed_slide_count', 10)} slides

**Key Assumptions:**
{chr(10).join(['• ' + a for a in plan_data.get('key_assumptions', [])])}"""

        # Update session
        await self.session_manager.update_progress(
            session.id, session.user_id,
            {'has_plan': True}
        )

        await self._send_chat(websocket, session, message)

        # v4.0.8: Add action buttons for plan confirmation (like v3.4 Stage 3)
        action_msg = create_action_request(
            session_id=session.id,
            prompt_text="Does this structure work for you?",
            actions=[
                {
                    "label": "Yes, let's build it!",
                    "value": "accept_plan",
                    "primary": True,
                    "requires_input": False
                },
                {
                    "label": "I'd like to make changes",
                    "value": "reject_plan",
                    "primary": False,
                    "requires_input": True
                }
            ]
        )
        await websocket.send_json(action_msg.model_dump(mode='json'))

    async def _handle_generate_strawman(self, websocket: WebSocket, session: SessionV4, decision):
        """Handle GENERATE_STRAWMAN action - create presentation outline.

        v4.0.13: Added topic validation guard to prevent "Untitled" presentations.
        """
        # v4.0.13: LAYER 4 - Guard: Refuse to generate without valid topic
        topic = session.topic or session.initial_request

        invalid_topics = ['untitled', 'presentation', 'unknown', 'your presentation', '']
        if not topic or topic.lower().strip() in invalid_topics:
            logger.warning(f"Attempted strawman generation without valid topic: '{topic}'")
            await self._send_chat(
                websocket, session,
                "I'd love to create a presentation outline for you! "
                "Could you tell me what topic you'd like to present on?"
            )
            return

        # Send status
        await self._send_status(websocket, session, "Generating presentation outline...")

        logger.info(f"Generating strawman for topic: {topic}")

        # Generate strawman
        strawman = await self.strawman_generator.generate(
            topic=topic,
            audience=session.audience or "general",
            duration=session.duration or 15,
            purpose=session.purpose or "inform"
        )

        # Save strawman
        strawman_dict = strawman.dict()
        await self.session_manager.save_strawman(
            session.id, session.user_id, strawman_dict
        )

        # v4.0.5: Create preview presentation with deck-builder
        preview_url = None
        preview_presentation_id = None
        try:
            logger.info("Creating preview presentation with deck-builder...")

            # Transform strawman to deck-builder format
            api_payload = self.strawman_transformer.transform(strawman_dict, topic)

            # Call deck-builder API
            api_response = await self.deck_builder_client.create_presentation(api_payload)

            # v4.0.13: Defensive null check for deck-builder response
            if not api_response or not isinstance(api_response, dict):
                logger.error(f"Deck-builder returned invalid response for preview: {type(api_response)}")
                raise ValueError("Deck-builder API returned invalid response")

            url_path = api_response.get('url')
            if not url_path:
                logger.error(f"Deck-builder preview response missing 'url': {api_response}")
                raise ValueError("Deck-builder response missing 'url' field")

            preview_url = self.deck_builder_client.get_full_url(url_path)
            preview_presentation_id = api_response.get('id', '')

            logger.info(f"Preview created: {preview_url} (id: {preview_presentation_id})")

        except Exception as e:
            logger.error(f"Failed to create preview with deck-builder: {e}")
            # Continue without preview - frontend will show skeletons

        # Refresh session to get updated strawman flag
        session = await self.session_manager.get_or_create(session.id, session.user_id)

        # Send slide update (with preview_url if available)
        await self._send_slide_update(
            websocket, session, strawman_dict,
            preview_url=preview_url,
            preview_presentation_id=preview_presentation_id
        )

        # Send follow-up message (like v3.4)
        if preview_url:
            await self._send_chat(
                websocket, session,
                f"I've created an outline with {len(strawman.slides)} slides for **{topic}**. "
                "Review the structural outline in the preview. You can request changes or approve it to proceed."
            )
        else:
            await self._send_chat(
                websocket, session,
                f"I've created an outline with {len(strawman.slides)} slides for **{topic}**. "
                "Review the structure and approve it to proceed."
            )

        # v4.0.4: Send action request for user to approve or refine (like v3.4)
        action_msg = create_action_request(
            session_id=session.id,
            prompt_text="Does this outline look good, or would you like to make changes?",
            actions=[
                {
                    "label": "Looks perfect!",
                    "value": "accept_strawman",
                    "primary": True,
                    "requires_input": False
                },
                {
                    "label": "Make some changes",
                    "value": "request_refinement",
                    "primary": False,
                    "requires_input": True
                }
            ]
        )
        await websocket.send_json(action_msg.model_dump(mode='json'))

    async def _handle_refine_strawman(self, websocket: WebSocket, session: SessionV4, decision):
        """Handle REFINE_STRAWMAN action - modify existing outline."""
        await self._send_status(websocket, session, "Refining presentation outline...")

        # Get refinement feedback from decision
        feedback = decision.response_text or ""

        # For now, just acknowledge - full refinement would involve AI call
        await self._send_chat(
            websocket, session,
            "I've noted your feedback. Let me update the outline accordingly."
        )

    async def _handle_invoke_tools(self, websocket: WebSocket, session: SessionV4, decision):
        """Handle INVOKE_TOOLS action - call content generation tools."""
        tool_calls = decision.tool_calls or []

        if not tool_calls:
            await self._send_chat(websocket, session, "Ready to generate content when you give the go-ahead.")
            return

        # Send status
        await self._send_status(websocket, session, "Generating presentation content...")

        # Execute tools
        session_context = session.get_decision_context()

        for tool_request in tool_calls:
            try:
                tool_call = ToolCall(
                    tool_id=tool_request.tool_id,
                    parameters=tool_request.parameters,
                    context=session_context
                )

                result = await self.tool_registry.execute(
                    tool_call, session_context, check_approval=False
                )

                if result.success:
                    logger.info(f"Tool {tool_request.tool_id} executed successfully")
                else:
                    logger.warning(f"Tool {tool_request.tool_id} failed: {result.error}")

            except Exception as e:
                logger.error(f"Tool execution error: {e}")

        # Update session
        await self.session_manager.update_progress(
            session.id, session.user_id,
            {'has_content': True}
        )

        await self._send_chat(
            websocket, session,
            "Content generation complete! Your presentation is ready."
        )

    async def _handle_complete(self, websocket: WebSocket, session: SessionV4, decision):
        """Handle COMPLETE action - presentation finished."""
        message = decision.response_text or "Your presentation is complete! You can view it using the preview link."

        # Mark as complete
        await self.session_manager.update_progress(
            session.id, session.user_id,
            {'is_complete': True}
        )

        # Send presentation URL if available
        if session.presentation_url:
            await self._send_presentation_url(websocket, session)

        await self._send_chat(websocket, session, message)

    async def _update_session_from_response(self, session: SessionV4, decision):
        """Update session based on information extracted from AI decision.

        v4.0.1: The Decision Engine now extracts context (topic, audience, etc.)
        from user messages and returns them in decision.extracted_context.
        v4.0.10: Updated to handle typed ExtractedContext model (Gemini compatible).
        v4.0.13: Added diagnostic logging and fallback topic extraction.
        """
        # v4.0.13: Diagnostic logging to trace topic extraction
        logger.info(f"=== _update_session_from_response DEBUG ===")
        logger.info(f"  decision.action_type: {decision.action_type}")
        response_preview = decision.response_text[:100] if decision.response_text else 'None'
        logger.info(f"  response_text[:100]: {response_preview}...")

        # v4.0.10: Handle typed ExtractedContext model (has attributes, not dict keys)
        # Use getattr for model, get() for dict fallback
        def get_value(obj, key, default=None):
            """Get value from either typed model or dict."""
            if hasattr(obj, key):
                return getattr(obj, key, default)
            elif isinstance(obj, dict):
                return obj.get(key, default)
            return default

        extracted = getattr(decision, 'extracted_context', None)

        # v4.0.13: Log extracted context details
        if extracted:
            logger.info(f"  extracted.topic: {get_value(extracted, 'topic', 'N/A')}")
            logger.info(f"  extracted.has_topic: {get_value(extracted, 'has_topic', 'N/A')}")
        else:
            logger.warning(f"  extracted_context is None/missing!")

        # v4.0.13: LAYER 3 - Fallback: Parse topic from response_text if not in extracted_context
        if not extracted or not get_value(extracted, 'topic'):
            fallback_topic = self._extract_topic_from_response(decision.response_text)
            if fallback_topic:
                logger.info(f"  -> Fallback extracted topic from response_text: {fallback_topic}")
                if not extracted:
                    from src.models.decision import ExtractedContext
                    extracted = ExtractedContext(topic=fallback_topic, has_topic=True)
                else:
                    # Update existing extracted context (model has mutable fields)
                    if hasattr(extracted, 'topic'):
                        extracted.topic = fallback_topic
                        extracted.has_topic = True

        if not extracted:
            logger.info("  -> No extracted context to process (even after fallback)")
            return

        updates = {}

        # v4.0.15: Extract key session data with GUARDS against overwriting
        # Once a field is set, don't overwrite it from subsequent messages
        topic = get_value(extracted, 'topic')
        if topic:
            # Only set topic if not already established
            if not session.topic:
                updates['topic'] = topic
                updates['has_topic'] = True
                # Also set as initial_request if not set
                if not session.initial_request:
                    updates['initial_request'] = topic
                logger.info(f"  → Extracted topic: {topic}")
            else:
                logger.info(f"  → Ignoring extracted topic '{topic}' - session already has topic '{session.topic}'")

        audience = get_value(extracted, 'audience')
        if audience:
            # Only set audience if not already established
            if not session.audience:
                updates['audience'] = audience
                updates['has_audience'] = True
                logger.info(f"  → Extracted audience: {audience}")
            else:
                logger.info(f"  → Ignoring extracted audience - session already has: '{session.audience}'")

        duration = get_value(extracted, 'duration')
        if duration:
            # Only set duration if not already established
            if not session.duration:
                try:
                    updates['duration'] = int(duration)
                    updates['has_duration'] = True
                    logger.info(f"  → Extracted duration: {duration}")
                except (ValueError, TypeError):
                    pass
            else:
                logger.info(f"  → Ignoring extracted duration - session already has: {session.duration}")

        purpose = get_value(extracted, 'purpose')
        if purpose:
            # Only set purpose if not already established
            if not session.purpose:
                updates['purpose'] = purpose
                updates['has_purpose'] = True
                logger.info(f"  → Extracted purpose: {purpose}")
            else:
                logger.info(f"  → Ignoring extracted purpose - session already has: '{session.purpose}'")

        tone = get_value(extracted, 'tone')
        if tone:
            # Only set tone if not already established
            if not session.tone:
                updates['tone'] = tone
                logger.info(f"  → Extracted tone: {tone}")
            else:
                logger.info(f"  → Ignoring extracted tone - session already has: '{session.tone}'")

        # Also accept explicit boolean flags from the AI
        for flag in ['has_topic', 'has_audience', 'has_duration', 'has_purpose']:
            flag_value = get_value(extracted, flag)
            if flag_value is True and flag not in updates:
                updates[flag] = True

        # Update session if we have changes
        if updates:
            logger.info(f"Updating session with extracted context: {list(updates.keys())}")
            await self.session_manager.update_progress(
                session.id, session.user_id, updates
            )

    async def _send_greeting(self, websocket: WebSocket, session: SessionV4):
        """Send initial greeting message."""
        greeting = (
            "Hello! I'm your presentation assistant. "
            "I can help you create professional presentations. "
            "What topic would you like to present on?"
        )
        await self._send_chat(websocket, session, greeting)

    async def _send_chat(self, websocket: WebSocket, session: SessionV4, message: str):
        """Send chat message."""
        # Add to history
        await self.session_manager.add_to_history(
            session.id, session.user_id,
            {'role': 'assistant', 'content': message, 'timestamp': datetime.utcnow().isoformat()}
        )

        chat_msg = create_chat_message(session.id, message)
        await websocket.send_json(chat_msg.model_dump(mode='json'))

    async def _send_status(self, websocket: WebSocket, session: SessionV4, message: str, status: StatusLevel = StatusLevel.THINKING):
        """Send status update."""
        status_msg = create_status_update(session.id, status, message)
        await websocket.send_json(status_msg.model_dump(mode='json'))

    async def _send_slide_update(
        self,
        websocket: WebSocket,
        session: SessionV4,
        strawman: Dict,
        preview_url: Optional[str] = None,
        preview_presentation_id: Optional[str] = None
    ):
        """Send slide update with strawman.

        v4.0.4: Enhanced to include all fields expected by frontend (matching v3.4 format).
        v4.0.5: Added preview_url and preview_presentation_id for right panel rendering.
        """
        # v4.0.4: Get topic from strawman or session
        topic = strawman.get('title') or session.topic or session.initial_request or 'Untitled'

        # Convert strawman to slides format expected by frontend (SlideData model)
        slides = []
        for idx, slide in enumerate(strawman.get('slides', [])):
            # Determine slide type based on hero_type or layout
            hero_type = slide.get('hero_type')
            if hero_type:
                slide_type = hero_type  # title_slide, section_divider, closing_slide
            elif slide.get('is_hero'):
                slide_type = 'hero'
            else:
                slide_type = 'content'

            # Build narrative - prefer notes, then generate from title/topic
            slide_title = slide.get('title', f'Slide {idx + 1}')
            narrative = slide.get('notes', '')
            if not narrative:
                narrative = f"Key content about {slide_title}"

            slides.append({
                'slide_id': slide.get('slide_id', f'slide_{idx+1}'),
                'slide_number': slide.get('slide_number', idx + 1),
                'slide_type': slide_type,
                'title': slide_title,
                'narrative': narrative,
                'key_points': slide.get('topics', []),
                'analytics_needed': None,
                'visuals_needed': None,
                'diagrams_needed': None,
                'structure_preference': slide.get('layout', 'L01')
            })

        logger.info(f"Sending slide_update with {len(slides)} slides for topic: {topic}, preview_url: {preview_url}")

        slide_msg = create_slide_update(
            session_id=session.id,
            operation="full_update",
            metadata={
                'main_title': topic,  # v4.0.4: Use topic as main_title
                'slide_count': len(slides),
                'overall_theme': 'professional',
                'design_suggestions': '',
                'target_audience': session.audience or 'general',
                'presentation_duration': session.duration or 15,
                'preview_url': preview_url,  # v4.0.5: For right panel rendering
                'preview_presentation_id': preview_presentation_id  # v4.0.5: For tracking
            },
            slides=slides
        )
        await websocket.send_json(slide_msg.model_dump(mode='json'))

    async def _send_presentation_url(self, websocket: WebSocket, session: SessionV4):
        """Send presentation URL."""
        if not session.presentation_url:
            return

        url_msg = create_presentation_url(
            session_id=session.id,
            url=session.presentation_url,
            presentation_id=session.presentation_id or '',
            message="Your presentation is ready!"
        )
        await websocket.send_json(url_msg.model_dump(mode='json'))

    async def _send_error(self, websocket: WebSocket, session: SessionV4, error: str):
        """Send error message."""
        await self._send_chat(
            websocket, session,
            f"I encountered an issue: {error}. Please try again."
        )

    # ========== v4.0.6: Content Generation Methods ==========

    def _is_explicit_approval(self, message: str) -> bool:
        """
        Check if message contains explicit approval for content generation.

        v4.0.6: Deterministic check for approval phrases.

        Args:
            message: User message

        Returns:
            True if explicit approval detected
        """
        message_lower = message.lower().strip()

        for phrase in self.explicit_approval_phrases:
            if phrase in message_lower:
                return True

        return False

    def _extract_topic_from_response(self, response_text: str) -> Optional[str]:
        """
        v4.0.13: Fallback topic extraction from AI response text.

        Parses common patterns where AI acknowledges a topic but didn't populate
        extracted_context.topic (Gemini sometimes fails to do this).

        Patterns detected:
        - "Great! 'Sri Krishna' is a fascinating topic"
        - "'Machine Learning' sounds like an interesting topic"
        - "presentation on 'Climate Change'"

        Args:
            response_text: The AI's response text

        Returns:
            Extracted topic string or None
        """
        if not response_text:
            return None

        import re

        # Pattern 1: Quoted topic (single or double quotes) followed by topic-related words
        quoted_patterns = [
            r"['\"]([^'\"]{2,50})['\"].*(?:is|sounds|as).*(?:topic|subject|interesting|great|fascinating)",
            r"(?:topic|presentation|deck).*(?:about|on|for).*['\"]([^'\"]{2,50})['\"]",
            r"['\"]([^'\"]{2,50})['\"].*(?:presentation|deck|slides)",
        ]

        for pattern in quoted_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                topic = match.group(1).strip()
                logger.info(f"Fallback parser found quoted topic: '{topic}'")
                return topic

        # Pattern 2: "about X" patterns without quotes (less reliable, only use if starts with capital)
        about_pattern = r"(?:presentation|deck|slides).*(?:about|on|for)\s+([A-Z][^\.,!?]{2,40})"
        match = re.search(about_pattern, response_text)
        if match:
            topic = match.group(1).strip()
            logger.info(f"Fallback parser found 'about' topic: '{topic}'")
            return topic

        logger.debug(f"Fallback parser found no topic in response")
        return None

    async def _handle_content_generation(self, websocket: WebSocket, session: SessionV4):
        """
        Handle content generation when user explicitly approves.

        v4.0.6: Bypasses Decision Engine and calls text-service directly.
        Simplified pipeline (text-service only for content slides).

        Args:
            websocket: WebSocket connection
            session: Current session
        """
        await self._send_status(websocket, session, "Generating presentation content...")

        try:
            # 1. Get strawman slides
            strawman = session.strawman
            if not strawman:
                await self._send_chat(websocket, session, "No presentation outline found. Let me create one first.")
                return

            # 2. Generate content for each slide via text-service
            logger.info(f"Generating content for {len(strawman.get('slides', []))} slides...")
            enriched_slides = await self._generate_slide_content(strawman, session)

            # 3. Create final presentation with generated content (v3.4 approach)
            logger.info("Creating final presentation with generated content...")
            final_url, final_id = await self._create_final_presentation(enriched_slides, session)

            # 4. Update session
            await self.session_manager.update_progress(
                session.id, session.user_id,
                {
                    'has_content': True,
                    'has_explicit_approval': True,
                    'presentation_url': final_url,
                    'presentation_id': final_id
                }
            )

            # Refresh session
            session = await self.session_manager.get_or_create(session.id, session.user_id)

            # 5. Send completion message with URL
            await self._send_presentation_complete(websocket, session, final_url)

        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            await self._send_chat(
                websocket, session,
                f"Sorry, content generation encountered an error: {str(e)[:100]}"
            )

    def _select_variant_for_slide(self, slide: Dict[str, Any]) -> str:
        """
        Select appropriate text-service variant based on slide content.

        v4.0.7: Simple count-based selection using valid variants from registry.
        This fixes HTTP 422 errors caused by invalid variant_id.

        Args:
            slide: Slide dict with 'topics' list

        Returns:
            Valid variant_id for text-service v1.2
        """
        topics = slide.get('topics', [])
        topic_count = len(topics)

        # Select variant based on topic count
        # All variants verified valid in config/unified_variant_registry.json
        if topic_count <= 2:
            return 'comparison_2col'  # Good for pros/cons, before/after
        elif topic_count == 3:
            return 'sequential_3col'  # Good for 3-step processes
        elif topic_count == 4:
            return 'grid_2x2_centered'  # 2x2 grid with icons
        elif topic_count == 5:
            return 'sequential_5col'  # 5-step process
        else:
            return 'grid_2x3'  # 6+ items, use 2x3 grid (default)

    def _validate_text_request(self, request: Dict[str, Any]) -> tuple:
        """
        v4.0.9: Validate request before sending to Text Service v1.2.

        Args:
            request: Request dict to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str or None)
        """
        # Required fields in slide_spec
        required_slide_fields = ['slide_title', 'slide_purpose', 'key_message', 'tone', 'audience']
        slide_spec = request.get('slide_spec', {})

        for field in required_slide_fields:
            if field not in slide_spec:
                return False, f"Missing required field: slide_spec.{field}"
            if slide_spec[field] is None or slide_spec[field] == '':
                return False, f"Empty required field: slide_spec.{field}"

        # Required top-level fields
        if not request.get('variant_id'):
            return False, "Missing required field: variant_id"

        # v4.0.20: Validate target_points has at least one topic
        # Empty target_points causes Text Service LLM to return null
        target_points = slide_spec.get('target_points', [])
        if not target_points:
            return False, "target_points is empty - cannot generate content (LLM needs input)"

        return True, None

    async def _generate_single_slide(
        self,
        idx: int,
        slide: Dict[str, Any],
        session: SessionV4,
        total_slides: int
    ) -> Dict[str, Any]:
        """
        Generate content for a single slide.

        v4.0.23: Added for parallel slide generation.

        Args:
            idx: Slide index (0-based)
            slide: Slide dict from strawman
            session: Current session
            total_slides: Total number of slides

        Returns:
            Dict with slide content and 'idx' for ordering
        """
        import json as _json
        import traceback

        slide_id = slide.get('slide_id', f'slide_{idx+1}')
        is_hero = slide.get('is_hero', False)
        hero_type = slide.get('hero_type')

        try:
            if is_hero or hero_type:
                # v4.0.24: Hero slides - Call Text Service hero endpoints for rich content with images
                logger.info(f"Slide {idx+1}/{total_slides}: Hero slide ({hero_type or 'hero'})")

                presentation_title = session.topic or session.initial_request or 'Untitled Presentation'

                # v4.0.25: Map hero_type to endpoint (use -with-image for background images)
                endpoint_map = {
                    'title_slide': '/v1.2/hero/title-with-image',
                    'section_divider': '/v1.2/hero/section-with-image',
                    'closing_slide': '/v1.2/hero/closing-with-image'
                }
                endpoint = endpoint_map.get(hero_type, '/v1.2/hero/title-with-image')

                # Build hero request payload
                hero_payload = {
                    "slide_number": idx + 1,
                    "slide_type": hero_type or "title_slide",
                    "narrative": slide.get('notes') or slide.get('narrative') or '',
                    "topics": slide.get('topics') or [],
                    "visual_style": "professional",  # v4.0.25: Required for -with-image endpoints
                    "context": {
                        "presentation_title": presentation_title,
                        "total_slides": total_slides,
                        "tone": session.tone or "professional",
                        "audience": session.audience or "general"
                    }
                }

                try:
                    result = await self.text_service_client.call_hero_endpoint(endpoint, hero_payload)
                    html_content = result.get('html_content') or result.get('html', '')

                    if not html_content:
                        raise ValueError("Empty HTML from hero endpoint")

                    logger.info(f"  ✅ Hero slide {idx+1} generated via Text Service ({endpoint})")

                except Exception as e:
                    logger.warning(f"  ⚠️ Hero endpoint failed, using fallback: {e}")
                    # Fallback to local HTML (with null-safe subtitle from Change 2)
                    if hero_type == 'title_slide':
                        html_content = self.strawman_transformer._create_title_slide_html(presentation_title, slide)
                    else:
                        html_content = self.strawman_transformer._create_hero_html(slide, hero_type)

                return {
                    'idx': idx,
                    'slide_id': slide_id,
                    'layout': 'L29',
                    'content': html_content,
                    'is_hero': True,
                    'hero_type': hero_type
                }
            else:
                # Content slides: Call text-service
                logger.info(f"Slide {idx+1}/{total_slides}: Content slide - calling text-service")

                # v4.0.23: Prefer variant from strawman, fallback to selector
                strawman_variant = slide.get('variant_id')
                variant_id = strawman_variant or self._select_variant_for_slide(slide)
                variant_source = 'strawman' if strawman_variant else 'fallback'
                topics = slide.get('topics', [])

                # Handle empty topics
                if not topics:
                    slide_title = slide.get('title', 'Slide')
                    slide_notes = slide.get('notes', '')

                    if slide_notes:
                        topics = [
                            f"Key point: {slide_notes[:80]}",
                            f"Details about {slide_title}",
                            f"Understanding {slide_title}"
                        ]
                    else:
                        topics = [
                            f"Key aspects of {slide_title}",
                            f"Important details about {slide_title}",
                            f"Understanding {slide_title}"
                        ]
                    logger.warning(f"  ⚠️ Slide {idx+1}: Empty topics, generated fallback")

                logger.info(f"  → Variant: {variant_id} (source: {variant_source}, {len(topics)} topics)")

                key_message = ' | '.join(topics[:3]) if topics else slide.get('title', '')
                slide_title = slide.get('title', 'this topic')
                notes = slide.get('notes')
                slide_purpose = notes if notes else f"Present key points about {slide_title}"

                request = {
                    'variant_id': variant_id,
                    'slide_spec': {
                        'slide_title': slide.get('title', 'Slide'),
                        'slide_purpose': slide_purpose,
                        'key_message': key_message,
                        'target_points': topics,
                        'tone': session.tone or 'professional',
                        'audience': session.audience or 'general audience'
                    },
                    'presentation_spec': {
                        'presentation_title': session.topic or session.initial_request or 'Presentation',
                        'presentation_type': session.purpose or 'Informational',
                        'current_slide_number': idx + 1,
                        'total_slides': total_slides
                    },
                    'enable_parallel': True,
                    'validate_character_counts': False
                }

                # Validate request
                is_valid, error_msg = self._validate_text_request(request)
                if not is_valid:
                    raise ValueError(f"Request validation failed: {error_msg}")

                logger.info(f"  📤 Text Service request (slide {idx+1})")

                # Capture request for debugging
                from src.utils.debug_capture import capture_text_service_request
                capture_text_service_request(
                    session_id=session.id,
                    slide_index=idx,
                    request=request
                )

                result = await self.text_service_client.generate(request)

                # Capture response
                response_data = {
                    'content': result.content if hasattr(result, 'content') else str(result),
                    'has_content': hasattr(result, 'content'),
                    'result_type': type(result).__name__
                }
                capture_text_service_request(
                    session_id=session.id,
                    slide_index=idx,
                    request=request,
                    response=response_data
                )

                logger.info(f"  ✅ Slide {idx+1} generated successfully")

                return {
                    'idx': idx,
                    'slide_id': slide_id,
                    'layout': 'L25',
                    'content': result.content if hasattr(result, 'content') else str(result),
                    'is_hero': False,
                    'title': slide.get('title', '')
                }

        except Exception as e:
            full_traceback = traceback.format_exc()
            logger.warning(
                f"  ⚠️ Slide {idx+1} failed, using fallback: {type(e).__name__}: {str(e)[:200]}"
            )

            # Capture error
            from src.utils.debug_capture import capture_text_service_request
            capture_text_service_request(
                session_id=session.id,
                slide_index=idx,
                request=locals().get('request', {}),
                error=f"{type(e).__name__}: {str(e)}\n{full_traceback}"
            )

            # Fallback: use strawman transformer content
            fallback_html = self.strawman_transformer._create_content_html(slide)
            return {
                'idx': idx,
                'slide_id': slide_id,
                'layout': 'L25',
                'content': fallback_html,
                'is_hero': False,
                'title': slide.get('title', ''),
                'fallback': True
            }

    async def _generate_slide_content(
        self,
        strawman: Dict[str, Any],
        session: SessionV4
    ) -> List[Dict[str, Any]]:
        """
        Generate content for all slides in strawman using PARALLEL execution.

        v4.0.23: Uses asyncio.gather() for parallel slide generation.
        Previously sequential (~30-50s), now parallel (~5s).

        Args:
            strawman: Strawman dict with slides
            session: Current session

        Returns:
            List of enriched slides with generated content
        """
        import asyncio

        slides = strawman.get('slides', [])
        total_slides = len(slides)

        logger.info(f"🚀 Starting PARALLEL generation for {total_slides} slides...")

        # Create tasks for all slides
        tasks = [
            self._generate_single_slide(idx, slide, session, total_slides)
            for idx, slide in enumerate(slides)
        ]

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results, handle any unexpected exceptions
        enriched_slides = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # This shouldn't happen since _generate_single_slide catches exceptions
                logger.error(f"Unexpected task exception for slide {i+1}: {result}")
                # Create fallback result
                slide = slides[i]
                fallback_html = self.strawman_transformer._create_content_html(slide)
                enriched_slides.append({
                    'idx': i,
                    'slide_id': slide.get('slide_id', f'slide_{i+1}'),
                    'layout': 'L25',
                    'content': fallback_html,
                    'is_hero': False,
                    'title': slide.get('title', ''),
                    'fallback': True
                })
            else:
                enriched_slides.append(result)

        # Sort by idx to maintain original slide order
        enriched_slides.sort(key=lambda x: x.get('idx', 0))

        # Remove idx field from final output
        for slide in enriched_slides:
            slide.pop('idx', None)

        # Log summary
        fallback_count = sum(1 for s in enriched_slides if s.get('fallback'))
        if fallback_count > 0:
            logger.warning(
                f"✅ Parallel generation complete: {fallback_count}/{total_slides} slides used fallback"
            )
        else:
            logger.info(f"✅ Parallel generation complete: All {total_slides} slides successful")

        return enriched_slides

    async def _create_final_presentation(
        self,
        enriched_slides: List[Dict[str, Any]],
        session: SessionV4
    ) -> tuple:
        """
        Create final presentation with generated content.

        v4.0.6: Creates NEW presentation with enriched content (v3.4 approach).

        Args:
            enriched_slides: List of slides with generated content
            session: Current session

        Returns:
            Tuple of (presentation_url, presentation_id)
        """
        # Build presentation payload
        slides_payload = []

        for slide in enriched_slides:
            if slide.get('is_hero') or slide.get('layout') == 'L29':
                slides_payload.append({
                    'layout': 'L29',
                    'content': {'hero_content': slide['content']}
                })
            else:
                slides_payload.append({
                    'layout': 'L25',
                    'content': {
                        'slide_title': slide.get('title', ''),
                        'rich_content': slide['content']
                    }
                })

        # Create NEW presentation (v3.4 approach - not update)
        presentation_data = {
            'title': session.topic or session.initial_request or 'Presentation',
            'slides': slides_payload
        }

        logger.info(f"Creating final presentation with {len(slides_payload)} slides...")
        api_response = await self.deck_builder_client.create_presentation(presentation_data)

        # v4.0.13: Defensive null check for deck-builder response
        if not api_response or not isinstance(api_response, dict):
            logger.error(f"Deck-builder returned invalid response for final presentation: {type(api_response)}")
            raise ValueError("Deck-builder API returned invalid response for final presentation")

        url_path = api_response.get('url')
        if not url_path:
            logger.error(f"Deck-builder final response missing 'url': {api_response}")
            raise ValueError("Deck-builder response missing 'url' field")

        final_url = self.deck_builder_client.get_full_url(url_path)
        final_id = api_response.get('id', '')

        if not final_id:
            logger.warning("Deck-builder final response missing 'id', using empty string")

        logger.info(f"Final presentation created: {final_url} (id: {final_id})")
        return final_url, final_id

    async def _send_presentation_complete(
        self,
        websocket: WebSocket,
        session: SessionV4,
        presentation_url: str
    ):
        """
        Send presentation completion message with URL.

        v4.0.6: Sends both chat message and presentation_url message.
        v4.0.8: Added completion action buttons.

        Args:
            websocket: WebSocket connection
            session: Current session
            presentation_url: Final presentation URL
        """
        # Count slides
        slide_count = len(session.strawman.get('slides', [])) if session.strawman else 0
        topic = session.topic or session.initial_request or 'your presentation'

        # Send presentation URL message
        url_msg = create_presentation_url(
            session_id=session.id,
            url=presentation_url,
            presentation_id=session.presentation_id or '',
            slide_count=slide_count,
            message=f"Your presentation '{topic}' with {slide_count} slides is ready!"
        )
        await websocket.send_json(url_msg.model_dump(mode='json'))

        # Send chat message
        await self._send_chat(
            websocket, session,
            f"🎉 Your presentation is ready!\n\n"
            f"**{topic}** - {slide_count} slides\n\n"
            f"[View Presentation]({presentation_url})"
        )

        # v4.0.8: Add completion action buttons
        action_msg = create_action_request(
            session_id=session.id,
            prompt_text="What would you like to do next?",
            actions=[
                {
                    "label": "Done, looks great!",
                    "value": "complete_presentation",
                    "primary": True,
                    "requires_input": False
                },
                {
                    "label": "Make adjustments",
                    "value": "request_adjustments",
                    "primary": False,
                    "requires_input": True
                }
            ]
        )
        await websocket.send_json(action_msg.model_dump(mode='json'))


# Compatibility alias
WebSocketHandler = WebSocketHandlerV4
