"""
Context Builder Module - Phase 1 Implementation
Intelligently selects only the necessary context for each workflow state.
"""

from typing import Dict, List, Any, Optional, Tuple
import json
from abc import ABC, abstractmethod
from datetime import datetime


class StateContextStrategy(ABC):
    """Abstract base for state-specific context strategies"""
    
    @abstractmethod
    def build_context(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build minimal context for this state"""
        pass
    
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """List fields this state needs from session data"""
        pass


class GreetingStrategy(StateContextStrategy):
    """PROVIDE_GREETING needs almost nothing"""
    
    def build_context(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "is_returning_user": bool(session_data.get("conversation_history"))
        }
    
    def get_required_fields(self) -> List[str]:
        return []  # No specific fields needed


class ClarifyingQuestionsStrategy(StateContextStrategy):
    """ASK_CLARIFYING_QUESTIONS needs only the topic"""
    
    def build_context(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "user_initial_request": session_data.get("user_initial_request", "")
        }
    
    def get_required_fields(self) -> List[str]:
        return ["user_initial_request"]


class ConfirmationPlanStrategy(StateContextStrategy):
    """CREATE_CONFIRMATION_PLAN needs topic + answers"""
    
    def build_context(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "user_initial_request": session_data.get("user_initial_request", ""),
            "clarifying_answers": session_data.get("clarifying_answers", {})
        }
    
    def get_required_fields(self) -> List[str]:
        return ["user_initial_request", "clarifying_answers"]


class GenerateStrawmanStrategy(StateContextStrategy):
    """GENERATE_STRAWMAN needs the full context: plan + original request + Q&A"""
    
    def build_context(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        # Note: In Phase 1, plan might still be in conversation history
        # We'll extract it from there
        plan = self._extract_plan_from_session(session_data)
        
        # GENERATE_STRAWMAN needs the complete picture
        return {
            "user_initial_request": session_data.get("user_initial_request", ""),
            "clarifying_answers": session_data.get("clarifying_answers", {}),
            "confirmation_plan": plan
        }
    
    def get_required_fields(self) -> List[str]:
        return ["user_initial_request", "clarifying_answers"]  # Plus plan from history
    
    def _extract_plan_from_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract plan from conversation history (Phase 1 approach)"""
        # Look through conversation history for the plan
        for msg in reversed(session_data.get("conversation_history", [])):
            if msg.get("role") == "assistant":
                content = msg.get("content", {})
                if isinstance(content, dict) and content.get("type") == "ConfirmationPlan":
                    return content
        return {}


class RefineStrawmanStrategy(StateContextStrategy):
    """REFINE_STRAWMAN needs COMPLETE strawman + recent feedback"""
    
    def build_context(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        # Get last 3 messages for refinement context
        recent_history = session_data.get("conversation_history", [])[-3:]
        
        # Extract refinement request
        refinement_request = ""
        for msg in reversed(recent_history):
            if msg.get("role") == "user":
                refinement_request = msg.get("content", "")
                break
        
        # Extract current strawman (Phase 1: from conversation history)
        current_strawman = self._extract_strawman_from_session(session_data)
        
        return {
            "current_strawman": current_strawman,  # FULL strawman, not summary!
            "refinement_request": refinement_request
        }
    
    def get_required_fields(self) -> List[str]:
        return []  # Will use conversation history in Phase 1
    
    def _extract_strawman_from_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract strawman from session data or conversation history"""
        # First try session_data (more reliable)
        if 'presentation_strawman' in session_data and session_data['presentation_strawman']:
            strawman = session_data['presentation_strawman']
            if isinstance(strawman, dict) and 'slides' in strawman:
                return strawman
        
        # Fallback to conversation history
        for msg in reversed(session_data.get("conversation_history", [])):
            if msg.get("role") == "assistant":
                content = msg.get("content", {})
                if isinstance(content, dict) and content.get("type") == "PresentationStrawman":
                    return content
        
        # Log warning if not found
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("No strawman found in session data or conversation history")
        return {}
    
    def _summarize_strawman(self, strawman: Dict[str, Any]) -> Dict[str, Any]:
        """Create a lightweight summary instead of full content"""
        if not strawman:
            return {}
        
        slides = strawman.get("slides", [])
        return {
            "title": strawman.get("title", ""),
            "num_slides": len(slides),
            "slide_titles": [s.get("title", "") for s in slides]
        }


class LayoutGenerationStrategy(StateContextStrategy):
    """LAYOUT_GENERATION needs full strawman for layout creation"""

    def build_context(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        # Extract strawman from session data
        strawman = self._extract_strawman_from_session(session_data)

        return {
            "presentation_strawman": strawman,  # Full strawman for layout generation
            "user_initial_request": session_data.get("user_initial_request", ""),
            "clarifying_answers": session_data.get("clarifying_answers", {}),
            "target_audience": session_data.get("clarifying_answers", {}).get("audience", ""),
            "presentation_duration": session_data.get("clarifying_answers", {}).get("duration", "")
        }

    def get_required_fields(self) -> List[str]:
        return ["presentation_strawman", "user_initial_request", "clarifying_answers"]

    def _extract_strawman_from_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract strawman from session data"""
        # First try session_data (more reliable)
        if 'presentation_strawman' in session_data and session_data['presentation_strawman']:
            strawman = session_data['presentation_strawman']
            if isinstance(strawman, dict) and 'slides' in strawman:
                return strawman

        # Log warning if not found
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("No strawman found in session data for layout generation")
        return {}


class ContentGenerationStrategy(StateContextStrategy):
    """CONTENT_GENERATION needs strawman for text generation (v3.1 Stage 6)"""

    def build_context(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        # Extract strawman from session data
        strawman = self._extract_strawman_from_session(session_data)

        return {
            "presentation_strawman": strawman,  # Full strawman needed for text generation
            "user_initial_request": session_data.get("user_initial_request", ""),
            "clarifying_answers": session_data.get("clarifying_answers", {}),
        }

    def get_required_fields(self) -> List[str]:
        return ["presentation_strawman"]

    def _extract_strawman_from_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract strawman from session data"""
        # First try session_data (more reliable)
        if 'presentation_strawman' in session_data and session_data['presentation_strawman']:
            strawman = session_data['presentation_strawman']
            if isinstance(strawman, dict) and 'slides' in strawman:
                return strawman

        # Log warning if not found
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("No strawman found in session data for content generation")
        return {}


class ContextBuilder:
    """State-aware context builder - Phase 1 Core Component"""
    
    def __init__(self):
        self.strategies = {
            "PROVIDE_GREETING": GreetingStrategy(),
            "ASK_CLARIFYING_QUESTIONS": ClarifyingQuestionsStrategy(),
            "CREATE_CONFIRMATION_PLAN": ConfirmationPlanStrategy(),
            "GENERATE_STRAWMAN": GenerateStrawmanStrategy(),
            "REFINE_STRAWMAN": RefineStrawmanStrategy(),
            "LAYOUT_GENERATION": LayoutGenerationStrategy(),  # Phase 2 support
            "CONTENT_GENERATION": ContentGenerationStrategy()  # v3.1 Stage 6
        }
    
    def build_context(
        self, 
        state: str, 
        session_data: Dict[str, Any],
        user_intent: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Build minimal context for the given state"""
        
        strategy = self.strategies.get(state)
        if not strategy:
            raise ValueError(f"No strategy defined for state: {state}")
        
        # Get minimal context from strategy
        context = strategy.build_context(session_data)
        
        # Add current state and intent
        context["current_state"] = state
        if user_intent:
            context["user_intent"] = user_intent
        
        # Generate prompt
        prompt = self._generate_prompt(state, context)
        
        return context, prompt
    
    
    def _generate_prompt(self, state: str, context: Dict[str, Any]) -> str:
        """Generate state-specific prompts with minimal context"""
        
        if state == "PROVIDE_GREETING":
            return "Provide a warm greeting and ask what presentation the user wants to create."
        
        elif state == "ASK_CLARIFYING_QUESTIONS":
            return f"""The user wants to create a presentation about:
{context.get('user_initial_request')}

Ask 3-5 clarifying questions about audience, duration, key messages, and focus areas."""
        
        elif state == "CREATE_CONFIRMATION_PLAN":
            return f"""Create a presentation plan based on:
Topic: {context.get('user_initial_request')}
Details: {json.dumps(context.get('clarifying_answers', {}), indent=2)}

Include title, 5-7 slides with key points, duration, and themes."""
        
        elif state == "GENERATE_STRAWMAN":
            return f"""Generate a complete presentation based on:

Original Request: {context.get('user_initial_request')}
User Requirements: {json.dumps(context.get('clarifying_answers', {}), indent=2)}
Approved Plan: {json.dumps(context.get('confirmation_plan', {}), indent=2)}

Create detailed content for each slide that incorporates all the above context."""
        
        elif state == "REFINE_STRAWMAN":
            strawman = context.get('current_strawman', {})
            return f"""Refine the presentation based on user feedback.

Current presentation:
{json.dumps(strawman, indent=2)}

User's refinement request: {context.get('refinement_request')}

Make the requested changes while maintaining the overall structure and quality."""

        elif state == "CONTENT_GENERATION":
            strawman = context.get('presentation_strawman', {})
            slide_count = len(strawman.get('slides', []))
            return f"""Generate enriched content for presentation slides.

Current presentation:
Title: {strawman.get('main_title', '')}
Theme: {strawman.get('overall_theme', '')}
Audience: {strawman.get('target_audience', '')}
Total Slides: {slide_count}

This stage generates real text content for each slide using the Text Service.
Content will be contextually relevant and professionally written."""

        return json.dumps(context)
    
    def estimate_tokens(self, text: str) -> int:
        """Simple token estimation"""
        return len(text) // 4