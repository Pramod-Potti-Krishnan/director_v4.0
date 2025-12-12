"""
Supabase client and operations for Deckster.
"""
import os
from typing import Optional
from supabase import acreate_client, AsyncClient
from config.settings import get_settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Global client instance
_supabase_client: Optional[AsyncClient] = None


async def get_supabase_client() -> AsyncClient:
    """
    Get or create the Supabase client instance.
    
    Returns:
        Supabase client
        
    Raises:
        RuntimeError: If Supabase is not configured or connection fails
    """
    global _supabase_client
    
    if _supabase_client is None:
        settings = get_settings()
        
        # Check if Supabase is configured
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            raise RuntimeError(
                "Supabase configuration missing. "
                "Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables."
            )
        
        try:
            # Create async client
            _supabase_client = await acreate_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_ANON_KEY
            )
            logger.info("Supabase async client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise RuntimeError(f"Cannot connect to Supabase: {str(e)}")
    
    return _supabase_client


class SupabaseOperations:
    """Wrapper for common Supabase operations."""
    
    def __init__(self):
        """Initialize with Supabase client."""
        self.client = get_supabase_client()
        self.sessions_table = "sessions"
    
    async def create_session(self, session_data: dict) -> dict:
        """
        Create a new session.
        
        Args:
            session_data: Session data to insert
            
        Returns:
            Created session data
        """
        try:
            result = await self.client.table(self.sessions_table).insert(session_data).execute()
            logger.info(f"Created session: {session_data.get('id')}")
            return result.data[0] if result.data else session_data
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """
        Get a session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None
        """
        try:
            result = await self.client.table(self.sessions_table).select("*").eq("id", session_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {str(e)}")
            return None
    
    async def update_session(self, session_id: str, updates: dict) -> dict:
        """
        Update a session.
        
        Args:
            session_id: Session ID
            updates: Fields to update
            
        Returns:
            Updated session data
        """
        try:
            result = await self.client.table(self.sessions_table).update(updates).eq("id", session_id).execute()
            logger.info(f"Updated session {session_id}")
            return result.data[0] if result.data else updates
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {str(e)}")
            raise
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Success status
        """
        try:
            await self.client.table(self.sessions_table).delete().eq("id", session_id).execute()
            logger.info(f"Deleted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
            return False