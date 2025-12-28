"""
WebSocket Handler for Director Agent v4.0

Uses AI-driven Decision Engine instead of rigid state machine.
Preserves connection management and message protocol from v3.4.
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
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

# v4.2: Stage 5 - Strawman Refinement
from src.core.strawman_refiner import StrawmanRefiner
from src.core.strawman_differ import StrawmanDiffer
from src.models.refinement import MergeStrategy

# v4.2: Stage 6 - Layout-Aligned Content Generation
from src.utils.layout_payload_assembler import LayoutPayloadAssembler, AssemblyContext
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
from config.settings import get_settings

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

        # v4.2: Initialize Strawman Refiner and Differ for Stage 5
        if self.settings.STRAWMAN_REFINEMENT_ENABLED:
            from src.core.layout_analyzer import LayoutSeriesMode
            series_mode = LayoutSeriesMode(self.settings.LAYOUT_SERIES_MODE)
            self.strawman_refiner = StrawmanRefiner(
                model_name=self.settings.GCP_MODEL_REFINE_STRAWMAN,
                project_id=self.settings.GCP_PROJECT_ID,
                location=self.settings.GCP_LOCATION,
                series_mode=series_mode
            )
            self.strawman_differ = StrawmanDiffer()
            logger.info(f"Strawman Refiner initialized with model: {self.settings.GCP_MODEL_REFINE_STRAWMAN}")
        else:
            self.strawman_refiner = None
            self.strawman_differ = None

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
        # v4.0.31: Use print() for Railway visibility
        print(f"[SESSION] Connected: session={session_id}, user={user_id}")

        # Get or create session
        session = await self.session_manager.get_or_create(session_id, user_id)
        # v4.0.31: Log session state
        print(f"[SESSION]   has_topic={session.has_topic}, has_strawman={session.has_strawman}, has_content={session.has_content}")

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

        elif message_type == 'set_branding':
            # v4.0: Handle branding configuration (logo, footer)
            await self._handle_set_branding(websocket, session, data)
            return

        else:
            logger.warning(f"Unknown message type: {message_type}")
            return

        # v3.4 compatibility: Validate non-empty input
        if not user_message or not user_message.strip():
            logger.warning(f"Received empty/whitespace user input, ignoring")
            return

        # v4.0.31: Use print() for Railway visibility
        msg_preview = user_message[:80] + '...' if len(user_message) > 80 else user_message
        print(f"[MSG] Received: '{msg_preview}' type={message_type}")

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
            # v4.0.31: Use print() for Railway visibility
            print(f"[DECISION] Action={decision.action_type}, confidence={decision.confidence:.2f}")
            reasoning_preview = decision.reasoning[:100] if decision.reasoning else 'None'
            print(f"[DECISION]   Reasoning: {reasoning_preview}...")

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

    async def _handle_set_branding(self, websocket: WebSocket, session: SessionV4, data: Dict[str, Any]):
        """
        Handle set_branding message to configure logo/footer for session.

        v4.0: Enables logo rendering by setting session branding before presentation creation.

        Expected payload:
        {
            "type": "set_branding",
            "payload": {
                "logo": {
                    "url": "https://example.com/logo.png",
                    "position": "top_right",  // optional
                    "width": 120  // optional
                }
            }
        }
        """
        try:
            from src.models.presentation_config import PresentationBranding, LogoConfig

            payload = data.get('payload', data)
            logo_config = None

            if 'logo' in payload:
                logo_data = payload['logo']
                logo_config = LogoConfig(
                    url=logo_data.get('url'),
                    position=logo_data.get('position', 'top_right'),
                    width=logo_data.get('width', 120)
                )

            branding = PresentationBranding(logo=logo_config)
            session.set_branding(branding)

            await websocket.send_json({
                "type": "branding_set",
                "success": True,
                "logo_url": logo_config.url if logo_config else None
            })
            logger.info(f"[Branding] Set logo URL: {logo_config.url if logo_config else 'None'}")

        except Exception as e:
            logger.error(f"[Branding] Error setting branding: {e}")
            await websocket.send_json({
                "type": "branding_set",
                "success": False,
                "error": str(e)
            })

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
        v4.5.10: Fixed summary to use actual topic/audience instead of "Your presentation".
        """
        plan_data = decision.plan_data or {}

        # v4.5.10: Build summary from session context if not in plan_data
        summary = plan_data.get('summary')
        if not summary:
            topic = session.topic or session.initial_request or 'your topic'
            audience = session.audience or 'general audience'
            purpose = session.purpose or 'inform'
            summary = f"A presentation about '{topic}' for {audience}, designed to {purpose}."

        message = decision.response_text or f"""Here's my proposed plan for your presentation:

**Summary:** {summary}

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

        # v4.5: Generate strawman with explicit slide count if user specified
        strawman = await self.strawman_generator.generate(
            topic=topic,
            audience=session.audience or "general",
            duration=session.duration or 15,
            purpose=session.purpose or "inform",
            requested_slide_count=session.requested_slide_count
        )

        # v4.5: Build ContentContext at strawman stage (THEME_SYSTEM_DESIGN.md v2.3)
        # Use presets if available (from Smart Context Extraction), otherwise raw values
        from src.models.content_context import build_content_context
        content_context = build_content_context(
            audience=session.audience_preset or session.audience,
            purpose=session.purpose_preset or session.purpose,
            duration=session.duration,
            tone=session.tone
        )
        session.content_context = content_context.to_text_service_format()
        logger.info(f"v4.5: Built ContentContext for session: audience={session.audience_preset or session.audience}, purpose={session.purpose_preset or session.purpose}")

        # Save strawman
        strawman_dict = strawman.dict()
        await self.session_manager.save_strawman(
            session.id, session.user_id, strawman_dict
        )

        # v4.0.31: Detailed strawman logging
        slides = strawman_dict.get('slides', [])
        hero_count = sum(1 for s in slides if s.get('is_hero') or s.get('hero_type'))
        content_count = len(slides) - hero_count
        print(f"[STRAWMAN] Generated: '{topic}' with {len(slides)} slides")
        print(f"[STRAWMAN]   Hero: {hero_count}, Content: {content_count}")
        for i, slide in enumerate(slides):
            slide_type = slide.get('hero_type') or ('hero' if slide.get('is_hero') else 'content')
            variant = slide.get('variant_id', 'auto')
            title_preview = slide.get('title', '')[:40]
            print(f"[STRAWMAN]   Slide {i+1}: {slide_type} ({variant}) - '{title_preview}'")

        # v4.0.5: Create preview presentation with deck-builder
        preview_url = None
        preview_presentation_id = None
        try:
            # v4.0.31: Use print() for Railway visibility
            print(f"[DECK] Creating preview presentation...")

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

            # v4.0.31: Use print() for Railway visibility
            print(f"[DECK-OK] Preview created: id={preview_presentation_id}, url={preview_url}")

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
        """
        Handle REFINE_STRAWMAN action - modify existing outline.

        v4.2: Full AI-driven refinement implementation for Stage 5.
        Uses StrawmanRefiner to parse feedback and modify specific slides.
        Re-runs LayoutAnalyzer on modified slides for proper service routing.
        """
        await self._send_status(websocket, session, "Refining presentation outline...")

        # Get refinement feedback from decision
        feedback = decision.response_text or ""

        if not feedback.strip():
            await self._send_chat(
                websocket, session,
                "I didn't catch any specific changes. What would you like me to modify?"
            )
            return

        # Check if refinement is enabled
        if not self.strawman_refiner:
            await self._send_chat(
                websocket, session,
                "I've noted your feedback. Let me update the outline accordingly."
            )
            logger.warning("Strawman refinement disabled - using stub response")
            return

        # Check if we have a strawman to refine
        if not session.strawman:
            await self._send_chat(
                websocket, session,
                "I don't have an outline to refine yet. Let me create one first."
            )
            return

        try:
            # Build context for refinement
            context = {
                "audience": session.audience,
                "tone": session.tone,
                "purpose": session.purpose,
                "duration": session.duration
            }

            # Call AI-driven refiner
            logger.info(f"Refining strawman with feedback: '{feedback[:100]}...'")
            result = await self.strawman_refiner.refine_from_chat(
                current_strawman=session.strawman,
                user_feedback=feedback,
                context=context
            )

            if not result.success:
                await self._send_chat(
                    websocket, session,
                    f"I couldn't apply those changes: {result.error or result.reasoning}. "
                    "Could you be more specific about what you'd like to change?"
                )
                return

            # Save updated strawman to session
            await self.session_manager.save_strawman(
                session.id, session.user_id, result.updated_strawman
            )

            # Refresh session
            session = await self.session_manager.get_or_create(session.id, session.user_id)

            # Generate new preview with updated strawman
            preview_url, preview_id = await self._generate_preview(result.updated_strawman, session)

            # Update session with new preview
            if preview_url:
                await self.session_manager.update_progress(
                    session.id, session.user_id,
                    {
                        'presentation_url': preview_url,
                        'presentation_id': preview_id
                    }
                )

            # Send updated slide_update to frontend
            await self._send_slide_update(
                websocket, session,
                result.updated_strawman,
                preview_url=preview_url,
                preview_presentation_id=preview_id
            )

            # Summarize changes
            change_summary = self.strawman_refiner.summarize_changes(result.changes)
            await self._send_chat(
                websocket, session,
                f"I've updated the outline: {change_summary}\n\n"
                "Would you like to make more changes, or does this look good?"
            )

            # Re-send approval buttons
            action_msg = create_action_request(
                session_id=session.id,
                prompt_text="How does this look?",
                actions=[
                    {
                        "label": "Looks perfect!",
                        "value": "accept_strawman",
                        "primary": True,
                        "requires_input": False
                    },
                    {
                        "label": "More changes",
                        "value": "request_refinement",
                        "primary": False,
                        "requires_input": True
                    }
                ]
            )
            await websocket.send_json(action_msg.model_dump(mode='json'))

            logger.info(f"Refinement complete: {len(result.changes)} changes applied")

        except Exception as e:
            logger.error(f"Strawman refinement failed: {e}", exc_info=True)
            await self._send_chat(
                websocket, session,
                "I had trouble applying those changes. Could you try rephrasing what you'd like to modify?"
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

        # v4.0.27: Phase-aware topic updates
        # Allow clarifications BEFORE strawman generation, lock AFTER
        topic = get_value(extracted, 'topic')
        if topic:
            can_update_topic = (
                not session.topic or  # No topic yet
                not session.has_strawman  # Still in clarification phase
            )
            if can_update_topic:
                if session.topic and session.topic != topic:
                    logger.info(f"  → Topic clarified: '{session.topic}' → '{topic}'")
                updates['topic'] = topic
                updates['has_topic'] = True
                # Also set as initial_request if not set
                if not session.initial_request:
                    updates['initial_request'] = topic
                if not session.topic:
                    logger.info(f"  → Extracted topic: {topic}")
            else:
                logger.info(f"  → Topic locked (strawman exists): keeping '{session.topic}'")

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

        # v4.5: Extract Smart Context Extraction fields
        slide_count = get_value(extracted, 'slide_count')
        has_explicit_slide_count = get_value(extracted, 'has_explicit_slide_count')
        if slide_count and has_explicit_slide_count:
            if not session.requested_slide_count:
                try:
                    updates['requested_slide_count'] = int(slide_count)
                    logger.info(f"  → Extracted explicit slide count: {slide_count}")
                except (ValueError, TypeError):
                    pass

        # v4.5: Extract preset mappings
        audience_preset = get_value(extracted, 'audience_preset')
        if audience_preset and not session.audience_preset:
            updates['audience_preset'] = audience_preset
            logger.info(f"  → Extracted audience preset: {audience_preset}")

        purpose_preset = get_value(extracted, 'purpose_preset')
        if purpose_preset and not session.purpose_preset:
            updates['purpose_preset'] = purpose_preset
            logger.info(f"  → Extracted purpose preset: {purpose_preset}")

        time_preset = get_value(extracted, 'time_preset')
        if time_preset and not session.time_preset:
            updates['time_preset'] = time_preset
            logger.info(f"  → Extracted time preset: {time_preset}")

        # v4.5: Build ContentContext from presets if we have enough info
        # This bridges the extracted presets to the Theme System's content_context
        if not session.content_context:
            # Use extracted presets or derive from raw values
            final_audience = audience_preset or updates.get('audience_preset') or session.audience_preset
            final_purpose = purpose_preset or updates.get('purpose_preset') or session.purpose_preset
            final_duration = updates.get('duration') or session.duration or 20

            # Only build if we have at least audience or purpose preset
            if final_audience or final_purpose:
                try:
                    from src.models.content_context import build_content_context
                    content_context = build_content_context(
                        audience=final_audience or "professional",
                        purpose=final_purpose or "inform",
                        duration=final_duration,
                        tone=updates.get('tone') or session.tone
                    )
                    updates['content_context'] = content_context.to_text_service_format()
                    logger.info(f"  → Built ContentContext from presets: audience={final_audience}, purpose={final_purpose}")
                except Exception as e:
                    logger.warning(f"  → Failed to build ContentContext: {e}")

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
                'subtitle': slide.get('subtitle'),  # v4.5.4: Include subtitle
                'narrative': narrative,
                'key_points': slide.get('topics', []),
                # v4.5.4: Include strawman metadata for preview display
                'variant_id': slide.get('variant_id'),
                'service': slide.get('service'),
                'purpose': slide.get('purpose'),
                'semantic_group': slide.get('semantic_group'),
                # Existing fields
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

    # ========== v4.2: Stage 5 - Diff on Generate ==========

    async def _sync_with_deck_builder(self, session: SessionV4) -> Tuple[Dict[str, Any], List[Any]]:
        """
        DIFF ON GENERATE: Sync with Deck-Builder before content generation.

        v4.2: Stage 5 - Fetch current state from Deck-Builder and detect any
        changes the user made via direct edits in the preview.

        Args:
            session: Current session with strawman and presentation_id

        Returns:
            Tuple of (merged_strawman, list_of_changes)
        """
        from typing import Tuple

        if not session.presentation_id:
            logger.debug("No presentation_id - skipping Deck-Builder sync")
            return session.strawman, []

        if not self.settings.DIFF_ON_GENERATE_ENABLED:
            logger.debug("Diff on generate disabled - using session strawman as-is")
            return session.strawman, []

        if not self.strawman_differ:
            logger.debug("StrawmanDiffer not initialized - using session strawman as-is")
            return session.strawman, []

        try:
            # Fetch current state from Deck-Builder
            logger.info(f"Fetching presentation state from Deck-Builder: {session.presentation_id}")
            db_state = await self.deck_builder_client.get_presentation_state(session.presentation_id)

            if not db_state:
                logger.warning(f"Could not fetch presentation state for {session.presentation_id}")
                return session.strawman, []

            # Compute diff
            diff = self.strawman_differ.compute_diff(session.strawman, db_state)

            if not diff.has_changes:
                logger.info("No changes detected in Deck-Builder - using session strawman")
                return session.strawman, []

            logger.info(
                f"Detected changes in Deck-Builder: "
                f"{len(diff.added_slides)} added, {len(diff.removed_slide_ids)} removed, "
                f"{len(diff.modified_slides)} modified"
            )

            # Merge changes into Director's strawman (Deck-Builder wins)
            merge_result = self.strawman_differ.merge_changes(
                session.strawman, diff, MergeStrategy.DECKBUILDER_WINS
            )

            if not merge_result.success:
                logger.error(f"Merge failed: {merge_result.conflicts}")
                return session.strawman, []

            # Re-analyze layout for slides with significant changes
            merged_strawman = merge_result.merged_strawman
            if diff.slides_needing_reanalysis and self.strawman_refiner:
                for slide_mod in diff.slides_needing_reanalysis:
                    idx = slide_mod.slide_number - 1
                    slides = merged_strawman.get("slides", [])
                    if 0 <= idx < len(slides):
                        slide = slides[idx]
                        result = self.strawman_refiner.layout_analyzer.analyze(
                            slide_type_hint=slide.get("slide_type_hint", "text"),
                            hero_type=slide.get("hero_type"),
                            topic_count=len(slide.get("topics", [])),
                            purpose=slide.get("purpose"),
                            title=slide.get("title"),
                            topics=slide.get("topics")
                        )
                        slide["layout"] = result.layout
                        slide["service"] = result.service
                        logger.debug(
                            f"Re-analyzed slide {slide_mod.slide_number}: "
                            f"layout={result.layout}, service={result.service}"
                        )

            # Save merged strawman back to session
            await self.session_manager.save_strawman(
                session.id, session.user_id, merged_strawman
            )

            return merged_strawman, diff.modified_slides

        except Exception as e:
            logger.error(f"Deck-Builder sync failed: {e}", exc_info=True)
            return session.strawman, []

    async def _handle_content_generation(self, websocket: WebSocket, session: SessionV4):
        """
        Handle content generation when user explicitly approves.

        v4.0.6: Bypasses Decision Engine and calls text-service directly.
        Simplified pipeline (text-service only for content slides).

        v4.2: Stage 5 - Sync with Deck-Builder before generation (diff on generate).
        Detects any changes the user made in the preview and incorporates them.

        Args:
            websocket: WebSocket connection
            session: Current session
        """
        await self._send_status(websocket, session, "Generating presentation content...")

        try:
            # 0. Get initial strawman
            strawman = session.strawman
            if not strawman:
                await self._send_chat(websocket, session, "No presentation outline found. Let me create one first.")
                return

            # 1. v4.2: DIFF ON GENERATE - Sync with Deck-Builder first
            # This detects any changes the user made via direct edits in the preview
            await self._send_status(websocket, session, "Syncing with preview changes...")
            strawman, modified_slides = await self._sync_with_deck_builder(session)

            if modified_slides:
                logger.info(f"Incorporated {len(modified_slides)} user edits from Deck-Builder preview")

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

    def _select_variant_for_slide(
        self,
        slide: Dict[str, Any],
        layout_info: Optional[Any] = None
    ) -> str:
        """
        Select appropriate text-service variant based on slide content.

        v4.0.7: Simple count-based selection using valid variants from registry.
        This fixes HTTP 422 errors caused by invalid variant_id.

        v4.0.24: Added layout_info parameter for layout-aware variant selection.
        When Layout Service coordination is enabled, variants are constrained
        to those supported by the layout.

        Args:
            slide: Slide dict with 'topics' list
            layout_info: Optional LayoutTemplate from Layout Service

        Returns:
            Valid variant_id for text-service v1.2
        """
        topics = slide.get('topics', [])
        topic_count = len(topics)

        # v4.0.24: Layout-aware variant selection
        if layout_info and hasattr(layout_info, 'supported_variants') and layout_info.supported_variants:
            # Find best matching variant from layout's supported list
            for variant in layout_info.supported_variants:
                if self._variant_matches_topic_count(variant, topic_count):
                    return variant
            # If no topic-count match, return first supported variant
            return layout_info.supported_variants[0]

        # Fallback: topic count-based selection
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

    def _variant_matches_topic_count(self, variant: str, topic_count: int) -> bool:
        """
        Check if a variant is appropriate for the given topic count.

        v4.0.24: Helper for layout-aware variant selection.

        Args:
            variant: Variant ID to check
            topic_count: Number of topics in the slide

        Returns:
            True if variant is suitable for the topic count
        """
        # Map variants to their expected topic counts
        variant_topic_map = {
            'comparison_2col': 2,
            'sequential_2col': 2,
            'sequential_3col': 3,
            'comparison_3col': 3,
            'sequential_4col': 4,
            'comparison_4col': 4,
            'grid_2x2_centered': 4,
            'sequential_5col': 5,
            'grid_2x3': 6,
            'grid_3x2': 6,
            'matrix_2x2': 4,
            'matrix_2x3': 6,
            'metrics_3col': 3,
            'metrics_4col': 4,
        }

        expected = variant_topic_map.get(variant)
        # If variant not in map, it's flexible - allow it
        if expected is None:
            return True
        # Allow some flexibility (exact match or one off)
        return abs(expected - topic_count) <= 1

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

    async def _get_layout_info(self, layout_id: str) -> Optional[Any]:
        """
        Fetch layout info from Layout Service.

        v4.0.24: Helper for layout-aware variant selection.

        Args:
            layout_id: Layout ID (e.g., 'L25', 'L29')

        Returns:
            LayoutTemplate from Layout Service, or None if unavailable
        """
        try:
            from src.clients.layout_service_client import LayoutServiceClient
            client = LayoutServiceClient()

            # Check service availability first
            if not await client.health_check():
                logger.debug("Layout Service unavailable for layout info fetch")
                return None

            layout = await client.get_layout(layout_id)
            logger.debug(f"Fetched layout info for {layout_id}")
            return layout

        except Exception as e:
            logger.warning(f"Failed to fetch layout info for {layout_id}: {e}")
            return None

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

        # v4.0.31: Removed noisy [HERO-DIAG] for non-hero slides - only log relevant info

        try:
            if is_hero or hero_type:
                # v4.0.24: Hero slides - Call Text Service hero endpoints for rich content with images
                # v4.0.31: Use [SLIDE] prefix for consistency
                # v4.3: Use unified /v1.2/slides/* endpoints when enabled
                print(f"[SLIDE] Slide {idx+1}/{total_slides}: type=hero, hero_type={hero_type or 'hero'}")

                presentation_title = session.topic or session.initial_request or 'Untitled Presentation'
                settings = get_settings()

                # v4.3: Use unified slides API for spec-compliant responses
                if settings.USE_UNIFIED_SLIDES_API:
                    narrative = slide.get('notes') or slide.get('narrative') or ''
                    topics = slide.get('topics') or []
                    context = {
                        "tone": session.tone or "professional",
                        "audience": session.audience or "general"
                    }

                    # v4.5: Get theme config and content context for Text Service
                    from src.models.theme_config import get_theme_config
                    theme_config = get_theme_config(session.theme_id or settings.DEFAULT_THEME_ID)
                    theme_dict = theme_config.to_text_service_format()
                    content_context = session.content_context
                    styling_mode = settings.THEME_STYLING_MODE

                    # v4.6: Get visual_style and image_model from ImageStyleAgreement
                    image_style_agreement = session.get_image_style_agreement()
                    if image_style_agreement:
                        hero_visual_style = image_style_agreement.to_visual_style()
                        # Hero slides get is_hero=True for quality tier selection
                        hero_image_model = image_style_agreement.get_model_for_slide(is_hero=True)
                        context["image_model"] = hero_image_model
                        # v4.7: Extract global_brand for simplified image prompting
                        hero_global_brand = image_style_agreement.to_global_brand()
                        print(f"[HERO-STYLE] Using image style: visual={hero_visual_style}, model={hero_image_model}")
                        print(f"[HERO-STYLE]   global_brand: {list(hero_global_brand.keys()) if hero_global_brand else 'None'}")
                    else:
                        hero_visual_style = "professional"
                        hero_global_brand = None
                        print(f"[HERO-STYLE] No ImageStyleAgreement, defaulting to professional")

                    try:
                        if hero_type == 'title_slide' or not hero_type:
                            # H1-generated: Title slide with AI image
                            print(f"[SLIDE] Using unified API: /v1.2/slides/H1-generated")
                            result = await self.text_service_client.generate_h1_generated(
                                slide_number=idx + 1,
                                narrative=narrative,
                                topics=topics,
                                presentation_title=presentation_title,
                                subtitle=slide.get('subtitle'),
                                visual_style=hero_visual_style,
                                context=context,
                                theme_config=theme_dict,
                                content_context=content_context,
                                styling_mode=styling_mode,
                                # v4.7: Global brand for simplified image prompting
                                global_brand=hero_global_brand
                            )
                            layout = 'H1-generated'
                        elif hero_type == 'section_divider':
                            # H2-section: Section divider
                            print(f"[SLIDE] Using unified API: /v1.2/slides/H2-section")
                            result = await self.text_service_client.generate_h2_section(
                                slide_number=idx + 1,
                                narrative=narrative,
                                section_number=slide.get('section_number'),
                                section_title=slide.get('title'),
                                topics=topics,
                                visual_style=hero_visual_style,
                                theme_config=theme_dict,
                                content_context=content_context,
                                styling_mode=styling_mode,
                                # v4.7: Global brand for simplified image prompting
                                global_brand=hero_global_brand
                            )
                            layout = 'H2-section'
                        elif hero_type == 'closing_slide':
                            # H3-closing: Closing slide
                            print(f"[SLIDE] Using unified API: /v1.2/slides/H3-closing")
                            result = await self.text_service_client.generate_h3_closing(
                                slide_number=idx + 1,
                                narrative=narrative,
                                closing_message=slide.get('title', 'Thank You'),
                                visual_style=hero_visual_style,
                                theme_config=theme_dict,
                                content_context=content_context,
                                styling_mode=styling_mode,
                                # v4.7: Global brand for simplified image prompting
                                global_brand=hero_global_brand
                            )
                            layout = 'H3-closing'
                        else:
                            # Fallback to H1-generated
                            print(f"[SLIDE] Using unified API: /v1.2/slides/H1-generated (fallback)")
                            result = await self.text_service_client.generate_h1_generated(
                                slide_number=idx + 1,
                                narrative=narrative,
                                topics=topics,
                                presentation_title=presentation_title,
                                visual_style=hero_visual_style,
                                context=context,
                                theme_config=theme_dict,
                                content_context=content_context,
                                styling_mode=styling_mode,
                                # v4.7: Global brand for simplified image prompting
                                global_brand=hero_global_brand
                            )
                            layout = 'H1-generated'

                        # v4.3: Response is spec-compliant with all fields
                        print(f"[HERO-OK] Slide {idx+1} generated via unified slides API ({layout})")

                        return {
                            'idx': idx,
                            'slide_id': slide_id,
                            'layout': layout,
                            'content': result.get('hero_content', ''),
                            'slide_title': result.get('slide_title', ''),
                            'subtitle': result.get('subtitle', ''),
                            'section_number': result.get('section_number', ''),
                            'contact_info': result.get('contact_info', ''),
                            'author_info': result.get('author_info', ''),
                            'background_color': result.get('background_color'),
                            'background_image': result.get('background_image'),
                            'is_hero': True,
                            'hero_type': hero_type
                        }

                    except Exception as e:
                        print(f"[HERO-ERROR] Unified API failed, falling back to legacy: {str(e)[:100]}")
                        # Fall through to legacy behavior

                # Legacy behavior (USE_UNIFIED_SLIDES_API=False or fallback)
                # v4.0.25: Map hero_type to endpoint (use -with-image for background images)
                endpoint_map = {
                    'title_slide': '/v1.2/hero/title-with-image',
                    'section_divider': '/v1.2/hero/section-with-image',
                    'closing_slide': '/v1.2/hero/closing-with-image'
                }
                endpoint = endpoint_map.get(hero_type, '/v1.2/hero/title-with-image')

                # v4.6: Get visual_style and image_model from ImageStyleAgreement for legacy path
                legacy_image_style = session.get_image_style_agreement()
                if legacy_image_style:
                    legacy_visual_style = legacy_image_style.to_visual_style()
                    legacy_image_model = legacy_image_style.get_model_for_slide(is_hero=True)
                else:
                    legacy_visual_style = "professional"
                    legacy_image_model = None

                # Build hero request payload
                hero_context = {
                    "presentation_title": presentation_title,
                    "total_slides": total_slides,
                    "tone": session.tone or "professional",
                    "audience": session.audience or "general"
                }
                if legacy_image_model:
                    hero_context["image_model"] = legacy_image_model

                hero_payload = {
                    "slide_number": idx + 1,
                    "slide_type": hero_type or "title_slide",
                    "narrative": slide.get('notes') or slide.get('narrative') or '',
                    "topics": slide.get('topics') or [],
                    "visual_style": legacy_visual_style,  # v4.6: From ImageStyleAgreement
                    "context": hero_context
                }

                try:
                    result = await self.text_service_client.call_hero_endpoint(endpoint, hero_payload)
                    # v4.0.26: Text Service returns 'content' field, not 'html_content'
                    html_content = result.get('content') or result.get('html', '')

                    if not html_content:
                        raise ValueError("Empty HTML from hero endpoint")

                    print(f"[HERO-OK] Slide {idx+1} generated via Text Service ({endpoint})")

                except Exception as e:
                    # v4.0.29: Use print() for Railway visibility (logger not captured)
                    error_type = type(e).__name__
                    error_msg = str(e)
                    stack_trace = traceback.format_exc()

                    print(f"[HERO-ERROR] Slide {idx+1} FAILED:")
                    print(f"[HERO-ERROR]   Type: {error_type}")
                    print(f"[HERO-ERROR]   Message: {error_msg}")
                    print(f"[HERO-ERROR]   Endpoint: {endpoint}")
                    print(f"[HERO-ERROR]   Payload keys: {list(hero_payload.keys())}")
                    print(f"[HERO-ERROR]   Stack trace: {stack_trace[:500]}")

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
                # v4.0.31: Use print() for Railway visibility
                # v4.3: Use unified /v1.2/slides/C1-text for combined generation (1 LLM call)
                print(f"[SLIDE] Slide {idx+1}/{total_slides}: type=content")

                # v4.0: Check for I-series (image+text) generation
                # v4.8: Unified Variant System - detect I-series from variant_id suffix
                settings = get_settings()
                if settings.USE_ISERIES_GENERATION:
                    from src.utils.variant_catalog import is_iseries_variant, get_iseries_layout
                    variant_id = slide.get('variant_id')
                    if variant_id and is_iseries_variant(variant_id):
                        layout_type = get_iseries_layout(variant_id)  # Extract I1/I2/I3/I4
                        print(f"[SLIDE] Slide {idx+1}: I-series detected from variant_id '{variant_id}' -> {layout_type}")
                        return await self._generate_iseries_slide(idx, slide, session, total_slides)

                # Get settings for configuration checks
                settings = get_settings()

                # v4.3: Use unified slides API for combined generation (67% LLM savings!)
                if settings.USE_UNIFIED_SLIDES_API:
                    strawman_variant = slide.get('variant_id', 'bullets')

                    # v4.6.0: Validate variant is Gold Standard C1 (never use null or non-C1 variants)
                    from src.utils.variant_catalog import GOLD_STANDARD_C1_VARIANTS
                    if not strawman_variant or strawman_variant not in GOLD_STANDARD_C1_VARIANTS:
                        logger.warning(
                            f"Non-Gold-Standard variant '{strawman_variant}' for slide {idx+1}, "
                            f"using fallback: grid_2x2_centered_c1"
                        )
                        strawman_variant = "grid_2x2_centered_c1"

                    topics = slide.get('topics', [])
                    narrative = slide.get('notes') or slide.get('narrative') or ''

                    # Handle empty topics
                    if not topics:
                        slide_title_text = slide.get('title', 'Slide')
                        slide_notes = slide.get('notes', '')
                        if slide_notes:
                            topics = [f"Key point: {slide_notes[:80]}"]
                        else:
                            topics = [f"Key aspects of {slide_title_text}"]

                    context = {
                        "tone": session.tone or "professional",
                        "audience": session.audience or "general"
                    }

                    # v4.5: Get theme config and content context for Text Service
                    from src.models.theme_config import get_theme_config
                    theme_config = get_theme_config(session.theme_id or settings.DEFAULT_THEME_ID)

                    try:
                        print(f"[SLIDE] Using unified API: /v1.2/slides/C1-text (1 LLM call)")

                        result = await self.text_service_client.generate_c1_text(
                            slide_number=idx + 1,
                            narrative=narrative,
                            variant_id=strawman_variant,
                            slide_title=slide.get('title'),
                            subtitle=slide.get('subtitle'),
                            topics=topics,
                            content_style="bullets",
                            context=context,
                            # v4.5: Theme system params (ignored by v1.2.2, used by v1.3.0)
                            theme_config=theme_config.to_text_service_format(),
                            content_context=session.content_context,
                            styling_mode=settings.THEME_STYLING_MODE
                        )

                        # v4.3: Response includes slide_title, subtitle, body, background_color
                        print(f"[SLIDE-OK] Slide {idx+1} generated via unified API (C1-text)")

                        return {
                            'idx': idx,
                            'slide_id': slide_id,
                            'layout': 'C1-text',
                            'content': result.get('body', '') or result.get('rich_content', ''),
                            'slide_title': result.get('slide_title', ''),
                            'subtitle': result.get('subtitle', ''),
                            'body': result.get('body', ''),
                            'rich_content': result.get('rich_content', ''),
                            'background_color': result.get('background_color'),
                            'is_hero': False,
                            'title': slide.get('title', '')
                        }

                    except Exception as e:
                        print(f"[SLIDE-ERROR] Unified API failed, falling back to legacy: {str(e)[:100]}")
                        # Fall through to legacy behavior

                # Legacy behavior (USE_UNIFIED_SLIDES_API=False or fallback)
                # v4.0.24: Fetch layout info for layout-aware variant selection
                layout_info = None
                if settings.USE_LAYOUT_SERVICE_COORDINATION:
                    layout_info = await self._get_layout_info(slide.get('layout', 'L25'))

                # v4.0.23: Prefer variant from strawman, fallback to selector
                # v4.0.24: Pass layout_info for layout-aware fallback selection
                # v4.6.0: Validate variant is Gold Standard C1
                strawman_variant = slide.get('variant_id')
                variant_id = strawman_variant or self._select_variant_for_slide(slide, layout_info)

                # v4.6.0: Ensure variant is Gold Standard C1 (never use null or non-C1 variants)
                from src.utils.variant_catalog import GOLD_STANDARD_C1_VARIANTS
                if not variant_id or variant_id not in GOLD_STANDARD_C1_VARIANTS:
                    logger.warning(
                        f"Non-Gold-Standard variant '{variant_id}' in legacy path for slide {idx+1}, "
                        f"using fallback: grid_2x2_centered_c1"
                    )
                    variant_id = "grid_2x2_centered_c1"

                variant_source = 'strawman' if strawman_variant else ('layout-aware' if layout_info else 'fallback')
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
                    print(f"[CONTENT]   WARNING: Empty topics, generated fallback")

                # v4.0.31: Use print() for Railway visibility
                title_preview = slide.get('title', '')[:40]
                print(f"[CONTENT] variant={variant_id} ({variant_source}), topics={len(topics)}, title='{title_preview}'")

                # v4.7: Use strawman's rich context fields for better content generation
                purpose = slide.get('purpose', '')  # Story context from strawman
                generation_instructions = slide.get('generation_instructions', '')  # Generation guidance
                notes = slide.get('notes', '')  # Speaker notes
                slide_title = slide.get('title', 'this topic')

                # Build slide_purpose: purpose > notes > fallback
                if purpose:
                    slide_purpose = purpose
                elif notes:
                    slide_purpose = notes
                else:
                    slide_purpose = f"Present key points about {slide_title}"

                # Build key_message: generation_instructions > topics > fallback
                if generation_instructions:
                    key_message = generation_instructions
                elif topics:
                    key_message = ' | '.join(topics[:3])
                else:
                    key_message = slide.get('title', '')

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

                # v4.0.24: Add content zone dimensions for optimized text generation
                if layout_info:
                    request['content_zone'] = {
                        'width': getattr(layout_info, 'content_zone_width', 1800),
                        'height': getattr(layout_info, 'content_zone_height', 720)
                    }
                    # Add slot constraints for text slots
                    if hasattr(layout_info, 'slots') and layout_info.slots:
                        text_slots = [s for s in layout_info.slots if getattr(s, 'type', '') == 'text']
                        if text_slots:
                            request['text_constraints'] = [
                                {
                                    'slot_id': getattr(slot, 'id', f'slot_{i}'),
                                    'max_width': getattr(slot, 'width', 600),
                                    'max_height': getattr(slot, 'height', 400)
                                }
                                for i, slot in enumerate(text_slots)
                            ]
                    print(f"[CONTENT]   Layout zone: {request['content_zone']['width']}x{request['content_zone']['height']}")

                # Validate request
                is_valid, error_msg = self._validate_text_request(request)
                if not is_valid:
                    raise ValueError(f"Request validation failed: {error_msg}")

                # v4.0.31: Use print() for Railway visibility
                print(f"[CONTENT] Calling Text Service /v1.2/generate for slide {idx+1}")

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

                # v4.0.31: Use print() for Railway visibility
                print(f"[SLIDE-OK] Slide {idx+1} content generated successfully")

                # v4.7: Use C1-text layout (more content space than L25)
                content_html = result.content if hasattr(result, 'content') else str(result)
                return {
                    'idx': idx,
                    'slide_id': slide_id,
                    'layout': 'C1-text',  # v4.7: C1-text has 840px content vs L25's 720px
                    'content': content_html,
                    'slide_title': slide.get('title', ''),  # For C1-text layout
                    'subtitle': slide.get('subtitle', ''),  # v4.7: Pass through from strawman
                    'body': content_html,  # For C1-text content area
                    'is_hero': False,
                    'title': slide.get('title', '')  # Keep for backward compat
                }

        except Exception as e:
            full_traceback = traceback.format_exc()
            # v4.0.31: Use print() for Railway visibility
            error_msg = str(e)[:150]
            print(f"[SLIDE-ERROR] Slide {idx+1} FAILED: {type(e).__name__}: {error_msg}")
            print(f"[SLIDE-ERROR]   Using fallback HTML")

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
            # v4.7: Use C1-text layout (more content space than L25)
            return {
                'idx': idx,
                'slide_id': slide_id,
                'layout': 'C1-text',  # v4.7: C1-text has 840px content vs L25's 720px
                'content': fallback_html,
                'slide_title': slide.get('title', ''),  # For C1-text layout
                'subtitle': slide.get('subtitle', ''),  # v4.7: Pass through from strawman
                'body': fallback_html,  # For C1-text content area
                'is_hero': False,
                'title': slide.get('title', ''),  # Keep for backward compat
                'fallback': True
            }

    async def _generate_iseries_slide(
        self,
        idx: int,
        slide: Dict[str, Any],
        session: SessionV4,
        total_slides: int
    ) -> Dict[str, Any]:
        """
        Generate I-series slide (image + text combined layout).

        v4.0: Called when USE_ISERIES_GENERATION is enabled and slide has
        needs_image=True and suggested_iseries set.
        v4.8: Unified Variant System - uses variant_id suffix to determine
        layout_type (I1/I2/I3/I4) and passes content_variant to Text Service.

        I-series layouts:
        - I1: Wide image left (660x1080), content right (1200x840)
        - I2: Wide image right (660x1080), content left (1140x840)
        - I3: Narrow image left (360x1080), content right (1500x840)
        - I4: Narrow image right (360x1080), content left (1440x840)

        Args:
            idx: Slide index (0-based)
            slide: Slide dict from strawman
            session: Current session
            total_slides: Total number of slides

        Returns:
            Dict with slide content and 'idx' for ordering
        """
        import traceback
        from src.utils.variant_catalog import (
            get_iseries_layout,
            get_content_variant_base,
            is_iseries_variant,
            GOLD_STANDARD_I_SERIES_VARIANTS
        )

        slide_id = slide.get('slide_id', f'slide_{idx+1}')

        # v4.8: Unified Variant System - extract layout_type and content_variant from variant_id
        variant_id = slide.get('variant_id')

        if variant_id and is_iseries_variant(variant_id):
            layout_type = get_iseries_layout(variant_id)  # e.g., "I1" from "sequential_3col_i1"
            content_variant = get_content_variant_base(variant_id)  # e.g., "sequential_3col"

            # Validate against Gold Standard I-series variants
            if variant_id not in GOLD_STANDARD_I_SERIES_VARIANTS:
                logger.warning(
                    f"Non-Gold-Standard I-series variant '{variant_id}' for slide {idx+1}, "
                    f"using fallback: single_column_3section_i1"
                )
                variant_id = "single_column_3section_i1"
                layout_type = "I1"
                content_variant = "single_column_3section"

            print(f"[ISERIES] Unified variant: {variant_id} -> layout={layout_type}, content_variant={content_variant}")
        else:
            # Fallback: Legacy mode using suggested_iseries (backward compatibility)
            layout_type = slide.get('suggested_iseries', 'I1')
            content_variant = None  # Text Service uses default
            print(f"[ISERIES] Legacy mode: layout_type={layout_type}, no content_variant")

        # Get settings for I-series defaults
        settings = get_settings()
        content_style = settings.ISERIES_DEFAULT_CONTENT_STYLE

        # v4.6: Get visual_style from ImageStyleAgreement if available
        image_style_agreement = session.get_image_style_agreement()
        if image_style_agreement:
            visual_style = image_style_agreement.to_visual_style()
            image_model = image_style_agreement.get_model_for_slide(is_hero=False)
            # v4.7: Extract global_brand for simplified image prompting
            global_brand = image_style_agreement.to_global_brand()
            print(f"[ISERIES] Using ImageStyleAgreement: visual_style={visual_style}, model={image_model}")
            print(f"[ISERIES]   global_brand: {list(global_brand.keys()) if global_brand else 'None'}")
        else:
            visual_style = settings.ISERIES_DEFAULT_VISUAL_STYLE
            image_model = None
            global_brand = None
            print(f"[ISERIES] No ImageStyleAgreement, using default: visual_style={visual_style}")

        try:
            # Build I-series request
            title = slide.get('title', 'Untitled')
            narrative = slide.get('notes') or slide.get('narrative') or f"Key points about {title}"
            topics = slide.get('topics', [])

            # Context for I-series generation
            context = {
                "presentation_title": session.topic or session.initial_request or 'Presentation',
                "total_slides": total_slides,
                "current_slide": idx + 1,
                "tone": session.tone or "professional",
                "audience": session.audience or "general"
            }

            # v4.6: Add image_model to context if available
            if image_model:
                context["image_model"] = image_model
            if image_style_agreement:
                context["image_style_agreement"] = image_style_agreement.to_context_dict()

            # v4.5: Get theme config and content context for Text Service
            from src.models.theme_config import get_theme_config
            theme_config = get_theme_config(session.theme_id or settings.DEFAULT_THEME_ID)
            theme_dict = theme_config.to_text_service_format()

            print(f"[ISERIES] Generating {layout_type} for slide {idx+1}: '{title[:40]}...'")
            print(f"[ISERIES]   visual_style={visual_style}, topics={len(topics)}")

            # Call Text Service I-series endpoint
            # v4.8: Pass content_variant for Gold Standard template selection
            result = await self.text_service_client.generate_iseries(
                layout_type=layout_type,
                slide_number=idx + 1,
                title=title,
                narrative=narrative,
                topics=topics,
                visual_style=visual_style,
                content_style=content_style,
                context=context,
                max_bullets=5,
                # v4.5: Theme system params
                theme_config=theme_dict,
                content_context=session.content_context,
                styling_mode=settings.THEME_STYLING_MODE,
                # v4.7: Global brand for simplified image prompting
                global_brand=global_brand,
                # v4.8: Gold Standard content variant (Unified Variant System)
                content_variant=content_variant
            )

            # I-series returns combined HTML
            # The service may return 'content' or separate 'image_html' + 'content_html'
            if 'content' in result:
                html_content = result['content']
            else:
                # Combine image and content HTML
                image_html = result.get('image_html', '')
                content_html = result.get('content_html', '')
                title_html = result.get('title_html', f'<h2>{title}</h2>')

                # Assemble into container based on layout
                if layout_type in ('I1', 'I3'):
                    # Image on left
                    html_content = f'''
                    <div class="iseries-container iseries-{layout_type.lower()}" style="display: flex; width: 100%; height: 100%;">
                        <div class="iseries-image" style="flex-shrink: 0;">{image_html}</div>
                        <div class="iseries-content" style="flex: 1; padding: 20px;">
                            {title_html}
                            {content_html}
                        </div>
                    </div>
                    '''
                else:
                    # Image on right (I2, I4)
                    html_content = f'''
                    <div class="iseries-container iseries-{layout_type.lower()}" style="display: flex; width: 100%; height: 100%;">
                        <div class="iseries-content" style="flex: 1; padding: 20px;">
                            {title_html}
                            {content_html}
                        </div>
                        <div class="iseries-image" style="flex-shrink: 0;">{image_html}</div>
                    </div>
                    '''

            image_fallback = result.get('image_fallback', False)
            fallback_msg = " (gradient fallback)" if image_fallback else ""
            print(f"[ISERIES-OK] Slide {idx+1} generated{fallback_msg}")

            return {
                'idx': idx,
                'slide_id': slide_id,
                'layout': f'I{layout_type[1]}' if len(layout_type) > 1 else 'I1',
                'content': html_content,
                'is_hero': False,
                'is_iseries': True,
                'title': title,
                'image_fallback': image_fallback
            }

        except Exception as e:
            full_traceback = traceback.format_exc()
            error_msg = str(e)[:150]
            print(f"[ISERIES-ERROR] Slide {idx+1} FAILED: {type(e).__name__}: {error_msg}")
            print(f"[ISERIES-ERROR]   Falling back to standard content generation")

            # Capture error
            from src.utils.debug_capture import capture_text_service_request
            capture_text_service_request(
                session_id=session.id,
                slide_index=idx,
                request={'layout_type': layout_type, 'title': slide.get('title')},
                error=f"I-series failed: {str(e)}\n{full_traceback}"
            )

            # Fallback: generate as regular content slide
            # v4.8: Clear variant_id to fallback to C1 (unified approach)
            # Also clear legacy flags for backward compatibility
            slide_copy = slide.copy()
            slide_copy['variant_id'] = 'grid_2x2_centered_c1'  # Fallback to C1 variant
            slide_copy['needs_image'] = False  # Legacy flag (deprecated)
            slide_copy['suggested_iseries'] = None  # Legacy flag (deprecated)

            return await self._generate_single_slide(idx, slide_copy, session, total_slides)

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
        import time

        slides = strawman.get('slides', [])
        total_slides = len(slides)

        # v4.0.31: Use print() for Railway visibility with timing
        print(f"[TIMING] Starting PARALLEL generation for {total_slides} slides...")
        start_time = time.time()

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
                print(f"[SLIDE-ERROR] Unexpected task exception for slide {i+1}: {result}")
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

        # v4.0.31: Log summary with timing
        elapsed = time.time() - start_time
        fallback_count = sum(1 for s in enriched_slides if s.get('fallback'))
        success_count = total_slides - fallback_count
        print(f"[TIMING] Parallel generation complete: {elapsed:.1f}s for {total_slides} slides")
        print(f"[TIMING]   Success: {success_count}, Fallback: {fallback_count}")

        return enriched_slides

    async def _create_final_presentation(
        self,
        enriched_slides: List[Dict[str, Any]],
        session: SessionV4
    ) -> tuple:
        """
        Create final presentation with generated content.

        v4.0.6: Creates NEW presentation with enriched content (v3.4 approach).
        v4.2: Uses LayoutPayloadAssembler for layout-specific payloads
              aligned to SLIDE_GENERATION_INPUT_SPEC.md.
        v4.3: Supports unified slides API response format with slide_title,
              subtitle, body, rich_content fields directly from Text Service.

        Args:
            enriched_slides: List of slides with generated content
            session: Current session

        Returns:
            Tuple of (presentation_url, presentation_id)
        """
        # v4.2: Use LayoutPayloadAssembler for layout-specific payloads
        assembler = LayoutPayloadAssembler()
        slides_payload = []
        total_slides = len(enriched_slides)

        # Get branding if available
        branding = session.get_branding() if hasattr(session, 'get_branding') else None

        for idx, slide in enumerate(enriched_slides):
            layout = slide.get('layout', 'L25')
            is_hero = slide.get('is_hero', False) or layout in ['L29', 'H1-generated', 'H1-structured', 'H2-section', 'H3-closing']

            # Build context for assembly
            context = AssemblyContext(
                slide_number=idx + 1,
                total_slides=total_slides,
                presentation_title=session.topic or session.initial_request
            )

            # v4.3: Unified API returns 'slide_title' directly; legacy uses 'title'
            # Prefer slide_title (HTML formatted), fall back to title
            slide_title = slide.get('slide_title') or slide.get('title', '')
            subtitle = slide.get('subtitle', '')

            # Build content dict for assembler
            content_dict = {}

            if is_hero or layout in ['L29', 'H1-generated']:
                # Full-bleed hero - content is the complete HTML
                content_dict['hero_content'] = slide.get('content', '')
            elif layout == 'H1-structured':
                content_dict['author_info'] = slide.get('author_info', '')
            elif layout == 'H2-section':
                content_dict['section_number'] = slide.get('section_number', '')
            elif layout == 'H3-closing':
                content_dict['contact_info'] = slide.get('contact_info', '')
            elif layout.startswith('I') and len(layout) > 1 and layout[1].isdigit():
                # I-series: image + text
                # v4.3: Unified API returns 'body' directly
                content_dict['image_url'] = slide.get('image_url', '')
                content_dict['body'] = slide.get('body') or slide.get('content', '')
            elif layout in ['C3-chart', 'C3', 'V2-chart-text', 'V2']:
                # Chart layouts
                content_dict['chart_html'] = slide.get('chart_html') or slide.get('content', '')
                if layout in ['V2-chart-text', 'V2']:
                    content_dict['body'] = slide.get('body') or slide.get('insights', '')
            elif layout == 'L02':
                # Analytics-native layout
                content_dict['element_1'] = slide.get('element_1', '')
                content_dict['element_2'] = slide.get('element_2', '')
                content_dict['element_3'] = slide.get('element_3', '')
                content_dict['element_4'] = slide.get('element_4', '')
            elif layout in ['C5-diagram', 'C5', 'V3-diagram-text', 'V3']:
                # Diagram layouts
                content_dict['diagram_html'] = slide.get('diagram_html') or slide.get('svg_content') or slide.get('content', '')
                if layout in ['V3-diagram-text', 'V3']:
                    content_dict['body'] = slide.get('body', '')
            elif layout in ['C4-infographic', 'C4', 'V4-infographic-text', 'V4']:
                # Infographic layouts
                content_dict['infographic_html'] = slide.get('infographic_html') or slide.get('content', '')
                if layout in ['V4-infographic-text', 'V4']:
                    content_dict['body'] = slide.get('body', '')
            elif layout == 'C1-text':
                # v4.3: C1-text unified API returns body and rich_content directly
                content_dict['body'] = slide.get('body') or slide.get('content', '')
                content_dict['rich_content'] = slide.get('rich_content', '')
                content_dict['html'] = slide.get('content', '')
            else:
                # Default: L25 - use rich_content
                # v4.3: Prefer body/rich_content from unified API, fall back to content
                content_dict['rich_content'] = slide.get('rich_content') or slide.get('body') or slide.get('content', '')
                content_dict['html'] = slide.get('content', '')

            # Assemble payload using LayoutPayloadAssembler
            payload = assembler.assemble(
                layout=layout,
                slide_title=slide_title,
                subtitle=subtitle,
                content=content_dict,
                branding=branding,
                context=context,
                background_color=slide.get('background_color'),
                background_image=slide.get('background_image')
            )

            slides_payload.append(payload)

        # Create NEW presentation (v3.4 approach - not update)
        presentation_data = {
            'title': session.topic or session.initial_request or 'Presentation',
            'slides': slides_payload
        }

        # v4.0.31: Use print() for Railway visibility
        print(f"[DECK] Creating final presentation with {len(slides_payload)} slides...")
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

        # v4.0.31: Use print() for Railway visibility
        print(f"[DECK-OK] Final presentation created: id={final_id}, url={final_url}")
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
