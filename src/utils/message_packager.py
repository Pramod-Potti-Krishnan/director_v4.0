"""
Message packaging utilities for frontend communication.
"""
from uuid import uuid4
from datetime import datetime
from typing import Optional, List, Dict, Any
from src.models.agents import (
    ClarifyingQuestions, ConfirmationPlan, PresentationStrawman
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MessagePackager:
    """Packages agent responses into DirectorMessage format for frontend."""
    
    @staticmethod
    def package(response: Any, session_id: str, current_state: str) -> dict:
        """
        Convert agent response to DirectorMessage format for frontend.
        
        Args:
            response: Agent response (various types)
            session_id: Session ID
            current_state: Current workflow state
            
        Returns:
            DirectorMessage formatted dict
        """
        base_message = {
            "id": f"msg_{uuid4().hex[:12]}",
            "type": "director_message",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "source": "director_inbound",
            "slide_data": None,
            "chat_data": None
        }
        
        # Handle different response types based on state
        if current_state == "PROVIDE_GREETING":
            base_message["chat_data"] = {
                "type": "info",
                "content": response,  # Simple string greeting
                "actions": None,
                "progress": None,
                "references": None
            }
            
        elif current_state == "ASK_CLARIFYING_QUESTIONS":
            # response is ClarifyingQuestions object or dict
            if hasattr(response, 'questions'):
                # It's a ClarifyingQuestions object
                questions = response.questions
            elif isinstance(response, dict) and 'questions' in response:
                # It's already a dict
                questions = response['questions']
            else:
                # Fallback - try to extract questions
                questions = response if isinstance(response, list) else []
            
            base_message["chat_data"] = {
                "type": "question",
                "content": {"questions": questions},
                "actions": None
            }
            
        elif current_state == "CREATE_CONFIRMATION_PLAN":
            # response is ConfirmationPlan object
            base_message["chat_data"] = {
                "type": "summary",
                "content": {
                    "summary_of_user_request": response.summary_of_user_request,
                    "key_assumptions": response.key_assumptions,
                    "proposed_slide_count": response.proposed_slide_count
                },
                "actions": [
                    {
                        "action_id": "accept",
                        "type": "accept_changes",
                        "label": "Accept",
                        "primary": True
                    },
                    {
                        "action_id": "reject",
                        "type": "provide_feedback",
                        "label": "Request Changes",
                        "primary": False
                    }
                ]
            }
            
        elif current_state in ["GENERATE_STRAWMAN", "REFINE_STRAWMAN"]:
            # response is PresentationStrawman object
            logger.debug(f"Packaging strawman with {len(response.slides)} slides")
            logger.debug(f"Strawman title: {response.main_title}")
            slides = []
            for slide in response.slides:
                slides.append({
                    # Use actual model fields
                    "slide_id": slide.slide_id,
                    "slide_number": slide.slide_number,
                    "slide_type": slide.slide_type,
                    "title": slide.title,
                    "narrative": slide.narrative,
                    "key_points": slide.key_points,
                    
                    # Optional guidance fields
                    "analytics_needed": slide.analytics_needed,
                    "visuals_needed": slide.visuals_needed,
                    "diagrams_needed": slide.diagrams_needed,
                    "structure_preference": slide.structure_preference,
                    "speaker_notes": slide.speaker_notes,
                    
                    # Legacy fields for backward compatibility
                    "subtitle": None,
                    "body_content": [
                        {"type": "text", "content": point}
                        for point in slide.key_points
                    ],
                    "layout_type": "content",  # Default, could be enhanced
                    "animations": [],
                    "transitions": {}
                })
            
            base_message["slide_data"] = {
                "type": "complete",
                "slides": slides,
                "presentation_metadata": {
                    "title": response.main_title,
                    "total_slides": len(response.slides),
                    "theme": response.overall_theme,
                    "design_suggestions": response.design_suggestions,
                    "target_audience": response.target_audience,
                    "presentation_duration": response.presentation_duration
                }
            }
            
            base_message["chat_data"] = {
                "type": "info",
                "content": "Here's your presentation structure. Would you like to make any changes?",
                "actions": [
                    {
                        "action_id": "accept",
                        "type": "accept_changes",
                        "label": "Looks good!",
                        "primary": True
                    },
                    {
                        "action_id": "refine",
                        "type": "request_refinement",
                        "label": "Make changes",
                        "primary": False,
                        "requires_input": True
                    }
                ]
            }
        
        logger.debug(f"Packaged {current_state} response for session {session_id}")
        return base_message
    
    @staticmethod
    def package_error(error: str, session_id: str) -> dict:
        """
        Package an error message.
        
        Args:
            error: Error message
            session_id: Session ID
            
        Returns:
            Error message in DirectorMessage format
        """
        return {
            "id": f"msg_{uuid4().hex[:12]}",
            "type": "director_message",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "source": "director_inbound",
            "slide_data": None,
            "chat_data": {
                "type": "error",
                "content": f"I encountered an error: {error}. Please try again.",
                "actions": None,
                "progress": None,
                "references": None
            }
        }
    
    @staticmethod
    def package_progress(message: str, session_id: str, agent_statuses: Optional[Dict[str, str]] = None) -> dict:
        """
        Package a progress update message.
        
        Args:
            message: Progress message
            session_id: Session ID
            agent_statuses: Optional status of various agents
            
        Returns:
            Progress message in DirectorMessage format
        """
        return {
            "id": f"msg_{uuid4().hex[:12]}",
            "type": "director_message",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "source": "director_inbound",
            "slide_data": None,
            "chat_data": {
                "type": "progress",
                "content": message,
                "actions": None,
                "progress": {
                    "status": "processing",
                    "agentStatuses": agent_statuses or {}
                },
                "references": None
            }
        }