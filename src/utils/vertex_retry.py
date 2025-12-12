"""
Vertex AI Retry Utility with Exponential Backoff

Handles 429 RESOURCE_EXHAUSTED errors from Google Vertex AI
by implementing exponential backoff retry logic.
"""

import asyncio
import logging
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def call_with_retry(
    func: Callable[[], T],
    max_retries: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    operation_name: str = "Vertex AI call"
) -> T:
    """
    Call async function with exponential backoff retry for 429 errors.

    Args:
        func: Async function to call (should be a lambda or callable)
        max_retries: Maximum number of retry attempts (default: 5)
        base_delay: Base delay in seconds (default: 2.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        operation_name: Description of operation for logging

    Returns:
        Result from successful function call

    Raises:
        Exception: If all retries exhausted or non-429 error occurs
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            # Attempt the operation
            result = await func()

            # Success - log if this was a retry
            if attempt > 0:
                logger.info(f"✅ {operation_name} succeeded after {attempt} retries")

            return result

        except Exception as e:
            last_exception = e
            error_str = str(e)

            # Check if this is a 429 error
            is_429_error = (
                "429" in error_str or
                "RESOURCE_EXHAUSTED" in error_str or
                "Quota exceeded" in error_str or
                "rate limit" in error_str.lower()
            )

            if is_429_error and attempt < max_retries - 1:
                # Calculate exponential backoff delay
                delay = min(base_delay * (2 ** attempt), max_delay)

                logger.warning(
                    f"⚠️  {operation_name} hit rate limit (attempt {attempt + 1}/{max_retries}). "
                    f"Retrying in {delay:.1f}s..."
                )

                await asyncio.sleep(delay)
                continue

            # Either not a 429 error, or we've exhausted retries
            if is_429_error:
                logger.error(
                    f"❌ {operation_name} failed after {max_retries} retry attempts due to rate limiting"
                )
            else:
                logger.error(f"❌ {operation_name} failed with non-retryable error: {error_str}")

            raise

    # This should never be reached, but just in case
    raise last_exception or Exception(f"{operation_name} failed after {max_retries} attempts")
