"""
Session Management for Director Agent v4.0

Manages session CRUD operations with Supabase for the flexible SessionV4 model.

Key changes from v3.4:
- Works with SessionV4 (progress flags instead of state)
- Generic context storage
- Flexible field updates
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import traceback
import logging
from supabase import AsyncClient

from src.models.session import SessionV4

logger = logging.getLogger(__name__)


class SessionManagerV4:
    """
    Manages session CRUD operations with Supabase for v4.0.

    Uses flexible context storage instead of state-specific fields.
    """

    def __init__(self, supabase_client: AsyncClient):
        """
        Initialize session manager.

        Args:
            supabase_client: Supabase async client instance
        """
        self.supabase = supabase_client
        self.table_name = "dr_sessions_v4"  # New table for v4.0
        self.cache: Dict[str, SessionV4] = {}  # Local cache

        logger.info(f"SessionManagerV4 initialized with table: {self.table_name}")

    async def get_or_create(self, session_id: str, user_id: str) -> SessionV4:
        """
        Get existing session or create new one.

        Args:
            session_id: Session ID
            user_id: User ID

        Returns:
            SessionV4 object
        """
        # Check cache first
        cache_key = f"{user_id}:{session_id}"
        if cache_key in self.cache:
            logger.debug(f"Cache hit for session {session_id}")
            return self.cache[cache_key]

        # Try to fetch from Supabase
        try:
            result = await self.supabase.table(self.table_name).select("*").eq("id", session_id).eq("user_id", user_id).execute()

            if result.data:
                session_data = result.data[0]
                session = SessionV4.from_supabase(session_data)
                self.cache[cache_key] = session
                logger.info(f"Retrieved session {session_id} from Supabase")
                return session

        except Exception as e:
            logger.error(f"Error fetching session {session_id}: {type(e).__name__}: {str(e)}")
            traceback.print_exc()

        # Create new session
        session = SessionV4(
            id=session_id,
            user_id=user_id,
            conversation_history=[],
            context={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # Save to Supabase
        try:
            session_data = session.to_supabase_dict()
            await self.supabase.table(self.table_name).insert(session_data).execute()
            logger.info(f"Created new session {session_id} for user {user_id}")
        except Exception as e:
            logger.error(f"Error creating session in Supabase: {type(e).__name__}: {str(e)}")
            traceback.print_exc()
            # Continue with local session

        self.cache[cache_key] = session
        return session

    async def update_progress(
        self,
        session_id: str,
        user_id: str,
        flags: Dict[str, bool]
    ) -> None:
        """
        Update progress flags.

        Args:
            session_id: Session ID
            user_id: User ID
            flags: Dict of flag_name -> value
        """
        session = await self.get_or_create(session_id, user_id)

        # Update flags
        for flag, value in flags.items():
            if hasattr(session, flag):
                setattr(session, flag, value)

        session.updated_at = datetime.utcnow()

        # Update in Supabase
        try:
            updates = {**flags, 'updated_at': session.updated_at.isoformat()}
            await self.supabase.table(self.table_name).update(updates).eq('id', session_id).eq('user_id', user_id).execute()
            logger.info(f"Updated progress flags for session {session_id}: {flags}")

            # Clear cache
            self._clear_cache(user_id, session_id)

        except Exception as e:
            logger.error(f"Error updating progress flags: {type(e).__name__}: {str(e)}")
            traceback.print_exc()

    async def set_context(
        self,
        session_id: str,
        user_id: str,
        key: str,
        value: Any
    ) -> None:
        """
        Set a context value.

        Args:
            session_id: Session ID
            user_id: User ID
            key: Context key
            value: Context value
        """
        session = await self.get_or_create(session_id, user_id)
        session.set_context(key, value)

        # Update in Supabase
        try:
            await self.supabase.table(self.table_name).update({
                'context': session.context,
                'updated_at': session.updated_at.isoformat()
            }).eq('id', session_id).eq('user_id', user_id).execute()
            logger.debug(f"Set context {key} for session {session_id}")

        except Exception as e:
            logger.error(f"Error setting context: {type(e).__name__}: {str(e)}")
            traceback.print_exc()

    async def add_to_history(
        self,
        session_id: str,
        user_id: str,
        message: Dict[str, Any]
    ) -> None:
        """
        Add message to conversation history.

        Args:
            session_id: Session ID
            user_id: User ID
            message: Message dict with role, content, timestamp
        """
        session = await self.get_or_create(session_id, user_id)

        # Convert Pydantic objects to dict if needed
        if hasattr(message.get('content'), 'dict'):
            message['content'] = message['content'].dict()

        # Add timestamp if not present
        if 'timestamp' not in message:
            message['timestamp'] = datetime.utcnow().isoformat()

        session.conversation_history.append(message)
        session.updated_at = datetime.utcnow()

        # Update in Supabase
        try:
            await self.supabase.table(self.table_name).update({
                'conversation_history': session.conversation_history,
                'updated_at': session.updated_at.isoformat()
            }).eq('id', session_id).eq('user_id', user_id).execute()
            logger.debug(f"Added message to session {session_id} history")

        except Exception as e:
            logger.error(f"Error updating conversation history: {type(e).__name__}: {str(e)}")
            traceback.print_exc()

    async def save_field(
        self,
        session_id: str,
        user_id: str,
        field: str,
        value: Any
    ) -> None:
        """
        Save a specific session field.

        Args:
            session_id: Session ID
            user_id: User ID
            field: Field name
            value: Value to save
        """
        session = await self.get_or_create(session_id, user_id)

        if hasattr(session, field):
            setattr(session, field, value)
            session.updated_at = datetime.utcnow()

            try:
                await self.supabase.table(self.table_name).update({
                    field: value,
                    'updated_at': session.updated_at.isoformat()
                }).eq('id', session_id).eq('user_id', user_id).execute()
                logger.info(f"Saved {field} for session {session_id}")

                self._clear_cache(user_id, session_id)

            except Exception as e:
                logger.error(f"Error saving session field: {type(e).__name__}: {str(e)}")
                traceback.print_exc()

    async def save_strawman(
        self,
        session_id: str,
        user_id: str,
        strawman: Dict[str, Any]
    ) -> None:
        """
        Save strawman and update progress flag.

        Args:
            session_id: Session ID
            user_id: User ID
            strawman: Strawman data
        """
        session = await self.get_or_create(session_id, user_id)

        session.strawman = strawman
        session.has_strawman = True
        session.updated_at = datetime.utcnow()

        try:
            await self.supabase.table(self.table_name).update({
                'strawman': strawman,
                'has_strawman': True,
                'updated_at': session.updated_at.isoformat()
            }).eq('id', session_id).eq('user_id', user_id).execute()
            logger.info(f"Saved strawman for session {session_id}")

            self._clear_cache(user_id, session_id)

        except Exception as e:
            logger.error(f"Error saving strawman: {type(e).__name__}: {str(e)}")
            traceback.print_exc()

    async def save_generated_slides(
        self,
        session_id: str,
        user_id: str,
        slides: List[Dict[str, Any]]
    ) -> None:
        """
        Save generated slides and update progress flag.

        Args:
            session_id: Session ID
            user_id: User ID
            slides: Generated slide content
        """
        session = await self.get_or_create(session_id, user_id)

        session.generated_slides = slides
        session.has_content = True
        session.updated_at = datetime.utcnow()

        try:
            await self.supabase.table(self.table_name).update({
                'generated_slides': slides,
                'has_content': True,
                'updated_at': session.updated_at.isoformat()
            }).eq('id', session_id).eq('user_id', user_id).execute()
            logger.info(f"Saved generated slides for session {session_id}")

            self._clear_cache(user_id, session_id)

        except Exception as e:
            logger.error(f"Error saving generated slides: {type(e).__name__}: {str(e)}")
            traceback.print_exc()

    async def save_presentation_url(
        self,
        session_id: str,
        user_id: str,
        presentation_id: str,
        url: str
    ) -> None:
        """
        Save presentation ID and URL, mark as complete.

        Args:
            session_id: Session ID
            user_id: User ID
            presentation_id: Deck builder presentation ID
            url: Preview URL
        """
        session = await self.get_or_create(session_id, user_id)

        session.presentation_id = presentation_id
        session.presentation_url = url
        session.is_complete = True
        session.updated_at = datetime.utcnow()

        try:
            await self.supabase.table(self.table_name).update({
                'presentation_id': presentation_id,
                'presentation_url': url,
                'is_complete': True,
                'updated_at': session.updated_at.isoformat()
            }).eq('id', session_id).eq('user_id', user_id).execute()
            logger.info(f"Saved presentation URL for session {session_id}: {url}")

            self._clear_cache(user_id, session_id)

        except Exception as e:
            logger.error(f"Error saving presentation URL: {type(e).__name__}: {str(e)}")
            traceback.print_exc()

    async def clear_for_new_presentation(
        self,
        session_id: str,
        user_id: str
    ) -> None:
        """
        Clear session for starting a new presentation.

        Args:
            session_id: Session ID
            user_id: User ID
        """
        session = await self.get_or_create(session_id, user_id)
        session.clear_for_new_presentation()

        try:
            await self.supabase.table(self.table_name).update({
                # Reset all progress flags
                'has_topic': False,
                'has_audience': False,
                'has_duration': False,
                'has_purpose': False,
                'has_plan': False,
                'has_strawman': False,
                'has_explicit_approval': False,
                'has_content': False,
                'is_complete': False,
                # Clear data
                'context': {},
                'initial_request': None,
                'topic': None,
                'audience': None,
                'duration': None,
                'purpose': None,
                'tone': None,
                'strawman': None,
                'generated_slides': None,
                'presentation_id': None,
                'presentation_url': None,
                'updated_at': session.updated_at.isoformat()
            }).eq('id', session_id).eq('user_id', user_id).execute()
            logger.info(f"Cleared session {session_id} for new presentation")

            self._clear_cache(user_id, session_id)

        except Exception as e:
            logger.error(f"Error clearing session: {type(e).__name__}: {str(e)}")
            traceback.print_exc()

    async def set_explicit_approval(
        self,
        session_id: str,
        user_id: str,
        approved: bool = True
    ) -> None:
        """
        Set explicit approval flag.

        Args:
            session_id: Session ID
            user_id: User ID
            approved: Whether user has approved
        """
        await self.update_progress(
            session_id, user_id,
            {'has_explicit_approval': approved}
        )

    def _clear_cache(self, user_id: str, session_id: str) -> None:
        """Clear session from cache."""
        cache_key = f"{user_id}:{session_id}"
        if cache_key in self.cache:
            del self.cache[cache_key]
            logger.debug(f"Cleared cache for session {session_id}")


# Compatibility alias
SessionManager = SessionManagerV4
