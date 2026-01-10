"""
Session Cleanup Utility for Director Agent v4.10

Cleans up orphaned blank presentation sessions that were never used.

v4.10: Implements OPERATING_MODEL_BUILDER_V2 Phase 4 - Session Cleanup.

Targets sessions where:
- has_blank_presentation = True (created with blank on connect)
- has_topic = False (user never provided a topic)
- created_at < (now - SESSION_CLEANUP_HOURS)

Usage:
    # As module
    from src.utils.session_cleanup import cleanup_orphaned_sessions
    deleted = await cleanup_orphaned_sessions()

    # As CLI (for scheduled jobs)
    python -m src.utils.session_cleanup

Author: Director v4.10
Date: January 2026
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from src.storage.supabase import get_supabase_client
from src.utils.logger import setup_logger
from config.settings import get_settings

logger = setup_logger(__name__)


async def cleanup_orphaned_sessions(
    max_age_hours: Optional[int] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Clean up orphaned blank presentation sessions.

    Finds and deletes sessions that:
    - Started with blank presentation (has_blank_presentation=True)
    - Never received a topic (has_topic=False)
    - Are older than max_age_hours

    Args:
        max_age_hours: Max age in hours before cleanup. Defaults to SESSION_CLEANUP_HOURS setting.
        dry_run: If True, only report what would be deleted without actually deleting.

    Returns:
        {
            "success": bool,
            "sessions_found": int,
            "sessions_deleted": int,
            "dry_run": bool,
            "cutoff_time": str,
            "errors": List[str]
        }
    """
    settings = get_settings()
    max_age = max_age_hours or settings.SESSION_CLEANUP_HOURS

    cutoff_time = datetime.utcnow() - timedelta(hours=max_age)
    cutoff_iso = cutoff_time.isoformat()

    logger.info(f"[Cleanup] Starting orphaned session cleanup (max_age={max_age}h, dry_run={dry_run})")
    logger.info(f"[Cleanup] Cutoff time: {cutoff_iso}")

    result = {
        "success": False,
        "sessions_found": 0,
        "sessions_deleted": 0,
        "dry_run": dry_run,
        "cutoff_time": cutoff_iso,
        "errors": []
    }

    try:
        supabase = await get_supabase_client()

        # Find orphaned sessions
        # Query: has_blank_presentation=True AND has_topic=False AND created_at < cutoff
        query = supabase.table("dr_sessions_v4").select("id, user_id, created_at, blank_presentation_id")
        query = query.eq("has_blank_presentation", True)
        query = query.eq("has_topic", False)
        query = query.lt("created_at", cutoff_iso)

        response = await query.execute()

        if not response.data:
            logger.info("[Cleanup] No orphaned sessions found")
            result["success"] = True
            return result

        orphaned_sessions = response.data
        result["sessions_found"] = len(orphaned_sessions)

        logger.info(f"[Cleanup] Found {len(orphaned_sessions)} orphaned sessions")

        if dry_run:
            logger.info("[Cleanup] DRY RUN - No sessions will be deleted")
            for session in orphaned_sessions:
                logger.info(f"[Cleanup] Would delete: id={session['id']}, created={session['created_at']}")
            result["success"] = True
            return result

        # Delete orphaned sessions
        deleted_count = 0
        for session in orphaned_sessions:
            session_id = session["id"]
            try:
                # Delete the session
                delete_response = await supabase.table("dr_sessions_v4").delete().eq("id", session_id).execute()

                if delete_response.data:
                    deleted_count += 1
                    logger.debug(f"[Cleanup] Deleted session: {session_id}")

                    # Optionally: Also delete the blank presentation from deck-builder
                    # This would require calling deck-builder's delete endpoint
                    # For now, we only clean up the session record

            except Exception as e:
                error_msg = f"Failed to delete session {session_id}: {str(e)}"
                logger.error(f"[Cleanup] {error_msg}")
                result["errors"].append(error_msg)

        result["sessions_deleted"] = deleted_count
        result["success"] = len(result["errors"]) == 0

        logger.info(f"[Cleanup] Completed: deleted {deleted_count}/{len(orphaned_sessions)} sessions")

    except Exception as e:
        error_msg = f"Cleanup failed: {str(e)}"
        logger.error(f"[Cleanup] {error_msg}")
        result["errors"].append(error_msg)

    return result


async def get_orphaned_session_stats() -> Dict[str, Any]:
    """
    Get statistics about orphaned sessions without deleting.

    Returns:
        {
            "total_orphaned": int,
            "by_age": {
                "1h": int,
                "6h": int,
                "24h": int,
                "older": int
            }
        }
    """
    try:
        supabase = await get_supabase_client()
        now = datetime.utcnow()

        # Get all orphaned sessions
        query = supabase.table("dr_sessions_v4").select("id, created_at")
        query = query.eq("has_blank_presentation", True)
        query = query.eq("has_topic", False)

        response = await query.execute()

        if not response.data:
            return {"total_orphaned": 0, "by_age": {"1h": 0, "6h": 0, "24h": 0, "older": 0}}

        sessions = response.data
        by_age = {"1h": 0, "6h": 0, "24h": 0, "older": 0}

        for session in sessions:
            created_str = session.get("created_at", "")
            if created_str:
                created = datetime.fromisoformat(created_str.replace("Z", "+00:00")).replace(tzinfo=None)
                age = now - created
                age_hours = age.total_seconds() / 3600

                if age_hours < 1:
                    by_age["1h"] += 1
                elif age_hours < 6:
                    by_age["6h"] += 1
                elif age_hours < 24:
                    by_age["24h"] += 1
                else:
                    by_age["older"] += 1

        return {
            "total_orphaned": len(sessions),
            "by_age": by_age
        }

    except Exception as e:
        logger.error(f"[Cleanup] Failed to get stats: {e}")
        return {"error": str(e)}


def run_cleanup():
    """CLI entry point for running cleanup as a scheduled job."""
    import argparse

    parser = argparse.ArgumentParser(description="Clean up orphaned blank presentation sessions")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    parser.add_argument("--max-age", type=int, help="Max age in hours (default: from settings)")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")
    args = parser.parse_args()

    async def main():
        if args.stats:
            stats = await get_orphaned_session_stats()
            print(f"\nOrphaned Session Statistics:")
            print(f"  Total: {stats.get('total_orphaned', 0)}")
            print(f"  By age:")
            by_age = stats.get("by_age", {})
            print(f"    < 1 hour:  {by_age.get('1h', 0)}")
            print(f"    1-6 hours: {by_age.get('6h', 0)}")
            print(f"    6-24 hours: {by_age.get('24h', 0)}")
            print(f"    > 24 hours: {by_age.get('older', 0)}")
        else:
            result = await cleanup_orphaned_sessions(
                max_age_hours=args.max_age,
                dry_run=args.dry_run
            )
            print(f"\nCleanup Result:")
            print(f"  Success: {result['success']}")
            print(f"  Sessions found: {result['sessions_found']}")
            print(f"  Sessions deleted: {result['sessions_deleted']}")
            print(f"  Dry run: {result['dry_run']}")
            if result['errors']:
                print(f"  Errors: {result['errors']}")

    asyncio.run(main())


if __name__ == "__main__":
    run_cleanup()
