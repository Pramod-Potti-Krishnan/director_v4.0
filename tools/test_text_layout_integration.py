#!/usr/bin/env python3
"""
Text Service + Layout Service Integration Test

Complete flow:
1. L29 Title Slide: Text Service generates FULL content (/v1.2/hero/title)
2. L25 Content Slides: Text Service generates MAIN CONTENT (/v1.2/generate)
3. Layout Service: Stitches all slides into a presentation and returns URL

Output: Presentation URL for visual validation

Usage:
    python tools/test_text_layout_integration.py
"""

import asyncio
import httpx
import json
from datetime import datetime

# Service URLs
TEXT_SERVICE_URL = "https://web-production-5daf.up.railway.app"
LAYOUT_SERVICE_URL = "https://web-production-f0d13.up.railway.app"

# Presentation theme
PRESENTATION = {
    "title": "The Story of Hanuman",
    "subtitle": "A Journey of Devotion, Strength, and Wisdom",
    "presenter": "Mythological Stories | For Kids",
    "audience": "children aged 6-12",
    "theme": "kids",
    "visual_style": "kids"
}

# Slide definitions
SLIDES = [
    # Slide 1: L29 Title Slide (Hero)
    {
        "layout": "L29",
        "type": "title_slide",
        "endpoint": "/v1.2/hero/title",
        "narrative": "Introduce the epic story of Hanuman, the mighty monkey god",
        "topics": ["Hanuman", "Ramayana", "Hindu Mythology", "Adventure"],
    },
    # Slide 2: L25 Content - Grid 2x2
    {
        "layout": "L25",
        "type": "content",
        "variant_id": "grid_2x2_centered",
        "slide_title": "Who is Hanuman?",
        "subtitle": "The greatest devotee of Lord Rama",
        "slide_purpose": "Introduce Hanuman's key qualities",
        "key_message": "Hanuman represents devotion, strength, and humility",
        "target_points": [
            "Son of the Wind God Vayu",
            "Blessed with incredible strength",
            "Devoted follower of Lord Rama",
            "Master of shape-shifting"
        ],
    },
    # Slide 3: L25 Content - Sequential 4 steps
    {
        "layout": "L25",
        "type": "content",
        "variant_id": "sequential_4col",
        "slide_title": "Hanuman's Greatest Adventures",
        "subtitle": "From birth to becoming a hero",
        "slide_purpose": "Show Hanuman's journey through key adventures",
        "key_message": "Each adventure teaches valuable lessons",
        "target_points": [
            "Flying to the Sun - Curiosity and Bravery",
            "Meeting Lord Rama - Finding Purpose",
            "Leaping to Lanka - Courage and Determination",
            "Bringing the Mountain - Never Giving Up"
        ],
    },
    # Slide 4: L25 Content - Comparison 2col
    {
        "layout": "L25",
        "type": "content",
        "variant_id": "comparison_2col",
        "slide_title": "Hanuman's Superpowers",
        "subtitle": "Physical strength meets spiritual wisdom",
        "slide_purpose": "Compare physical and spiritual abilities",
        "key_message": "True strength comes from within",
        "target_points": [
            "Physical Powers: Super strength, Flight, Size-changing",
            "Spiritual Powers: Devotion, Wisdom, Humility"
        ],
    },
    # Slide 5: L25 Content - Grid 2x3 numbered
    {
        "layout": "L25",
        "type": "content",
        "variant_id": "grid_2x3_numbered",
        "slide_title": "Lessons from Hanuman",
        "subtitle": "Values we can learn from the mighty hero",
        "slide_purpose": "Share life lessons from Hanuman's story",
        "key_message": "Hanuman teaches us how to be better people",
        "target_points": [
            "Be Devoted - Stay loyal to those you love",
            "Be Brave - Face your fears with courage",
            "Be Humble - Great power needs great humility",
            "Be Helpful - Use your strength to help others",
            "Be Patient - Good things take time",
            "Be Faithful - Believe in yourself and others"
        ],
    },
]


async def generate_l29_title_slide(client: httpx.AsyncClient, slide_def: dict) -> dict:
    """Generate L29 title slide via hero endpoint."""

    request = {
        "slide_number": 1,
        "slide_type": "title_slide",
        "narrative": slide_def["narrative"],
        "topics": slide_def["topics"],
        "visual_style": PRESENTATION["visual_style"],
        "context": {
            "theme": PRESENTATION["theme"],
            "audience": PRESENTATION["audience"],
            "presentation_title": PRESENTATION["title"],
            "presenter": PRESENTATION["presenter"]
        }
    }

    endpoint = f"{TEXT_SERVICE_URL}{slide_def['endpoint']}"
    print(f"    Calling: {endpoint}")

    response = await client.post(endpoint, json=request)
    response.raise_for_status()

    result = response.json()

    # Format for Layout Service: L29 uses hero_content
    return {
        "layout": "L29",
        "content": {
            "hero_content": result.get("content", "")
        }
    }


