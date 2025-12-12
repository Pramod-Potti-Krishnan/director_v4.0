"""
Streamlined Message Packager

This module converts agent outputs into lists of streamlined WebSocket messages
according to the new protocol. Each state handler returns a list of messages
that map directly to frontend UI components.
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import uuid

from src.models.websocket_messages import (
    StreamlinedMessage,
    ChatMessage,
    ActionRequest,
    SlideUpdate,
    StatusUpdate,
    PresentationURL,
    create_chat_message,
    create_action_request,
    create_slide_update,
    create_status_update,
    create_presentation_url,
    StatusLevel
)
from src.models.agents import (
    ClarifyingQuestions,
    ConfirmationPlan,
    PresentationStrawman,
    StateContext
)


class StreamlinedMessagePackager:
    """Packages agent outputs into streamlined WebSocket messages."""
    
    def __init__(self):
        """Initialize the packager."""
        pass
    
    def package_messages(
        self,
        session_id: str,
        state: str,
        agent_output: Any,
        context: Optional[StateContext] = None
    ) -> List[StreamlinedMessage]:
        """
        Package agent output into streamlined messages based on current state.
        
        Args:
            session_id: Current session identifier
            state: Current conversation state
            agent_output: Output from the agent
            context: Optional state context
            
        Returns:
            List of streamlined messages to send
        """
        if state == "PROVIDE_GREETING":
            return self._package_greeting(session_id)
        
        elif state == "ASK_CLARIFYING_QUESTIONS":
            return self._package_questions(session_id, agent_output)
        
        elif state == "CREATE_CONFIRMATION_PLAN":
            return self._package_confirmation_plan(session_id, agent_output)
        
        elif state == "GENERATE_STRAWMAN":
            return self._package_strawman(session_id, agent_output)
        
        elif state == "REFINE_STRAWMAN":
            return self._package_refinement(session_id, agent_output, context)

        elif state == "CONTENT_GENERATION":
            return self._package_content_generation(session_id, agent_output)

        else:
            # Fallback for unknown states
            return [create_chat_message(
                session_id=session_id,
                text=f"Processing state: {state}",
                role="assistant"
            )]
    
    def _package_greeting(self, session_id: str) -> List[StreamlinedMessage]:
        """Package greeting state messages."""
        return [
            create_chat_message(
                session_id=session_id,
                text="Hello! I'm Deckster, your AI presentation assistant. I can help you create "
                     "professional, engaging presentations on any topic.\n\n"
                     "What presentation would you like to build today?",
                role="assistant"
            )
        ]
    
    def _package_questions(
        self,
        session_id: str,
        questions: ClarifyingQuestions
    ) -> List[StreamlinedMessage]:
        """Package clarifying questions."""
        return [
            create_chat_message(
                session_id=session_id,
                text="Great topic! To create the perfect presentation for you, I need to understand your needs better:",
                list_items=questions.questions,
                role="assistant"
            )
        ]
    
    def _package_confirmation_plan(
        self,
        session_id: str,
        plan: ConfirmationPlan
    ) -> List[StreamlinedMessage]:
        """Package confirmation plan with separate summary and actions."""
        messages = []
        
        # Message 1: Plan summary
        messages.append(
            create_chat_message(
                session_id=session_id,
                text=f"Perfect! Based on your input, I'll create a {plan.proposed_slide_count}-slide presentation.",
                sub_title="Key assumptions I'm making:",
                list_items=plan.key_assumptions,
                role="assistant"
            )
        )
        
        # Message 2: Action request
        messages.append(
            create_action_request(
                session_id=session_id,
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
        )
        
        return messages
    
    def _package_strawman(
        self,
        session_id: str,
        strawman: Union[PresentationStrawman, Dict[str, Any]]
    ) -> List[StreamlinedMessage]:
        """Package strawman generation with status, slides, and actions."""
        messages = []

        # Note: Status update should be sent BEFORE generation starts
        # This is handled by create_pre_generation_status method

        # v2.0: Check if this is a URL response from deck-builder
        if isinstance(strawman, dict) and strawman.get("type") == "presentation_url":
            # v2.0 mode: deck-builder returned a URL - create proper message
            return [
                create_presentation_url(
                    session_id=session_id,
                    url=strawman.get("url", ""),
                    presentation_id=strawman.get("presentation_id", ""),
                    slide_count=strawman.get("slide_count", 0),
                    message=strawman.get("message", "Your presentation is ready!")
                )
            ]

        # v1.0 mode: Original logic for PresentationStrawman object
        # Message 1: Slide update with structured slide data
        slide_data = self._convert_slides_to_data(strawman)

        # v3.4 DIAGNOSTIC: Detailed logging for preview_url packaging (using print for Railway visibility)
        preview_url_value = strawman.preview_url if hasattr(strawman, 'preview_url') else None
        preview_presentation_id_value = strawman.preview_presentation_id if hasattr(strawman, 'preview_presentation_id') else None

        import sys
        print("="*80, flush=True)
        print("📦 PACKAGING STAGE 4 SLIDE_UPDATE", flush=True)
        print(f"   strawman type: {type(strawman)}", flush=True)
        print(f"   strawman class name: {strawman.__class__.__name__}", flush=True)
        print(f"   hasattr preview_url: {hasattr(strawman, 'preview_url')}", flush=True)
        print(f"   preview_url value: {preview_url_value}", flush=True)
        print(f"   hasattr preview_presentation_id: {hasattr(strawman, 'preview_presentation_id')}", flush=True)
        print(f"   preview_presentation_id value: {preview_presentation_id_value}", flush=True)

        # v3.4 FIX: Show warning if preview_url is None
        if not preview_url_value:
            print(f"   ⚠️  WARNING: preview_url is None!", flush=True)
            # Check if there's an error message stored
            if hasattr(strawman, '_preview_url_error'):
                print(f"   ⚠️  Reason: {strawman._preview_url_error}", flush=True)
            else:
                print(f"   ⚠️  Reason: Not set by Stage 4 (deck-builder might have failed)", flush=True)
            print(f"   ⚠️  Frontend will NOT show preview!", flush=True)
        else:
            print(f"   ✅ Preview URL will be sent to frontend", flush=True)

        print(f"   strawman.main_title: {strawman.main_title}", flush=True)
        print(f"   Total slides: {len(slide_data)}", flush=True)
        print("="*80, flush=True)
        sys.stdout.flush()

        messages.append(
            create_slide_update(
                session_id=session_id,
                operation="full_update",
                metadata={
                    "main_title": strawman.main_title,
                    "overall_theme": strawman.overall_theme,
                    "design_suggestions": strawman.design_suggestions,
                    "target_audience": strawman.target_audience,
                    "presentation_duration": strawman.presentation_duration,
                    "preview_url": preview_url_value,
                    "preview_presentation_id": preview_presentation_id_value
                },
                slides=slide_data
            )
        )

        # v3.4 FIX: If preview URL exists, send it as a chat message before action buttons
        # Note: Frontend displays preview_url in viewer pane, not as link in chat
        if hasattr(strawman, 'preview_url') and strawman.preview_url:
            messages.append(
                create_chat_message(
                    session_id=session_id,
                    text="Review the structural outline in the preview. If you're happy with the structure, click 'Looks perfect!' to generate rich HTML content for all slides using AI.",
                    format="plain",
                    role="assistant"
                )
            )

        # Message 2: Action request (ALWAYS send this!)
        messages.append(
            create_action_request(
                session_id=session_id,
                prompt_text="A base strawman is ready for you to validate. Does the structure look good, or would you like to propose refinements?",
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
        )

        return messages
    
    def _package_refinement(
        self,
        session_id: str,
        refined_strawman: Union[PresentationStrawman, Dict[str, Any]],
        context: Optional[StateContext] = None
    ) -> List[StreamlinedMessage]:
        """Package refined strawman with partial updates."""
        messages = []

        # v2.0: Check if this is a URL response from deck-builder
        if isinstance(refined_strawman, dict) and refined_strawman.get("type") == "presentation_url":
            # v2.0 mode: deck-builder returned a refined URL - create proper message
            return [
                create_presentation_url(
                    session_id=session_id,
                    url=refined_strawman.get("url", ""),
                    presentation_id=refined_strawman.get("presentation_id", ""),
                    slide_count=refined_strawman.get("slide_count", 0),
                    message=refined_strawman.get("message", "Your presentation has been refined!")
                )
            ]

        # v1.0 mode: Original logic for PresentationStrawman object
        # Message 1: Status update
        messages.append(
            create_status_update(
                session_id=session_id,
                status=StatusLevel.GENERATING,
                text="Refining your presentation based on your feedback...",
                progress=0
            )
        )

        # Message 2: Partial slide update
        # Note: In real implementation, we'd compare with previous version
        # and only send changed slides
        affected_slide_ids = self._get_affected_slides(refined_strawman, context)
        slide_data = self._convert_slides_to_data(
            refined_strawman,
            only_slides=affected_slide_ids
        )

        messages.append(
            create_slide_update(
                session_id=session_id,
                operation="partial_update",
                metadata={
                    "main_title": refined_strawman.main_title,
                    "overall_theme": refined_strawman.overall_theme,
                    "design_suggestions": refined_strawman.design_suggestions,
                    "target_audience": refined_strawman.target_audience,
                    "presentation_duration": refined_strawman.presentation_duration,
                    "preview_url": refined_strawman.preview_url if hasattr(refined_strawman, 'preview_url') else None
                },
                slides=slide_data,
                affected_slides=affected_slide_ids
            )
        )

        # Message 3: Explanation of changes
        messages.append(
            create_chat_message(
                session_id=session_id,
                text="I've updated your presentation based on your feedback.",
                sub_title="Changes made:",
                list_items=[
                    f"Updated slide {slide_id.split('_')[1]} with your requested changes"
                    for slide_id in affected_slide_ids
                ],
                role="assistant"
            )
        )

        # Message 4: Action request
        messages.append(
            create_action_request(
                session_id=session_id,
                prompt_text="Would you like to make any other changes?",
                actions=[
                    {
                        "label": "All done, looks great!",
                        "value": "accept_strawman",
                        "primary": True,
                        "requires_input": False
                    },
                    {
                        "label": "Make more changes",
                        "value": "request_refinement",
                        "primary": False,
                        "requires_input": True
                    }
                ]
            )
        )

        return messages

    def _package_content_generation(
        self,
        session_id: str,
        agent_output: Any
    ) -> List[StreamlinedMessage]:
        """Package content generation (Stage 6) messages."""
        # Check if this is a presentation URL response (v3.1 Stage 6 output)
        if isinstance(agent_output, dict) and agent_output.get("type") == "presentation_url":
            successful = agent_output.get("successful_slides", 0)
            total = agent_output.get("slide_count", 0)
            failed = agent_output.get("failed_slides", 0)

            # Build success message
            if failed == 0:
                text = f"Your presentation with real content is ready!\n\n"
                text += f"Content generated for all {successful} slides"
            else:
                text = f"Your presentation is ready!\n\n"
                text += f"Content generated for {successful}/{total} slides\n"
                text += f"({failed} slide(s) used placeholder content)"

            return [
                create_presentation_url(
                    session_id=session_id,
                    url=agent_output.get("url", ""),
                    presentation_id=agent_output.get("presentation_id", ""),
                    slide_count=total,
                    message=text
                )
            ]
        else:
            # Fallback for unexpected output format
            return [
                create_chat_message(
                    session_id=session_id,
                    text="Processing content generation...",
                    role="assistant"
                )
            ]

    def _convert_slides_to_data(
        self,
        strawman: PresentationStrawman,
        only_slides: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Convert Slide objects to dictionaries with all fields preserved.
        
        Args:
            strawman: The presentation strawman
            only_slides: Optional list of slide IDs to include (for partial updates)
            
        Returns:
            List of slide data dictionaries
        """
        slide_data = []
        
        for slide in strawman.slides:
            # Skip if we're doing partial update and this slide isn't affected
            if only_slides and slide.slide_id not in only_slides:
                continue
            
            slide_data.append({
                "slide_id": slide.slide_id,
                "slide_number": slide.slide_number,
                "slide_type": slide.slide_type,
                "title": slide.title,
                "narrative": slide.narrative,
                "key_points": slide.key_points,
                "analytics_needed": slide.analytics_needed,
                "visuals_needed": slide.visuals_needed,
                "diagrams_needed": slide.diagrams_needed,
                "structure_preference": slide.structure_preference
            })
        
        return slide_data
    
    
    def _get_affected_slides(
        self,
        refined_strawman: PresentationStrawman,
        context: Optional[StateContext] = None
    ) -> List[str]:
        """
        Determine which slides were affected by refinement.
        
        In production, this would compare with previous version
        to identify actual changes.
        """
        # Placeholder: assume slides 3 and 5 were changed
        # In real implementation, would do actual comparison
        return ["slide_003", "slide_005"]
    
    def create_status_message(
        self,
        session_id: str,
        status: StatusLevel,
        text: str,
        progress: Optional[int] = None,
        estimated_time: Optional[int] = None
    ) -> StatusUpdate:
        """Create a status update message."""
        return create_status_update(
            session_id=session_id,
            status=status,
            text=text,
            progress=progress,
            estimated_time=estimated_time
        )
    
    def create_error_message(
        self,
        session_id: str,
        error_text: str
    ) -> List[StreamlinedMessage]:
        """Create error messages."""
        return [
            create_status_update(
                session_id=session_id,
                status=StatusLevel.ERROR,
                text=error_text
            ),
            create_chat_message(
                session_id=session_id,
                text="I encountered an error while processing your request. Please try again or let me know if you need help.",
                format="plain",
                role="assistant"
            )
        ]
    
    def create_pre_generation_status(
        self,
        session_id: str,
        state: str
    ) -> StreamlinedMessage:
        """
        Create a status update to send BEFORE processing starts.
        
        Args:
            session_id: Session identifier
            state: Current state (GENERATE_STRAWMAN, REFINE_STRAWMAN, or CONTENT_GENERATION)

        Returns:
            Status update message
        """
        if state == "GENERATE_STRAWMAN":
            return create_status_update(
                session_id=session_id,
                status=StatusLevel.GENERATING,
                text="I'm working on the strawman to ensure we get the structure right before bringing in the details...",
                progress=0,
                estimated_time=20
            )
        elif state == "REFINE_STRAWMAN":
            return create_status_update(
                session_id=session_id,
                status=StatusLevel.GENERATING,
                text="Refining your presentation based on your feedback...",
                progress=0,
                estimated_time=15
            )
        elif state == "CONTENT_GENERATION":
            return create_status_update(
                session_id=session_id,
                status=StatusLevel.GENERATING,
                text="Generating real content for your slides using AI... This may take 30-60 seconds...",
                progress=0,
                estimated_time=45
            )
        else:
            return create_status_update(
                session_id=session_id,
                status=StatusLevel.THINKING,
                text="Processing your request...",
                progress=0
            )
    
    def create_progress_update(
        self,
        session_id: str,
        progress_percent: int,
        text: Optional[str] = None
    ) -> StatusUpdate:
        """
        Create a progress update during processing.
        
        Args:
            session_id: Session identifier
            progress_percent: Progress percentage (0-100)
            text: Optional status text
            
        Returns:
            Status update message
        """
        if text is None:
            if progress_percent < 30:
                text = "Analyzing your requirements..."
            elif progress_percent < 60:
                text = "Structuring your presentation..."
            elif progress_percent < 90:
                text = "Finalizing slide content..."
            else:
                text = "Almost done..."
        
        return create_status_update(
            session_id=session_id,
            status=StatusLevel.GENERATING,
            text=text,
            progress=progress_percent
        )
    
    def create_completion_status(
        self,
        session_id: str
    ) -> StatusUpdate:
        """Create a completion status update."""
        return create_status_update(
            session_id=session_id,
            status=StatusLevel.COMPLETE,
            text="Your presentation is ready!",
            progress=100
        )