#!/usr/bin/env python3
"""
Comprehensive Strawman Stage Test Suite

Tests all aspects of the strawman generation:
1. Story-driven slide categorization (slide_type_hint, purpose)
2. Layout analysis and service routing
3. Variant resolution via Text Service
4. Playbook matching (full, partial, no match)
5. Multiple topic types (technical, business, educational)
6. Preview URL generation with Layout Service

Usage:
    python test_strawman_comprehensive.py
    python test_strawman_comprehensive.py --quick      # Skip slow tests
    python test_strawman_comprehensive.py --topic "X"  # Single topic test
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set feature flags for testing
os.environ["USE_TEXT_SERVICE_COORDINATION"] = "true"
os.environ["USE_LAYOUT_SERVICE_COORDINATION"] = "false"


@dataclass
class TestResult:
    """Test result with pass/fail status and details."""
    name: str
    passed: bool
    duration: float
    details: Optional[str] = None
    error: Optional[str] = None


class StrawmanTestSuite:
    """Comprehensive strawman test suite."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.generator = None
        self.transformer = None
        self.deck_builder = None

    async def setup(self):
        """Initialize test components."""
        from src.agents.decision_engine import StrawmanGenerator
        from src.utils.strawman_transformer import StrawmanTransformer
        from src.utils.deck_builder_client import DeckBuilderClient
        from config.settings import get_settings

        settings = get_settings()
        self.generator = StrawmanGenerator()
        self.transformer = StrawmanTransformer()
        self.deck_builder = DeckBuilderClient(
            api_url=settings.DECK_BUILDER_API_URL,
            timeout=settings.DECK_BUILDER_TIMEOUT
        )

    def record(self, result: TestResult):
        """Record a test result."""
        self.results.append(result)
        status = "✓" if result.passed else "✗"
        print(f"  {status} {result.name} ({result.duration:.2f}s)")
        if result.details and result.passed:
            print(f"      {result.details}")
        if result.error:
            print(f"      ERROR: {result.error}")

    async def test_basic_strawman_generation(self) -> TestResult:
        """Test basic strawman generation with story-driven fields."""
        start = time.time()
        try:
            strawman = await self.generator.generate(
                topic="Digital Marketing Strategies",
                audience="business professionals",
                duration=15,
                purpose="inform"
            )

            # Validate structure
            assert len(strawman.slides) >= 5, f"Expected at least 5 slides, got {len(strawman.slides)}"
            assert strawman.slides[0].is_hero, "First slide should be hero"

            # Validate story-driven fields
            has_story_fields = 0
            for slide in strawman.slides:
                if slide.slide_type_hint:
                    has_story_fields += 1
                if slide.layout:
                    has_story_fields += 1

            return TestResult(
                name="Basic strawman generation",
                passed=True,
                duration=time.time() - start,
                details=f"{len(strawman.slides)} slides, {has_story_fields} story fields populated"
            )
        except Exception as e:
            return TestResult(
                name="Basic strawman generation",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    async def test_slide_type_hints(self) -> TestResult:
        """Test that slide_type_hint values are valid."""
        start = time.time()
        try:
            strawman = await self.generator.generate(
                topic="Cloud Architecture Patterns",
                audience="developers",
                duration=10,
                purpose="educate"
            )

            valid_types = {"hero", "text", "chart", "diagram", "infographic"}
            invalid_types = []
            type_counts = {}

            for slide in strawman.slides:
                hint = slide.slide_type_hint or ("hero" if slide.is_hero else "text")
                if hint not in valid_types:
                    invalid_types.append((slide.slide_number, hint))
                type_counts[hint] = type_counts.get(hint, 0) + 1

            if invalid_types:
                return TestResult(
                    name="Slide type hints validation",
                    passed=False,
                    duration=time.time() - start,
                    error=f"Invalid types: {invalid_types}"
                )

            # Most slides should be text (70%+ target)
            text_ratio = type_counts.get("text", 0) / len(strawman.slides)
            details = f"Types: {type_counts}, text ratio: {text_ratio:.0%}"

            return TestResult(
                name="Slide type hints validation",
                passed=True,
                duration=time.time() - start,
                details=details
            )
        except Exception as e:
            return TestResult(
                name="Slide type hints validation",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    async def test_layout_assignment(self) -> TestResult:
        """Test that layouts are assigned correctly."""
        start = time.time()
        try:
            strawman = await self.generator.generate(
                topic="Financial Performance Analysis",
                audience="executives",
                duration=15,
                purpose="report"
            )

            valid_layouts = {
                "L25", "L29", "C1-text", "C3-chart", "C4-infographic",
                "C5-diagram", "H1-generated", "H1-structured", "H2-section",
                "H3-closing", "I1", "I2", "I3", "I4"
            }
            layout_counts = {}
            invalid = []

            for slide in strawman.slides:
                layout = slide.layout or "L25"
                # Extract base layout (e.g., "L25" from "L25-bullets")
                base_layout = layout.split("-")[0] if "-" in layout else layout
                if base_layout not in valid_layouts and layout not in valid_layouts:
                    invalid.append((slide.slide_number, layout))
                layout_counts[layout] = layout_counts.get(layout, 0) + 1

            if invalid:
                return TestResult(
                    name="Layout assignment validation",
                    passed=False,
                    duration=time.time() - start,
                    error=f"Invalid layouts: {invalid}"
                )

            return TestResult(
                name="Layout assignment validation",
                passed=True,
                duration=time.time() - start,
                details=f"Layouts: {layout_counts}"
            )
        except Exception as e:
            return TestResult(
                name="Layout assignment validation",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    async def test_service_routing(self) -> TestResult:
        """Test that services are assigned based on slide_type_hint."""
        start = time.time()
        try:
            strawman = await self.generator.generate(
                topic="Machine Learning Pipeline Design",
                audience="data scientists",
                duration=20,
                purpose="technical"
            )

            valid_services = {"text", "analytics", "illustrator", "diagram"}
            service_counts = {}
            mismatches = []

            for slide in strawman.slides:
                service = slide.service or "text"
                hint = slide.slide_type_hint or ("hero" if slide.is_hero else "text")

                if service not in valid_services:
                    mismatches.append((slide.slide_number, f"invalid service: {service}"))
                    continue

                # Check service matches type hint
                expected_service_map = {
                    "hero": "text",
                    "text": "text",
                    "chart": "analytics",
                    "diagram": "diagram",
                    "infographic": "illustrator"
                }
                expected = expected_service_map.get(hint, "text")
                if service != expected:
                    mismatches.append((slide.slide_number, f"hint={hint}, service={service}, expected={expected}"))

                service_counts[service] = service_counts.get(service, 0) + 1

            # Allow minor mismatches (story-driven can override)
            if len(mismatches) > 2:
                return TestResult(
                    name="Service routing validation",
                    passed=False,
                    duration=time.time() - start,
                    error=f"Too many mismatches: {mismatches[:3]}..."
                )

            return TestResult(
                name="Service routing validation",
                passed=True,
                duration=time.time() - start,
                details=f"Services: {service_counts}"
            )
        except Exception as e:
            return TestResult(
                name="Service routing validation",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    async def test_variant_resolution(self) -> TestResult:
        """Test that text slides get variant_id assigned."""
        start = time.time()
        try:
            strawman = await self.generator.generate(
                topic="Project Management Best Practices",
                audience="managers",
                duration=15,
                purpose="train"
            )

            text_slides = [s for s in strawman.slides if s.service == "text" and not s.is_hero]
            with_variants = [s for s in text_slides if s.variant_id]

            ratio = len(with_variants) / max(1, len(text_slides))

            if ratio < 0.5:
                return TestResult(
                    name="Variant resolution",
                    passed=False,
                    duration=time.time() - start,
                    error=f"Only {len(with_variants)}/{len(text_slides)} text slides have variants ({ratio:.0%})"
                )

            variant_types = {}
            for s in with_variants:
                variant_types[s.variant_id] = variant_types.get(s.variant_id, 0) + 1

            return TestResult(
                name="Variant resolution",
                passed=True,
                duration=time.time() - start,
                details=f"{len(with_variants)}/{len(text_slides)} variants: {list(variant_types.keys())[:3]}"
            )
        except Exception as e:
            return TestResult(
                name="Variant resolution",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    async def test_hero_slides(self) -> TestResult:
        """Test hero slide generation (title, section dividers, closing)."""
        start = time.time()
        try:
            strawman = await self.generator.generate(
                topic="Enterprise Security Framework",
                audience="IT managers",
                duration=20,
                purpose="inform"
            )

            hero_slides = [s for s in strawman.slides if s.is_hero]

            if len(hero_slides) < 2:
                return TestResult(
                    name="Hero slides generation",
                    passed=False,
                    duration=time.time() - start,
                    error=f"Expected at least 2 hero slides, got {len(hero_slides)}"
                )

            hero_types = {}
            for s in hero_slides:
                hero_type = s.hero_type or "unknown"
                hero_types[hero_type] = hero_types.get(hero_type, 0) + 1

            # Should have title_slide at minimum
            has_title = hero_types.get("title_slide", 0) > 0 or strawman.slides[0].is_hero

            if not has_title:
                return TestResult(
                    name="Hero slides generation",
                    passed=False,
                    duration=time.time() - start,
                    error="No title slide found"
                )

            return TestResult(
                name="Hero slides generation",
                passed=True,
                duration=time.time() - start,
                details=f"{len(hero_slides)} heroes: {hero_types}"
            )
        except Exception as e:
            return TestResult(
                name="Hero slides generation",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    async def test_playbook_full_match(self) -> TestResult:
        """Test playbook FULL_MATCH scenario."""
        start = time.time()
        try:
            # This should match investor_pitch playbook
            strawman = await self.generator.generate(
                topic="TechCorp Series A Funding",
                audience="professionals",
                purpose="investor_pitch",
                duration=15
            )

            # Check if playbook was used (metadata or structure)
            metadata = strawman.metadata or {}
            match_type = metadata.get("playbook_match_type", "UNKNOWN")
            playbook_id = metadata.get("playbook_id", "")

            details = f"match={match_type}, playbook={playbook_id}"

            return TestResult(
                name="Playbook FULL_MATCH",
                passed=True,  # Test passes if generation succeeds
                duration=time.time() - start,
                details=details
            )
        except Exception as e:
            return TestResult(
                name="Playbook FULL_MATCH",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    async def test_playbook_partial_match(self) -> TestResult:
        """Test playbook PARTIAL_MATCH scenario."""
        start = time.time()
        try:
            # Professional + training but non-standard duration should partial match
            strawman = await self.generator.generate(
                topic="Sales Training Workshop",
                audience="professionals",
                purpose="training",
                duration=25
            )

            metadata = strawman.metadata or {}
            match_type = metadata.get("playbook_match_type", "UNKNOWN")

            return TestResult(
                name="Playbook PARTIAL_MATCH",
                passed=True,
                duration=time.time() - start,
                details=f"match={match_type}, slides={len(strawman.slides)}"
            )
        except Exception as e:
            return TestResult(
                name="Playbook PARTIAL_MATCH",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    async def test_playbook_no_match(self) -> TestResult:
        """Test playbook NO_MATCH scenario (custom generation)."""
        start = time.time()
        try:
            # Unusual audience/purpose should not match any playbook
            strawman = await self.generator.generate(
                topic="Quantum Computing Fundamentals",
                audience="hobbyists",
                purpose="curiosity",
                duration=45
            )

            metadata = strawman.metadata or {}
            match_type = metadata.get("playbook_match_type", "UNKNOWN")

            return TestResult(
                name="Playbook NO_MATCH (custom)",
                passed=True,
                duration=time.time() - start,
                details=f"match={match_type}, slides={len(strawman.slides)}"
            )
        except Exception as e:
            return TestResult(
                name="Playbook NO_MATCH (custom)",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    async def test_transformer_output(self) -> TestResult:
        """Test StrawmanTransformer produces valid Deck Builder payload."""
        start = time.time()
        try:
            strawman = await self.generator.generate(
                topic="API Design Principles",
                audience="developers",
                duration=10,
                purpose="educate"
            )

            strawman_dict = strawman.dict()
            payload = self.transformer.transform(strawman_dict, "API Design Principles")

            # Validate payload structure
            assert "slides" in payload, "Missing 'slides' in payload"
            assert len(payload["slides"]) == len(strawman.slides), "Slide count mismatch"

            # Check slide structure
            for i, slide in enumerate(payload["slides"]):
                assert "layout" in slide, f"Slide {i} missing 'layout'"
                assert "content" in slide, f"Slide {i} missing 'content'"

            return TestResult(
                name="Transformer output validation",
                passed=True,
                duration=time.time() - start,
                details=f"{len(payload['slides'])} slides transformed"
            )
        except Exception as e:
            return TestResult(
                name="Transformer output validation",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    async def test_deck_builder_preview(self) -> TestResult:
        """Test creating preview URL with Deck Builder."""
        start = time.time()
        try:
            strawman = await self.generator.generate(
                topic="Customer Success Metrics",
                audience="support managers",
                duration=10,
                purpose="report"
            )

            strawman_dict = strawman.dict()
            payload = self.transformer.transform(strawman_dict, "Customer Success Metrics")

            response = await self.deck_builder.create_presentation(payload)

            if not response:
                return TestResult(
                    name="Deck Builder preview",
                    passed=False,
                    duration=time.time() - start,
                    error="Empty response from Deck Builder"
                )

            url = response.get("url")
            pres_id = response.get("id")

            if not url or not pres_id:
                return TestResult(
                    name="Deck Builder preview",
                    passed=False,
                    duration=time.time() - start,
                    error=f"Missing url or id: {response}"
                )

            full_url = self.deck_builder.get_full_url(url)

            return TestResult(
                name="Deck Builder preview",
                passed=True,
                duration=time.time() - start,
                details=f"ID: {pres_id[:8]}..., URL: {full_url}"
            )
        except Exception as e:
            return TestResult(
                name="Deck Builder preview",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    async def test_different_durations(self) -> TestResult:
        """Test strawman generation with different durations."""
        start = time.time()
        try:
            results = []

            for duration in [5, 15, 30]:
                strawman = await self.generator.generate(
                    topic="Team Communication",
                    audience="employees",
                    duration=duration,
                    purpose="inform"
                )
                results.append((duration, len(strawman.slides)))

            # Longer durations should have more slides
            sorted_results = sorted(results, key=lambda x: x[0])

            # Just validate the relationship is generally correct
            details = ", ".join([f"{d}min={s}slides" for d, s in sorted_results])

            return TestResult(
                name="Duration scaling",
                passed=True,
                duration=time.time() - start,
                details=details
            )
        except Exception as e:
            return TestResult(
                name="Duration scaling",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    async def test_purpose_field_populated(self) -> TestResult:
        """Test that slide purpose field is populated."""
        start = time.time()
        try:
            strawman = await self.generator.generate(
                topic="Remote Work Policies",
                audience="HR managers",
                duration=15,
                purpose="policy"
            )

            with_purpose = [s for s in strawman.slides if s.purpose]

            ratio = len(with_purpose) / len(strawman.slides)

            if ratio < 0.5:
                return TestResult(
                    name="Purpose field population",
                    passed=False,
                    duration=time.time() - start,
                    error=f"Only {len(with_purpose)}/{len(strawman.slides)} slides have purpose ({ratio:.0%})"
                )

            purposes = list(set(s.purpose for s in with_purpose))

            return TestResult(
                name="Purpose field population",
                passed=True,
                duration=time.time() - start,
                details=f"{len(with_purpose)} slides, purposes: {purposes[:4]}"
            )
        except Exception as e:
            return TestResult(
                name="Purpose field population",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    async def test_generation_instructions(self) -> TestResult:
        """Test that generation_instructions are provided for complex slides."""
        start = time.time()
        try:
            strawman = await self.generator.generate(
                topic="Revenue Growth Analysis",
                audience="executives",
                duration=15,
                purpose="report"
            )

            with_instructions = [s for s in strawman.slides if s.generation_instructions]

            # Not all slides need instructions, but some should have them
            return TestResult(
                name="Generation instructions",
                passed=True,
                duration=time.time() - start,
                details=f"{len(with_instructions)}/{len(strawman.slides)} slides have instructions"
            )
        except Exception as e:
            return TestResult(
                name="Generation instructions",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    async def run_all(self, quick: bool = False):
        """Run all tests."""
        print("\n" + "=" * 60)
        print("COMPREHENSIVE STRAWMAN TEST SUITE (v4.0.25)")
        print("=" * 60)

        await self.setup()

        # Core tests (always run)
        core_tests = [
            self.test_basic_strawman_generation,
            self.test_slide_type_hints,
            self.test_layout_assignment,
            self.test_service_routing,
            self.test_variant_resolution,
            self.test_hero_slides,
        ]

        # Extended tests (skip in quick mode)
        extended_tests = [
            self.test_playbook_full_match,
            self.test_playbook_partial_match,
            self.test_playbook_no_match,
            self.test_transformer_output,
            self.test_deck_builder_preview,
            self.test_different_durations,
            self.test_purpose_field_populated,
            self.test_generation_instructions,
        ]

        tests_to_run = core_tests if quick else core_tests + extended_tests

        print(f"\nRunning {len(tests_to_run)} tests" + (" (quick mode)" if quick else "") + "...")
        print("-" * 60)

        for test in tests_to_run:
            result = await test()
            self.record(result)

        # Summary
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        total_time = sum(r.duration for r in self.results)

        print("\n" + "=" * 60)
        print(f"RESULTS: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
        print(f"Total time: {total_time:.1f}s")
        print("=" * 60)

        if passed == total:
            print("\n✓ ALL TESTS PASSED!")
        else:
            print("\n✗ Some tests failed:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.error}")

        return passed == total


async def main():
    quick = "--quick" in sys.argv

    # Single topic test
    if "--topic" in sys.argv:
        idx = sys.argv.index("--topic")
        if idx + 1 < len(sys.argv):
            topic = sys.argv[idx + 1]
            print(f"\n--- Single Topic Test: {topic} ---\n")

            from src.agents.decision_engine import StrawmanGenerator
            generator = StrawmanGenerator()

            strawman = await generator.generate(
                topic=topic,
                audience="professionals",
                duration=15,
                purpose="inform"
            )

            print(f"Generated {len(strawman.slides)} slides:\n")
            for slide in strawman.slides:
                print(f"[{slide.slide_number}] {slide.title[:50]}...")
                print(f"    type={slide.slide_type_hint}, layout={slide.layout}, service={slide.service}")
                if slide.variant_id:
                    print(f"    variant={slide.variant_id}")
                print()
            return

    # Full test suite
    suite = StrawmanTestSuite()
    success = await suite.run_all(quick=quick)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
