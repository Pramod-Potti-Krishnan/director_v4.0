#!/usr/bin/env python3
"""
Test suite for v4.5 Smart Context Extraction Enhancement

Tests:
1. ExtractedContext v4.5 fields (slide_count, presets)
2. SessionV4 v4.5 fields (requested_slide_count, presets)
3. StrawmanGenerator respects explicit slide count
4. Preset mapping in content_context
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("DIRECTOR v4.5 SMART CONTEXT EXTRACTION TEST SUITE")
print("=" * 60)
print()

def test_extracted_context_v45_fields():
    """Test 1: ExtractedContext has v4.5 fields for smart extraction."""
    print("[TEST 1] ExtractedContext v4.5 Fields")
    print("-" * 50)

    from src.models.decision import ExtractedContext

    # Create with v4.5 fields
    ctx = ExtractedContext(
        topic="AI Startup Pitch",
        audience="investors",
        duration=15,
        purpose="pitch",
        slide_count=20,
        has_explicit_slide_count=True,
        audience_preset="executive",
        purpose_preset="persuade",
        time_preset="standard"
    )

    # Verify v4.5 fields exist and work
    assert hasattr(ctx, 'slide_count'), "Missing slide_count field"
    assert hasattr(ctx, 'has_explicit_slide_count'), "Missing has_explicit_slide_count field"
    assert hasattr(ctx, 'audience_preset'), "Missing audience_preset field"
    assert hasattr(ctx, 'purpose_preset'), "Missing purpose_preset field"
    assert hasattr(ctx, 'time_preset'), "Missing time_preset field"
    print("  ✓ All v4.5 fields exist")

    assert ctx.slide_count == 20, f"Expected slide_count=20, got {ctx.slide_count}"
    assert ctx.has_explicit_slide_count == True
    assert ctx.audience_preset == "executive"
    assert ctx.purpose_preset == "persuade"
    assert ctx.time_preset == "standard"
    print("  ✓ Fields hold correct values")

    # Test default values
    ctx_defaults = ExtractedContext()
    assert ctx_defaults.slide_count is None
    assert ctx_defaults.has_explicit_slide_count == False
    assert ctx_defaults.audience_preset is None
    print("  ✓ Default values are None/False")

    print("  ✓ TEST 1 PASSED!")
    print()
    return True


def test_session_v45_fields():
    """Test 2: SessionV4 has v4.5 fields for smart extraction."""
    print("[TEST 2] SessionV4 v4.5 Fields")
    print("-" * 50)

    from src.models.session import SessionV4

    # Create session with v4.5 fields
    session = SessionV4(
        id="test-session",
        user_id="test-user",
        requested_slide_count=15,
        audience_preset="professional",
        purpose_preset="inform",
        time_preset="quick"
    )

    # Verify fields exist
    assert hasattr(session, 'requested_slide_count'), "Missing requested_slide_count"
    assert hasattr(session, 'audience_preset'), "Missing audience_preset"
    assert hasattr(session, 'purpose_preset'), "Missing purpose_preset"
    assert hasattr(session, 'time_preset'), "Missing time_preset"
    print("  ✓ All v4.5 session fields exist")

    # Verify values
    assert session.requested_slide_count == 15
    assert session.audience_preset == "professional"
    assert session.purpose_preset == "inform"
    assert session.time_preset == "quick"
    print("  ✓ Fields hold correct values")

    # Test default values
    session_defaults = SessionV4(id="test", user_id="test")
    assert session_defaults.requested_slide_count is None
    assert session_defaults.audience_preset is None
    print("  ✓ Default values are None")

    print("  ✓ TEST 2 PASSED!")
    print()
    return True


def test_content_context_with_presets():
    """Test 3: ContentContext builds correctly from presets."""
    print("[TEST 3] ContentContext from Presets")
    print("-" * 50)

    from src.models.content_context import build_content_context, AUDIENCE_PRESETS, PURPOSE_PRESETS

    # Test with preset values
    ctx = build_content_context(
        audience="executive",
        purpose="persuade",
        duration=10,
        tone="confident"
    )

    # Should use executive preset
    assert ctx.audience is not None
    assert ctx.audience.max_sentence_words <= 15, "Executive should have concise sentences"
    print(f"  ✓ Executive preset: max_sentence_words={ctx.audience.max_sentence_words}")

    # Should use persuade preset
    assert ctx.purpose is not None
    assert ctx.purpose.include_cta == True, "Persuade should include CTA"
    print(f"  ✓ Persuade preset: include_cta={ctx.purpose.include_cta}")

    # Test with informal audience names that should map to presets
    ctx_kids = build_content_context(audience="kids_young", purpose="educate")
    assert ctx_kids.audience.max_sentence_words <= 10, "Kids should have simple sentences"
    print(f"  ✓ Kids preset: max_sentence_words={ctx_kids.audience.max_sentence_words}")

    # Test to_text_service_format()
    format = ctx.to_text_service_format()
    assert 'audience' in format
    assert 'purpose' in format
    assert 'time' in format
    print(f"  ✓ to_text_service_format() includes all sections")

    print("  ✓ TEST 3 PASSED!")
    print()
    return True


def test_slide_count_logic():
    """Test 4: Slide count override logic in StrawmanGenerator."""
    print("[TEST 4] Slide Count Override Logic")
    print("-" * 50)

    from src.agents.decision_engine import StrawmanGenerator
    import inspect

    # Verify generate() accepts requested_slide_count parameter
    sig = inspect.signature(StrawmanGenerator.generate)
    params = list(sig.parameters.keys())

    assert 'requested_slide_count' in params, "generate() missing requested_slide_count param"
    print("  ✓ generate() accepts requested_slide_count parameter")

    # Verify _fallback_strawman accepts it too
    sig_fallback = inspect.signature(StrawmanGenerator._fallback_strawman)
    params_fallback = list(sig_fallback.parameters.keys())

    assert 'requested_slide_count' in params_fallback, "_fallback_strawman missing param"
    print("  ✓ _fallback_strawman() accepts requested_slide_count parameter")

    # Test fallback strawman with explicit count
    gen = StrawmanGenerator.__new__(StrawmanGenerator)  # Create without __init__
    gen.agent = None
    gen.layout_analyzer = None
    gen.content_analyzer = None
    gen.text_coord_client = None
    gen.layout_client = None
    gen.playbook_manager = None
    gen.playbook_merger = None

    # Generate with explicit slide count
    strawman = gen._fallback_strawman("Test Topic", duration=10, requested_slide_count=20)

    assert len(strawman.slides) == 20, f"Expected 20 slides, got {len(strawman.slides)}"
    print(f"  ✓ Fallback strawman respects explicit count: {len(strawman.slides)} slides")

    # Generate without explicit count (should use duration-based)
    strawman_default = gen._fallback_strawman("Test Topic", duration=10)
    expected_count = max(5, min(15, 10 // 2 + 2))  # = 7

    assert len(strawman_default.slides) == expected_count, f"Expected {expected_count}, got {len(strawman_default.slides)}"
    print(f"  ✓ Without explicit count, uses duration-based: {len(strawman_default.slides)} slides")

    print("  ✓ TEST 4 PASSED!")
    print()
    return True


def test_guidance_has_contextual_rules():
    """Test 5: Director guidance includes contextual question rules."""
    print("[TEST 5] Director Guidance Has v4.5 Rules")
    print("-" * 50)

    import os
    guidance_path = os.path.join(
        os.path.dirname(__file__),
        "config", "guidance", "director_guidance.md"
    )

    with open(guidance_path, 'r') as f:
        content = f.read()

    # Check for v4.5 contextual question rules
    assert "Don't Be a Broken Record" in content, "Missing 'Don't Be a Broken Record' section"
    print("  ✓ Has 'Don't Be a Broken Record' guidance")

    assert "board meeting" in content.lower() and "executive" in content.lower()
    print("  ✓ Has audience inference examples")

    assert "pitch deck" in content.lower() and "persuade" in content.lower()
    print("  ✓ Has purpose inference examples")

    assert "Mapping to Presets" in content
    print("  ✓ Has preset mapping section")

    print("  ✓ TEST 5 PASSED!")
    print()
    return True


def test_system_prompt_has_extraction_rules():
    """Test 6: Decision Engine system prompt has extraction rules."""
    print("[TEST 6] System Prompt Has Extraction Rules")
    print("-" * 50)

    from src.agents.decision_engine import DecisionEngine

    # Create engine (won't connect to Vertex AI, just load prompts)
    engine = DecisionEngine.__new__(DecisionEngine)
    engine.tool_registry = None
    engine.model_name = "test"
    engine.guidance = ""
    engine.cost_rules = ""
    engine.approval_phrases = {}

    # Build system prompt
    engine.tool_registry = type('MockRegistry', (), {
        'get_tool_for_llm': lambda self: [],
        'get_approval_phrases': lambda self: {}
    })()

    prompt = engine._build_system_prompt()

    # Check for v4.5 extraction rules
    assert "SLIDE COUNT PARSING" in prompt
    print("  ✓ Has SLIDE COUNT PARSING section")

    assert "AUDIENCE PRESET MAPPING" in prompt
    print("  ✓ Has AUDIENCE PRESET MAPPING section")

    assert "PURPOSE PRESET MAPPING" in prompt
    print("  ✓ Has PURPOSE PRESET MAPPING section")

    assert "TIME/DURATION PRESET MAPPING" in prompt
    print("  ✓ Has TIME/DURATION PRESET MAPPING section")

    assert "CONTEXTUAL QUESTIONS" in prompt
    print("  ✓ Has CONTEXTUAL QUESTIONS section")

    assert "Don't Be a Broken Record" in prompt
    print("  ✓ Has 'Don't Be a Broken Record' guidance")

    print("  ✓ TEST 6 PASSED!")
    print()
    return True


if __name__ == "__main__":
    results = []

    try:
        results.append(("ExtractedContext v4.5 Fields", test_extracted_context_v45_fields()))
    except Exception as e:
        print(f"  ✗ TEST 1 FAILED: {e}")
        results.append(("ExtractedContext v4.5 Fields", False))

    try:
        results.append(("SessionV4 v4.5 Fields", test_session_v45_fields()))
    except Exception as e:
        print(f"  ✗ TEST 2 FAILED: {e}")
        results.append(("SessionV4 v4.5 Fields", False))

    try:
        results.append(("ContentContext from Presets", test_content_context_with_presets()))
    except Exception as e:
        print(f"  ✗ TEST 3 FAILED: {e}")
        results.append(("ContentContext from Presets", False))

    try:
        results.append(("Slide Count Override Logic", test_slide_count_logic()))
    except Exception as e:
        print(f"  ✗ TEST 4 FAILED: {e}")
        results.append(("Slide Count Override Logic", False))

    try:
        results.append(("Director Guidance v4.5 Rules", test_guidance_has_contextual_rules()))
    except Exception as e:
        print(f"  ✗ TEST 5 FAILED: {e}")
        results.append(("Director Guidance v4.5 Rules", False))

    try:
        results.append(("System Prompt Extraction Rules", test_system_prompt_has_extraction_rules()))
    except Exception as e:
        print(f"  ✗ TEST 6 FAILED: {e}")
        results.append(("System Prompt Extraction Rules", False))

    # Summary
    print("=" * 60)
    passed = sum(1 for _, p in results if p)
    total = len(results)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print()
        print("✓ ALL TESTS PASSED!")
        print()
        print("Smart Context Extraction is ready!")
        print("- ExtractedContext has slide_count and preset fields ✓")
        print("- SessionV4 stores explicit slide count and presets ✓")
        print("- ContentContext builds from presets correctly ✓")
        print("- StrawmanGenerator respects explicit slide count ✓")
        print("- Director guidance has contextual question rules ✓")
        print("- System prompt has extraction and mapping rules ✓")
    else:
        print()
        print("✗ SOME TESTS FAILED")
        for name, passed in results:
            status = "✓" if passed else "✗"
            print(f"  {status} {name}")
        sys.exit(1)
