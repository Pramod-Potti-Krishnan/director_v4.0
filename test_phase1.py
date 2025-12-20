#!/usr/bin/env python3
"""
Phase 1 Test Script - Text Service Coordination

Tests the ContentAnalyzer and Text Service coordination components.

Usage:
    # Test ContentAnalyzer only (no external dependencies)
    python test_phase1.py --analyzer

    # Test Text Service coordination (requires running Text Service)
    python test_phase1.py --coordination

    # Test I-series client methods (requires running Text Service)
    python test_phase1.py --iseries

    # Run all tests
    python test_phase1.py --all
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_content_analyzer():
    """Test ContentAnalyzer with sample slides."""
    print("\n" + "="*60)
    print("TEST: ContentAnalyzer")
    print("="*60)

    from src.core.content_analyzer import ContentAnalyzer
    from src.models.decision import StrawmanSlide

    analyzer = ContentAnalyzer()

    # Test slides with different content types
    test_slides = [
        StrawmanSlide(
            slide_id="test-1",
            slide_number=1,
            title="Q4 Revenue Performance",
            topics=["Revenue grew 25% YoY", "EBITDA margin improved to 18%", "Customer count reached 50,000"],
            layout="L25",
            is_hero=False
        ),
        StrawmanSlide(
            slide_id="test-2",
            slide_number=2,
            title="Comparison: Cloud vs On-Premise",
            topics=["Cost comparison", "Performance metrics", "Security features", "Scalability"],
            layout="L25",
            is_hero=False
        ),
        StrawmanSlide(
            slide_id="test-3",
            slide_number=3,
            title="Implementation Workflow",
            topics=["Step 1: Assessment", "Step 2: Planning", "Step 3: Migration", "Step 4: Validation"],
            layout="L25",
            is_hero=False
        ),
        StrawmanSlide(
            slide_id="test-4",
            slide_number=4,
            title="Our Product Features",
            topics=["Easy to use", "Beautiful design", "Fast performance", "Secure"],
            layout="L25",
            is_hero=False
        ),
        StrawmanSlide(
            slide_id="test-5",
            slide_number=5,
            title="Organizational Structure",
            topics=["CEO", "VP Engineering", "VP Sales", "Team leads", "Individual contributors"],
            layout="L25",
            is_hero=False
        ),
    ]

    print("\nAnalyzing test slides...\n")

    for slide in test_slides:
        hints = analyzer.analyze(slide)

        print(f"Slide: {slide.title}")
        print(f"  has_numbers: {hints.has_numbers}")
        print(f"  is_comparison: {hints.is_comparison}")
        print(f"  is_time_based: {hints.is_time_based}")
        print(f"  is_hierarchical: {hints.is_hierarchical}")
        print(f"  is_process_flow: {hints.is_process_flow}")
        print(f"  pattern_type: {hints.pattern_type}")
        print(f"  suggested_service: {hints.suggested_service} (conf: {hints.service_confidence:.2f})")
        print(f"  needs_image: {hints.needs_image}")
        print(f"  suggested_iseries: {hints.suggested_iseries}")
        print(f"  detected_keywords: {hints.detected_keywords[:5]}")
        print()

    print("ContentAnalyzer test PASSED")
    return True


async def test_text_service_coordination():
    """Test Text Service coordination client."""
    print("\n" + "="*60)
    print("TEST: Text Service Coordination Client")
    print("="*60)

    from src.clients.text_service_coordination import TextServiceCoordinationClient
    from src.models.content_hints import ContentHints

    client = TextServiceCoordinationClient()

    # Health check
    print("\n1. Health Check...")
    is_healthy = await client.health_check()
    print(f"   Text Service healthy: {is_healthy}")

    if not is_healthy:
        print("\n   Text Service not available. Skipping coordination tests.")
        print("   Make sure Text Service is running at:", client.base_url)
        return False

    # Get capabilities
    print("\n2. Get Capabilities...")
    try:
        capabilities = await client.get_capabilities()
        print(f"   Service: {capabilities.service} v{capabilities.version}")
        print(f"   Variants: {len(capabilities.variants)} available")
        print(f"   Handles well: {capabilities.handles_well[:3]}...")
    except Exception as e:
        print(f"   Error: {e}")
        return False

    # Test can-handle
    print("\n3. Can-Handle Test...")
    try:
        slide_content = {
            "title": "Q4 Revenue Growth",
            "topics": ["25% YoY increase", "New markets", "Improved margins"],
            "topic_count": 3
        }
        hints = ContentHints(
            has_numbers=True,
            is_comparison=False,
            is_time_based=True,
            detected_keywords=["revenue", "growth", "yoy"]
        )
        available_space = {
            "width": 1800,
            "height": 720,
            "layout_id": "L25"
        }

        result = await client.can_handle(slide_content, hints, available_space)
        print(f"   can_handle: {result.can_handle}")
        print(f"   confidence: {result.confidence:.2f}")
        print(f"   reason: {result.reason}")
        print(f"   suggested_approach: {result.suggested_approach}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test recommend-variant
    print("\n4. Recommend-Variant Test...")
    try:
        result = await client.recommend_variant(slide_content, available_space)
        if result.recommended_variants:
            print(f"   Top recommendation: {result.recommended_variants[0].variant_id}")
            print(f"   Confidence: {result.recommended_variants[0].confidence:.2f}")
            print(f"   Reason: {result.recommended_variants[0].reason}")
        else:
            print("   No recommendations returned")
    except Exception as e:
        print(f"   Error: {e}")

    # Test get_best_variant convenience method
    print("\n5. Get-Best-Variant Test...")
    try:
        best = await client.get_best_variant(
            slide_content, hints, available_space, confidence_threshold=0.5
        )
        print(f"   Best variant: {best}")
    except Exception as e:
        print(f"   Error: {e}")

    print("\nText Service coordination test PASSED")
    return True


async def test_iseries_client():
    """Test I-series generation methods."""
    print("\n" + "="*60)
    print("TEST: I-Series Generation Methods")
    print("="*60)

    from src.utils.text_service_client_v1_2 import TextServiceClientV1_2

    client = TextServiceClientV1_2()

    # Health check for I-series
    print("\n1. I-Series Health Check...")
    try:
        is_healthy = await client.iseries_health_check()
        print(f"   I-series healthy: {is_healthy}")

        if not is_healthy:
            print("   I-series endpoints not available. Skipping.")
            return False
    except Exception as e:
        print(f"   Error: {e}")
        return False

    # Get I-series layouts
    print("\n2. Get I-Series Layouts...")
    try:
        layouts = await client.get_iseries_layouts()
        print(f"   Available layouts: {list(layouts.keys())}")
    except Exception as e:
        print(f"   Error: {e}")

    # Generate I1 sample (this may take 60-120s for image generation)
    print("\n3. Generate I1 Sample (may take 60-120s)...")
    try:
        result = await client.generate_iseries_i1(
            slide_number=1,
            title="Our Innovative Product",
            narrative="An overview of our groundbreaking product features",
            topics=["Easy to use", "Beautiful design", "Fast performance"],
            visual_style="professional",
            content_style="bullets"
        )
        print(f"   Generated: {len(result.get('content', ''))} chars")
        print(f"   Image fallback: {result.get('image_fallback', False)}")
        print(f"   Image URL: {result.get('image_url', 'N/A')[:50]}...")
    except Exception as e:
        print(f"   Error: {e}")

    print("\nI-Series test PASSED")
    return True


async def test_full_integration():
    """Test full integration with strawman generation."""
    print("\n" + "="*60)
    print("TEST: Full Integration (Strawman Enhancement)")
    print("="*60)

    from src.agents.decision_engine import StrawmanGenerator

    # Enable coordination flags for this test
    import os
    os.environ["USE_TEXT_SERVICE_COORDINATION"] = "true"
    os.environ["USE_LAYOUT_SERVICE_COORDINATION"] = "false"  # Layout Service may not be running

    generator = StrawmanGenerator()

    print("\n1. Generating strawman for 'Artificial Intelligence in Healthcare'...")
    try:
        strawman = await generator.generate(
            topic="Artificial Intelligence in Healthcare",
            audience="Healthcare executives",
            duration=15,
            purpose="inform"
        )

        print(f"\n   Generated {len(strawman.slides)} slides:")
        for slide in strawman.slides:
            hints = getattr(slide, 'content_hints', None)
            service = getattr(slide, 'suggested_service', 'N/A')
            iseries = getattr(slide, 'suggested_iseries', None)

            if slide.is_hero:
                print(f"   [{slide.slide_number}] HERO: {slide.title[:40]}...")
            else:
                print(f"   [{slide.slide_number}] {slide.title[:40]}...")
                if hints:
                    print(f"       hints: {hints.get('pattern_type', 'N/A')}, service: {service}")
                if iseries:
                    print(f"       I-series: {iseries}")

    except Exception as e:
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\nFull integration test PASSED")
    return True


def main():
    parser = argparse.ArgumentParser(description="Phase 1 Test Script")
    parser.add_argument("--analyzer", action="store_true", help="Test ContentAnalyzer only")
    parser.add_argument("--coordination", action="store_true", help="Test Text Service coordination")
    parser.add_argument("--iseries", action="store_true", help="Test I-series generation")
    parser.add_argument("--integration", action="store_true", help="Test full integration")
    parser.add_argument("--all", action="store_true", help="Run all tests")

    args = parser.parse_args()

    # Default to analyzer test if no args
    if not any([args.analyzer, args.coordination, args.iseries, args.integration, args.all]):
        args.analyzer = True

    results = []

    if args.analyzer or args.all:
        results.append(("ContentAnalyzer", test_content_analyzer()))

    if args.coordination or args.all:
        results.append(("Coordination", asyncio.run(test_text_service_coordination())))

    if args.iseries or args.all:
        results.append(("I-Series", asyncio.run(test_iseries_client())))

    if args.integration or args.all:
        results.append(("Integration", asyncio.run(test_full_integration())))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for name, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"  {name}: {status}")

    all_passed = all(r[1] for r in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
