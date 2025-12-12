"""
Unified Variant System Rollout Helper

Manages gradual rollout of the unified variant registration system.
Provides session-based decisions for using new vs. old classification/routing.

Version: 2.0.0
Created: 2025-11-29
"""

import hashlib
from typing import Optional
from config.settings import get_settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class UnifiedSystemRollout:
    """
    Rollout manager for unified variant system.

    Provides session-based decisions for gradual rollout based on:
    - Feature flag (UNIFIED_VARIANT_SYSTEM_ENABLED)
    - Rollout percentage (UNIFIED_VARIANT_SYSTEM_PERCENTAGE)
    - Session ID hashing for consistency

    Features:
    - Consistent session assignment (same session always gets same result)
    - Gradual percentage-based rollout
    - Easy to enable/disable globally
    - Logging for monitoring adoption

    Usage:
        rollout = UnifiedSystemRollout()

        if rollout.should_use_unified_system(session_id):
            # Use new unified system
            integration = DirectorIntegrationLayer()
            result = await integration.generate_presentation_content(...)
        else:
            # Use existing system
            router = ServiceRouterV1_2(...)
            result = await router.route_presentation(...)
    """

    def __init__(self):
        """Initialize rollout manager with settings."""
        self.settings = get_settings()

        logger.info(
            "UnifiedSystemRollout initialized",
            extra={
                "enabled": self.settings.UNIFIED_VARIANT_SYSTEM_ENABLED,
                "percentage": self.settings.UNIFIED_VARIANT_SYSTEM_PERCENTAGE
            }
        )

    def should_use_unified_system(self, session_id: Optional[str] = None) -> bool:
        """
        Determine if session should use unified variant system.

        Decision logic:
        1. If UNIFIED_VARIANT_SYSTEM_ENABLED=false → always return False
        2. If percentage=100 → always return True
        3. If percentage=0 → always return False
        4. Otherwise → hash session_id and check if it falls within percentage

        Args:
            session_id: Session identifier for consistent assignment

        Returns:
            True if should use unified system, False for existing system

        Example:
            rollout = UnifiedSystemRollout()

            # 50% rollout - some sessions use new, some use old
            if rollout.should_use_unified_system("session_123"):
                use_unified_system()
            else:
                use_existing_system()
        """
        # Check if feature is enabled
        if not self.settings.UNIFIED_VARIANT_SYSTEM_ENABLED:
            logger.debug("Unified system disabled by feature flag")
            return False

        # Get rollout percentage
        percentage = self.settings.UNIFIED_VARIANT_SYSTEM_PERCENTAGE

        # 100% rollout - always use unified
        if percentage >= 100:
            logger.debug("Using unified system (100% rollout)")
            return True

        # 0% rollout - never use unified
        if percentage <= 0:
            logger.debug("Using existing system (0% rollout)")
            return False

        # Percentage-based rollout with session hashing
        if session_id:
            # Hash session_id to get consistent assignment
            hash_value = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
            session_percentage = hash_value % 100

            use_unified = session_percentage < percentage

            logger.debug(
                f"Session rollout decision",
                extra={
                    "session_id": session_id,
                    "session_percentage": session_percentage,
                    "rollout_percentage": percentage,
                    "use_unified": use_unified
                }
            )

            return use_unified
        else:
            # No session_id - randomly assign based on percentage
            # (Not ideal for consistency, but fallback behavior)
            import random
            use_unified = random.randint(0, 99) < percentage

            logger.warning(
                f"Session rollout decision without session_id (inconsistent)",
                extra={
                    "rollout_percentage": percentage,
                    "use_unified": use_unified
                }
            )

            return use_unified

    def get_rollout_status(self) -> dict:
        """
        Get current rollout status.

        Returns:
            Dict with rollout configuration and status

        Example:
            rollout = UnifiedSystemRollout()
            status = rollout.get_rollout_status()
            print(f"Enabled: {status['enabled']}")
            print(f"Percentage: {status['percentage']}%")
        """
        return {
            "enabled": self.settings.UNIFIED_VARIANT_SYSTEM_ENABLED,
            "percentage": self.settings.UNIFIED_VARIANT_SYSTEM_PERCENTAGE,
            "registry_path": self.settings.VARIANT_REGISTRY_PATH,
            "mode": self._get_rollout_mode()
        }

    def _get_rollout_mode(self) -> str:
        """
        Get descriptive rollout mode.

        Returns:
            String describing current rollout mode
        """
        if not self.settings.UNIFIED_VARIANT_SYSTEM_ENABLED:
            return "disabled"
        elif self.settings.UNIFIED_VARIANT_SYSTEM_PERCENTAGE >= 100:
            return "full_rollout"
        elif self.settings.UNIFIED_VARIANT_SYSTEM_PERCENTAGE <= 0:
            return "disabled_by_percentage"
        else:
            return f"gradual_rollout_{self.settings.UNIFIED_VARIANT_SYSTEM_PERCENTAGE}pct"

    def log_system_decision(
        self,
        session_id: str,
        use_unified: bool,
        stage: str
    ):
        """
        Log which system was used for monitoring.

        Args:
            session_id: Session identifier
            use_unified: Whether unified system was used
            stage: Director stage (e.g., "GENERATE_STRAWMAN", "CONTENT_GENERATION")

        Example:
            rollout.log_system_decision(
                session_id="session_123",
                use_unified=True,
                stage="CONTENT_GENERATION"
            )
        """
        logger.info(
            f"System selection for {stage}",
            extra={
                "session_id": session_id,
                "system": "unified" if use_unified else "existing",
                "stage": stage,
                "rollout_percentage": self.settings.UNIFIED_VARIANT_SYSTEM_PERCENTAGE
            }
        )


# Global instance for easy access
_rollout_instance = None


def get_rollout_manager() -> UnifiedSystemRollout:
    """
    Get global rollout manager instance (singleton).

    Returns:
        UnifiedSystemRollout instance

    Example:
        from src.utils.unified_system_rollout import get_rollout_manager

        rollout = get_rollout_manager()
        if rollout.should_use_unified_system(session_id):
            ...
    """
    global _rollout_instance
    if _rollout_instance is None:
        _rollout_instance = UnifiedSystemRollout()
    return _rollout_instance


def should_use_unified_system(session_id: Optional[str] = None) -> bool:
    """
    Convenience function for rollout decision.

    Args:
        session_id: Session identifier

    Returns:
        True if should use unified system

    Example:
        from src.utils.unified_system_rollout import should_use_unified_system

        if should_use_unified_system(session_id):
            # Use DirectorIntegrationLayer
        else:
            # Use ServiceRouterV1_2
    """
    rollout = get_rollout_manager()
    return rollout.should_use_unified_system(session_id)
