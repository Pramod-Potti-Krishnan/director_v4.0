#!/usr/bin/env python3
"""
Direct Text Service v1.2 Test

Calls Text Service directly to diagnose if the issue is:
1. Text Service returning errors
2. Text Service returning null
3. Text Service working but Director not using it correctly

Usage:
    python tools/test_text_service.py
"""

import asyncio
import httpx
import json
import sys

TEXT_SERVICE_URL = "https://web-production-5daf.up.railway.app"

async def test_text_service():
    """Test Text Service v1.2 directly."""

    # Sample request matching what Director ACTUALLY sends
    # Director sends topics as List[str], not as objects!
    request = {
        "variant_id": "grid_2x2_centered",
        "slide_spec": {
            "slide_title": "Why Hanuman is Amazing",
            "slide_purpose": "Introduce key qualities of Hanuman",
            "key_message": "Devotion to Ram | Incredible Strength | Humble Nature",
            "target_points": [
                "Devotion to Ram",
                "Incredible Strength",
                "Humble Nature",
                "Courage"
            ],
            "tone": "inspiring",
            "audience": "kids"
        },
        "presentation_spec": {
            "presentation_title": "The Story of Hanuman",
            "presentation_type": "educational",
            "current_slide_number": 2,
            "total_slides": 5
        },
        "enable_parallel": True,
        "validate_character_counts": False
    }

    endpoint = f"{TEXT_SERVICE_URL}/v1.2/generate"

    print("=" * 60)
    print("Direct Text Service v1.2 Test")
    print("=" * 60)
    print(f"Endpoint: {endpoint}")
    print(f"Variant: {request['variant_id']}")
    print("-" * 60)
    print("Request:")
    print(json.dumps(request, indent=2)[:500] + "...")
    print("-" * 60)

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print("Sending request...")
            response = await client.post(endpoint, json=request)

            print(f"\nHTTP Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Content-Length: {response.headers.get('content-length')}")
            print("-" * 60)

            # Get raw response
            raw_body = response.text
            print(f"Raw Response ({len(raw_body)} chars):")
            print(raw_body[:1000])
            if len(raw_body) > 1000:
                print(f"... (truncated, {len(raw_body) - 1000} more chars)")
            print("-" * 60)

            # Try to parse JSON
            try:
                result = response.json()

                if result is None:
                    print("⚠️ RESULT IS NULL!")
                    return

                print(f"Parsed Result Type: {type(result).__name__}")

                if isinstance(result, dict):
                    print(f"Keys: {list(result.keys())}")
                    print(f"success: {result.get('success')}")

                    html = result.get('html', '')
                    print(f"HTML length: {len(html)} chars")

                    if html:
                        print("\nHTML Preview (first 500 chars):")
                        print(html[:500])
                    else:
                        print("⚠️ HTML IS EMPTY!")

                    # Check for errors
                    if 'detail' in result:
                        print(f"\n❌ ERROR DETAIL: {result['detail']}")

            except json.JSONDecodeError as e:
                print(f"❌ JSON Parse Error: {e}")

    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text[:500]}")

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_text_service())
