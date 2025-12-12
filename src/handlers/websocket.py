"""
WebSocket Handler for Director Agent v4.0

Uses AI-driven Decision Engine instead of rigid state machine.
Preserves connection management and message protocol from v3.4.
"""

import json
import asyncio
import logging
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
from src.tools.registry import register_all_tools, ToolCall
from src.storage.supabase import get_supabase_client
from src.models.websocket_messages import (
    StreamlinedMessage,
    create_chat_message,
    create_status_update,
    create_slide_update,
    create_sync_response,
    create_presentation_url
)

logger = logging.getLogger(__name__)


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

        # Initialize Decision Engine
        self.decision_engine = DecisionEngine(
            tool_registry=self.tool_registry,
            model_name=getattr(self.settings, 'GCP_MODEL_DECISION', 'gemini-2.5-flash-preview-05-20')
        )
        logger.info("Decision Engine initialized")

        # Initialize Strawman Generator
        self.strawman_generator = StrawmanGenerator(
            model_name=getattr(self.settings, 'GCP_MODEL_STRAWMAN', 'gemini-2.5-flash-preview-05-20')
        )
        logger.info("Strawman Generator initialized")

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
                data = json.loads(raw_data)

                # Handle ping/pong
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

        Args:
            websocket: WebSocket connection
            session: Current session
            data: Incoming message data
        """
        message_type = data.get('type', 'chat_message')
        payload = data.get('payload', {})

        # Extract user message
        if message_type == 'chat_message':
            user_message = payload.get('content', payload.get('message', ''))
        elif message_type == 'action_request':
            # Convert action to message
            action = payload.get('action', '')
            user_message = f"[ACTION: {action}] {payload.get('message', '')}"
        else:
            logger.warning(f"Unknown message type: {message_type}")
            return

        if not user_message:
            return

        logger.info(f"Processing message: {user_message[:100]}...")

        # Add to conversation history
        await self.session_manager.add_to_history(
            session.id, session.user_id,
            {'role': 'user', 'content': user_message, 'timestamp': datetime.utcnow().isoformat()}
        )

        # Refresh session
        session = await self.session_manager.get_or_create(session.id, session.user_id)

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

        # Update session based on context detected
        await self._update_session_from_response(session, decision)

        await self._send_chat(websocket, session, response_text)

    async def _handle_ask_questions(self, websocket: WebSocket, session: SessionV4, decision):
        """Handle ASK_QUESTIONS action - ask clarifying questions."""
        questions = decision.questions or []
        intro = decision.response_text or "To create the best presentation, I have a few questions:"

        # Format as chat message
        message = intro + "\n\n" + "\n".join([f"• {q}" for q in questions])

        await self._send_chat(websocket, session, message)

    async def _handle_propose_plan(self, websocket: WebSocket, session: SessionV4, decision):
        """Handle PROPOSE_PLAN action - propose presentation structure."""
        plan_data = decision.plan_data or {}

        message = decision.response_text or f"""Here's my proposed plan for your presentation:

**Summary:** {plan_data.get('summary', 'Your presentation')}

**Proposed Slides:** {plan_data.get('proposed_slide_count', 10)} slides

**Key Assumptions:**
{chr(10).join(['• ' + a for a in plan_data.get('key_assumptions', [])])}

Would you like me to proceed with this plan, or would you like to make any changes?"""

        # Update session
        await self.session_manager.update_progress(
            session.id, session.user_id,
            {'has_plan': True}
        )

        await self._send_chat(websocket, session, message)

    async def _handle_generate_strawman(self, websocket: WebSocket, session: SessionV4, decision):
        """Handle GENERATE_STRAWMAN action - create presentation outline."""
        # Send status
        await self._send_status(websocket, session, "Generating presentation outline...")

        # Generate strawman
        strawman = await self.strawman_generator.generate(
            topic=session.topic or session.initial_request or "Untitled",
            audience=session.audience or "general",
            duration=session.duration or 15,
            purpose=session.purpose or "inform"
        )

        # Save strawman
        strawman_dict = strawman.dict()
        await self.session_manager.save_strawman(
            session.id, session.user_id, strawman_dict
        )

        # Send slide update
        await self._send_slide_update(websocket, session, strawman_dict)

        # Send follow-up message
        await self._send_chat(
            websocket, session,
            f"I've created an outline with {len(strawman.slides)} slides. "
            "Take a look and let me know if you'd like any changes, "
            "or say 'generate' when you're ready to create the actual content."
        )

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
        """Update session based on information extracted from response."""
        # This would be enhanced to extract topic, audience, etc. from conversation
        pass

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

    async def _send_status(self, websocket: WebSocket, session: SessionV4, message: str):
        """Send status update."""
        status_msg = create_status_update(session.id, message)
        await websocket.send_json(status_msg.model_dump(mode='json'))

    async def _send_slide_update(self, websocket: WebSocket, session: SessionV4, strawman: Dict):
        """Send slide update with strawman."""
        # Convert strawman to slides format expected by frontend
        slides = []
        for slide in strawman.get('slides', []):
            slides.append({
                'slide_id': slide.get('slide_id'),
                'title': slide.get('title'),
                'topics': slide.get('topics', []),
                'layout': slide.get('layout', 'L01'),
                'is_hero': slide.get('is_hero', False)
            })

        slide_msg = create_slide_update(
            session_id=session.id,
            slides=slides,
            metadata={
                'main_title': strawman.get('title', 'Untitled'),
                'slide_count': len(slides)
            }
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


# Compatibility alias
WebSocketHandler = WebSocketHandlerV4
