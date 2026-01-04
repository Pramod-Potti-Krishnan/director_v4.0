#!/usr/bin/env python3
"""
Cron job entry point for session cleanup.

This script is designed to run as a Railway cron service.
It executes the cleanup, prints results, and exits.

Usage (Railway cron service):
    python cleanup_cron.py

Cron schedule recommendation: 0 */6 * * * (every 6 hours)
"""

import asyncio
import sys
from datetime import datetime


async def main():
    print(f"\n{'='*60}")
    print(f"Session Cleanup Job - {datetime.utcnow().isoformat()}Z")
    print(f"{'='*60}\n")

    try:
        from src.utils.session_cleanup import cleanup_orphaned_sessions, get_orphaned_session_stats

        # Get stats first
        print("Checking orphaned sessions...")
        stats = await get_orphaned_session_stats()
        print(f"  Total orphaned: {stats.get('total_orphaned', 0)}")
        by_age = stats.get('by_age', {})
        print(f"  By age: <1h={by_age.get('1h', 0)}, 1-6h={by_age.get('6h', 0)}, "
              f"6-24h={by_age.get('24h', 0)}, >24h={by_age.get('older', 0)}")

        # Run cleanup
        print("\nRunning cleanup...")
        result = await cleanup_orphaned_sessions(dry_run=False)

        print(f"\nCleanup Result:")
        print(f"  Success: {result['success']}")
        print(f"  Sessions found: {result['sessions_found']}")
        print(f"  Sessions deleted: {result['sessions_deleted']}")
        print(f"  Cutoff time: {result['cutoff_time']}")

        if result['errors']:
            print(f"  Errors: {result['errors']}")
            sys.exit(1)

        print(f"\n{'='*60}")
        print("Cleanup completed successfully")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