async def generate_l25_content_slide(
    client: httpx.AsyncClient,
    slide_def: dict,
    slide_number: int
) -> dict:
    """Generate L25 content slide via v1.2/generate endpoint."""

    request = {
        "variant_id": slide_def["variant_id"],
        "slide_spec": {
            "slide_title": slide_def["slide_title"],
            "slide_purpose": slide_def["slide_purpose"],
            "key_message": slide_def["key_message"],
            "target_points": slide_def["target_points"],
            "tone": "fun and engaging",
            "audience": PRESENTATION["audience"]
        },
        "presentation_spec": {
            "presentation_title": PRESENTATION["title"],
            "presentation_type": "educational storytelling",
            "current_slide_number": slide_number,
            "total_slides": len(SLIDES)
        },
        "enable_parallel": True,
        "validate_character_counts": False
    }

    endpoint = f"{TEXT_SERVICE_URL}/v1.2/generate"
    print(f"    Calling: {endpoint} (variant: {slide_def['variant_id']})")

    response = await client.post(endpoint, json=request)
    response.raise_for_status()

    result = response.json()

    # Format for Layout Service: L25 uses slide_title, subtitle, rich_content
    return {
        "layout": "L25",
        "content": {
            "slide_title": slide_def["slide_title"],
            "subtitle": slide_def["subtitle"],
            "rich_content": result.get("html", "")
        }
    }


async def create_presentation(client: httpx.AsyncClient, slides: list) -> dict:
    """Send slides to Layout Service to create presentation."""

    presentation_payload = {
        "title": PRESENTATION["title"],
        "slides": slides
    }

    endpoint = f"{LAYOUT_SERVICE_URL}/api/presentations"
    print(f"\n  Sending to Layout Service: {endpoint}")
    print(f"  Payload: {len(slides)} slides")

    response = await client.post(endpoint, json=presentation_payload)
    response.raise_for_status()

    return response.json()


async def main():
    """Main test function."""

    print("=" * 70)
    print("Text Service + Layout Service Integration Test")
    print("=" * 70)
    print(f"Text Service:   {TEXT_SERVICE_URL}")
    print(f"Layout Service: {LAYOUT_SERVICE_URL}")
    print(f"Presentation:   {PRESENTATION['title']}")
    print(f"Total Slides:   {len(SLIDES)} (1 L29 + {len(SLIDES)-1} L25)")
    print("-" * 70)

    layout_slides = []

    async with httpx.AsyncClient(timeout=120.0) as client:

        # Step 1: Generate all slides from Text Service
        print("\n[STEP 1] Generating slides from Text Service...")

        for i, slide_def in enumerate(SLIDES, 1):
            print(f"\n  [{i}/{len(SLIDES)}] Generating {slide_def['layout']} slide...")

            try:
                if slide_def["layout"] == "L29":
                    slide_data = await generate_l29_title_slide(client, slide_def)
                else:
                    slide_data = await generate_l25_content_slide(client, slide_def, i)

                layout_slides.append(slide_data)

                content_field = "hero_content" if slide_def["layout"] == "L29" else "rich_content"
                html_len = len(slide_data["content"].get(content_field, ""))
                print(f"    ✓ Success! HTML length: {html_len} chars")

            except httpx.HTTPStatusError as e:
                print(f"    ✗ HTTP Error: {e.response.status_code}")
                print(f"      Response: {e.response.text[:300]}")
                # Add placeholder slide
                if slide_def["layout"] == "L29":
                    layout_slides.append({
                        "layout": "L29",
                        "content": {"hero_content": f"<div style='text-align:center;padding:100px;'><h1>Error generating slide</h1></div>"}
                    })
                else:
                    layout_slides.append({
                        "layout": "L25",
                        "content": {
                            "slide_title": slide_def.get("slide_title", f"Slide {i}"),
                            "subtitle": slide_def.get("subtitle", ""),
                            "rich_content": f"<p style='color:red'>Error: {e.response.status_code}</p>"
                        }
                    })

            except Exception as e:
                print(f"    ✗ Error: {type(e).__name__}: {e}")
                # Add placeholder
                if slide_def["layout"] == "L29":
                    layout_slides.append({
                        "layout": "L29",
                        "content": {"hero_content": f"<div><h1>Error</h1><p>{e}</p></div>"}
                    })
                else:
                    layout_slides.append({
                        "layout": "L25",
                        "content": {
                            "slide_title": slide_def.get("slide_title", f"Slide {i}"),
                            "subtitle": "",
                            "rich_content": f"<p style='color:red'>Error: {e}</p>"
                        }
                    })

        # Step 2: Send slides to Layout Service
        print("\n" + "-" * 70)
        print("[STEP 2] Creating presentation in Layout Service...")

        try:
            result = await create_presentation(client, layout_slides)

            presentation_id = result.get("id", "unknown")
            presentation_url = result.get("url", f"{LAYOUT_SERVICE_URL}/p/{presentation_id}")

            print("\n" + "=" * 70)
            print("SUCCESS!")
            print("=" * 70)
            print(f"  Presentation ID: {presentation_id}")
            print(f"  Presentation URL: {presentation_url}")
            print("=" * 70)

            # Also print the full URL for easy access
            print(f"\n  Open in browser:")
            print(f"  {presentation_url}")
            print()

        except httpx.HTTPStatusError as e:
            print(f"\n  ✗ Layout Service Error: {e.response.status_code}")
            print(f"    Response: {e.response.text[:500]}")

        except Exception as e:
            print(f"\n  ✗ Error creating presentation: {type(e).__name__}: {e}")

    # Summary
    print("\n" + "-" * 70)
    print("SLIDES GENERATED:")
    print("-" * 70)
    for i, slide in enumerate(layout_slides, 1):
        layout = slide["layout"]
        if layout == "L29":
            html_len = len(slide["content"].get("hero_content", ""))
            title = "Hero Title Slide"
        else:
            html_len = len(slide["content"].get("rich_content", ""))
            title = slide["content"].get("slide_title", "Untitled")

        status = "✓" if html_len > 100 else "⚠"
        print(f"  {status} Slide {i}: {layout} - {title} ({html_len} chars)")

    print("-" * 70)


if __name__ == "__main__":
    asyncio.run(main())
