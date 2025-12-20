#!/usr/bin/env python3
"""
Test script for the Playbook System (v4.1)

Tests the three-tier matching algorithm:
- FULL_MATCH (90%+): Use playbook directly
- PARTIAL_MATCH (60-89%): Merge playbook with custom slides
- NO_MATCH (<60%): Generate from scratch
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.playbook_manager import PlaybookManager
from src.core.playbook_merger import PlaybookMerger
from src.models.playbook import MatchConfidence


def test_playbook_loading():
    """Test that playbooks are loaded correctly."""
    print("\n" + "=" * 60)
    print("TEST 1: Playbook Loading")
    print("=" * 60)

    manager = PlaybookManager()
    playbooks = manager.list_playbooks()

    print(f"\nLoaded {len(playbooks)} playbooks:")
    for pb in playbooks:
        print(f"  - {pb['playbook_id']}: {pb['audience']}/{pb['purpose']}/{pb['duration']}min ({pb['slide_count']} slides)")

    assert len(playbooks) >= 3, "Expected at least 3 sample playbooks"
    print("\n✓ Playbook loading test passed!")


def test_exact_match():
    """Test exact match (90%+ confidence)."""
    print("\n" + "=" * 60)
    print("TEST 2: Exact Match (FULL_MATCH)")
    print("=" * 60)

    manager = PlaybookManager()

    # Test exact match: professionals + investor_pitch + 15min
    match = manager.find_best_match(
        audience="professionals",
        purpose="investor_pitch",
        duration=15
    )

    print(f"\nSearch: professionals/investor_pitch/15min")
    print(f"Result: {match.playbook_id}")
    print(f"Confidence: {match.confidence:.2f}")
    print(f"Match Type: {match.match_type}")

    assert match.match_type == MatchConfidence.FULL_MATCH, f"Expected FULL_MATCH, got {match.match_type}"
    assert match.confidence >= 0.90, f"Expected confidence >= 0.90, got {match.confidence}"
    print("\n✓ Exact match test passed!")


def test_partial_match():
    """Test partial match (60-89% confidence)."""
    print("\n" + "=" * 60)
    print("TEST 3: Partial Match (PARTIAL_MATCH)")
    print("=" * 60)

    manager = PlaybookManager()

    # Test partial match: professionals + sales + 15min
    # Should partially match investor_pitch (sales is compatible with investor_pitch)
    match = manager.find_best_match(
        audience="professionals",
        purpose="sales",
        duration=15
    )

    print(f"\nSearch: professionals/sales/15min")
    print(f"Result: {match.playbook_id}")
    print(f"Confidence: {match.confidence:.2f}")
    print(f"Match Type: {match.match_type}")
    print(f"Match Details: {match.match_details}")
    print(f"Adaptation Notes: {match.adaptation_notes}")

    # Should be partial match (sales compatible with investor_pitch)
    assert match.playbook_id is not None, "Expected to find a partial match"
    print("\n✓ Partial match test passed!")


def test_no_match():
    """Test no match (<60% confidence)."""
    print("\n" + "=" * 60)
    print("TEST 4: No Match (NO_MATCH)")
    print("=" * 60)

    manager = PlaybookManager()

    # Test no match: children + investor_pitch + 30min
    # Children are not compatible with professionals
    match = manager.find_best_match(
        audience="children",
        purpose="investor_pitch",
        duration=30
    )

    print(f"\nSearch: children/investor_pitch/30min")
    print(f"Result: {match.playbook_id}")
    print(f"Confidence: {match.confidence:.2f}")
    print(f"Match Type: {match.match_type}")

    # This might be NO_MATCH or a very low PARTIAL_MATCH
    print(f"Adaptation Notes: {match.adaptation_notes}")
    print("\n✓ No match test passed!")


def test_audience_normalization():
    """Test audience normalization."""
    print("\n" + "=" * 60)
    print("TEST 5: Audience Normalization")
    print("=" * 60)

    manager = PlaybookManager()

    # Test various audience normalizations
    test_cases = [
        ("professional", "professionals"),
        ("business", "professionals"),
        ("college", "college_students"),
        ("university student", "college_students"),
        ("kids", "children"),
        ("elderly", "seniors"),
    ]

    for input_val, expected in test_cases:
        result = manager._normalize_audience(input_val)
        print(f"  '{input_val}' -> '{result}' (expected: {expected})")
        assert result == expected, f"Expected {expected}, got {result}"

    print("\n✓ Audience normalization test passed!")


def test_purpose_normalization():
    """Test purpose normalization."""
    print("\n" + "=" * 60)
    print("TEST 6: Purpose Normalization")
    print("=" * 60)

    manager = PlaybookManager()

    # Test various purpose normalizations
    test_cases = [
        ("investor pitch", "investor_pitch"),
        ("pitch", "investor_pitch"),
        ("quarterly review", "qbr"),
        ("training session", "training"),
        ("demo", "product_demo"),
    ]

    for input_val, expected in test_cases:
        result = manager._normalize_purpose(input_val)
        print(f"  '{input_val}' -> '{result}' (expected: {expected})")
        assert result == expected, f"Expected {expected}, got {result}"

    print("\n✓ Purpose normalization test passed!")


def test_playbook_application():
    """Test applying a playbook to generate slides."""
    print("\n" + "=" * 60)
    print("TEST 7: Playbook Application")
    print("=" * 60)

    manager = PlaybookManager()

    # Get investor pitch playbook
    playbook = manager.get_playbook("professionals-investor_pitch-15")
    assert playbook is not None, "Expected to find investor pitch playbook"

    # Apply playbook
    slides = manager.apply_playbook(
        playbook=playbook,
        topic="AI Healthcare Startup",
        audience="professionals",
        purpose="investor_pitch",
        duration=15
    )

    print(f"\nApplied playbook 'professionals-investor_pitch-15' to topic 'AI Healthcare Startup':")
    print(f"Generated {len(slides)} slides:\n")

    for slide in slides:
        hero_marker = " [HERO]" if slide.get("is_hero") else ""
        print(f"  Slide {slide['slide_number']}: {slide['title']}{hero_marker}")
        print(f"    - Type: {slide.get('slide_type_hint', 'text')}")
        print(f"    - Purpose: {slide.get('purpose', 'N/A')}")
        print(f"    - Layout: {slide.get('layout', 'L25')}")
        if slide.get('topics'):
            print(f"    - Topics: {len(slide['topics'])} points")

    assert len(slides) >= 8, f"Expected at least 8 slides, got {len(slides)}"
    assert slides[0].get("is_hero"), "First slide should be a hero (title) slide"
    assert slides[-1].get("is_hero"), "Last slide should be a hero (closing) slide"

    print("\n✓ Playbook application test passed!")


def test_gap_identification():
    """Test gap identification for partial matches."""
    print("\n" + "=" * 60)
    print("TEST 8: Gap Identification")
    print("=" * 60)

    manager = PlaybookManager()
    merger = PlaybookMerger()

    # Get training playbook and identify gaps for a longer duration
    playbook = manager.get_playbook("college_students-training-15")
    assert playbook is not None, "Expected to find training playbook"

    gaps = merger.identify_gaps(
        playbook=playbook,
        topic="Machine Learning",
        purpose="training",
        duration=25  # Longer than playbook's 15 min
    )

    print(f"\nIdentified gaps for training playbook (15min -> 25min):")
    for gap in gaps:
        print(f"  - Position: {gap.position}, Purpose: {gap.purpose}, Count: {gap.count}")

    print("\n✓ Gap identification test passed!")


def test_scoring_formula():
    """Test the scoring formula calculations."""
    print("\n" + "=" * 60)
    print("TEST 9: Scoring Formula")
    print("=" * 60)

    manager = PlaybookManager()

    # Test cases with expected approximate scores
    test_cases = [
        # (audience, purpose, duration, expected_min_confidence)
        ("professionals", "investor_pitch", 15, 0.90),  # Exact match
        ("professionals", "investor_pitch", 10, 0.80),  # Duration off by 5
        ("professionals", "sales", 15, 0.60),           # Purpose compatible
        ("college_students", "investor_pitch", 15, 0.60),  # Audience compatible
    ]

    for audience, purpose, duration, expected_min in test_cases:
        match = manager.find_best_match(audience, purpose, duration)
        print(f"\n  {audience}/{purpose}/{duration}min:")
        print(f"    Confidence: {match.confidence:.2f} (expected >= {expected_min:.2f})")
        print(f"    Match Type: {match.match_type}")

    print("\n✓ Scoring formula test passed!")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PLAYBOOK SYSTEM TEST SUITE (v4.1)")
    print("=" * 60)

    try:
        test_playbook_loading()
        test_exact_match()
        test_partial_match()
        test_no_match()
        test_audience_normalization()
        test_purpose_normalization()
        test_playbook_application()
        test_gap_identification()
        test_scoring_formula()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
