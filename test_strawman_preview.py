#!/usr/bin/env python3
"""
Generate Strawman and Create Preview URL

This script generates a strawman with content analysis and creates
a preview presentation that you can view in the browser.

Usage:
    python test_strawman_preview.py "Your Topic Here"
    python test_strawman_preview.py  # Uses default topic

Requirements:
    - Layout/Deck Builder Service running (default: http://localhost:8504)
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set feature flags for testing
os.environ["USE_TEXT_SERVICE_COORDINATION"] = "true"
os.environ["USE_LAYOUT_SERVICE_COORDINATION"] = "false"  # Set to true if Layout Service is running


async def generate_and_preview(topic: str):
    """Generate strawman and create preview URL."""

    print(f"\n{'='*60}")
    print(f"Generating Strawman Preview")
    print(f"{'='*60}")
    print(f"\nTopic: {topic}")

    # Import after setting env vars
    from src.agents.decision_engine import StrawmanGenerator
    from src.utils.strawman_transformer import StrawmanTransformer
    from src.utils.deck_builder_client import DeckBuilderClient
    from config.settings import get_settings

    settings = get_settings()

    # 1. Generate strawman with content analysis
    print("\n1. Generating strawman with content analysis...")
    generator = StrawmanGenerator()

    strawman = await generator.generate(
        topic=topic,
        audience="business professionals",
        duration=15,
        purpose="inform"
    )

    print(f"   Generated {len(strawman.slides)} slides")

    # 2. Print slides with story-driven analysis (v4.0.25)
    print("\n2. Slide Analysis (Story-Driven v4.0.25):")
    print("-" * 60)

    for slide in strawman.slides:
        # v4.0.25: Display story-driven fields
        slide_type = slide.slide_type_hint or ("hero" if slide.is_hero else "text")
        service = slide.service or "text"
        purpose = slide.purpose or "N/A"
        layout = slide.layout or "L25"

        if slide.is_hero:
            print(f"   [{slide.slide_number}] {slide_type.upper()} ({slide.hero_type}): {slide.title[:40]}")
            print(f"       → Layout: {layout} | Service: {service}")
            print(f"       → Purpose: {purpose}")
        else:
            print(f"   [{slide.slide_number}] {slide_type.upper()}: {slide.title[:40]}...")
            print(f"       → Layout: {layout} | Service: {service}")
            print(f"       → Purpose: {purpose}")

            if slide.variant_id:
                print(f"       → Variant: {slide.variant_id}")

            if slide.generation_instructions:
                instructions = slide.generation_instructions[:50]
                print(f"       → Instructions: {instructions}...")

            # Show topics if present
            if slide.topics and len(slide.topics) > 0:
                print(f"       → Topics: {len(slide.topics)} points")

    # 3. Transform and create preview
    print("\n3. Creating preview presentation...")

    transformer = StrawmanTransformer()
    deck_builder = DeckBuilderClient(
        api_url=settings.DECK_BUILDER_API_URL,
        timeout=settings.DECK_BUILDER_TIMEOUT
    )

    # Transform to deck-builder format
    strawman_dict = strawman.dict()
    api_payload = transformer.transform(strawman_dict, topic)

    print(f"   Deck Builder URL: {settings.DECK_BUILDER_API_URL}")

    try:
        # Create presentation
        response = await deck_builder.create_presentation(api_payload)

        if not response:
            print("   ERROR: Deck Builder returned empty response")
            print("   Is the Layout Service running?")
            return None

        url_path = response.get('url')
        presentation_id = response.get('id')

        if url_path:
            full_url = deck_builder.get_full_url(url_path)

            print(f"\n{'='*60}")
            print("SUCCESS!")
            print(f"{'='*60}")
            print(f"\nPresentation ID: {presentation_id}")
            print(f"\nPreview URL:")
            print(f"   {full_url}")
            print(f"\nOpen this URL in your browser to view the strawman.")

            return full_url
        else:
            print("   ERROR: No URL in response")
            print(f"   Response: {response}")
            return None

    except Exception as e:
        print(f"\n   ERROR: {type(e).__name__}: {e}")
        print(f"\n   Make sure the Layout/Deck Builder Service is running at:")
        print(f"   {settings.DECK_BUILDER_API_URL}")
        return None


async def main():
    # Get topic from command line or use default
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = "Artificial Intelligence in Modern Healthcare"

    url = await generate_and_preview(topic)

    if url:
        # Optionally open in browser
        print("\nWould you like to open in browser? (y/n): ", end="")
        try:
            response = input().strip().lower()
            if response == 'y':
                import webbrowser
                webbrowser.open(url)
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
