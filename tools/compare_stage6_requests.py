#!/usr/bin/env python3
"""
Compare Stage 6 Captured Requests Against TEXT_LAYOUT_SERVICE_INTEGRATION_SPEC.md

This script validates captured Text Service requests to identify mismatches
between what Director Stage 6 sends and what Text Service expects.

Usage:
    python tools/compare_stage6_requests.py

The script reads JSON files from debug_captures/ directory and validates:
1. Required fields are present
2. Field types match spec
3. variant_id is valid
4. slide_spec has all required keys
5. presentation_spec has all required keys
"""

import json
from pathlib import Path
from typing import List, Dict, Any

# Required fields per TEXT_LAYOUT_SERVICE_INTEGRATION_SPEC.md
REQUIRED_TOP_LEVEL = ['variant_id', 'slide_spec', 'presentation_spec']

REQUIRED_SLIDE_SPEC = [
    'slide_title',
    'slide_purpose',
    'key_message',
    'target_points',
    'tone',
    'audience'
]

REQUIRED_PRESENTATION_SPEC = [
    'presentation_title',
    'presentation_type',
    'current_slide_number',
    'total_slides'
]

# Valid L25 variants per spec
VALID_VARIANTS = [
    'grid_2x2_centered',
    'sequential_4col',
    'comparison_2col',
    'grid_2x3_numbered',
    'bullets_with_detail',
    'single_stat_hero'
]


def validate_request(request: Dict[str, Any]) -> List[str]:
    """
    Validate a Text Service request against the spec.

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check top-level fields
    for field in REQUIRED_TOP_LEVEL:
        if field not in request:
            errors.append(f"Missing required field: {field}")

    # Check variant_id
    if 'variant_id' in request:
        variant = request['variant_id']
        if variant not in VALID_VARIANTS:
            errors.append(
                f"Invalid variant_id: '{variant}'. "
                f"Valid options: {VALID_VARIANTS}"
            )
    else:
        errors.append("variant_id is missing")

    # Check slide_spec
    if 'slide_spec' in request:
        slide_spec = request['slide_spec']

        for field in REQUIRED_SLIDE_SPEC:
            if field not in slide_spec:
                errors.append(f"Missing slide_spec.{field}")

        # Check target_points is a non-empty list
        if 'target_points' in slide_spec:
            tp = slide_spec['target_points']
            if not isinstance(tp, list):
                errors.append(
                    f"slide_spec.target_points must be a list, got {type(tp).__name__}"
                )
            elif len(tp) == 0:
                errors.append("slide_spec.target_points is empty")
        else:
            errors.append("slide_spec.target_points is missing")

        # Check string fields are not empty
        string_fields = ['slide_title', 'slide_purpose', 'key_message', 'tone', 'audience']
        for field in string_fields:
            if field in slide_spec:
                if not isinstance(slide_spec[field], str):
                    errors.append(f"slide_spec.{field} must be a string")
                elif not slide_spec[field].strip():
                    errors.append(f"slide_spec.{field} is empty")
    else:
        errors.append("slide_spec is missing")

    # Check presentation_spec
    if 'presentation_spec' in request:
        pres_spec = request['presentation_spec']

        for field in REQUIRED_PRESENTATION_SPEC:
            if field not in pres_spec:
                errors.append(f"Missing presentation_spec.{field}")

        # Check numeric fields
        if 'current_slide_number' in pres_spec:
            if not isinstance(pres_spec['current_slide_number'], int):
                errors.append("presentation_spec.current_slide_number must be an integer")

        if 'total_slides' in pres_spec:
            if not isinstance(pres_spec['total_slides'], int):
                errors.append("presentation_spec.total_slides must be an integer")
    else:
        errors.append("presentation_spec is missing")

    return errors


def print_request_summary(request: Dict[str, Any]):
    """Print a summary of the request for debugging."""
    print(f"   variant_id: {request.get('variant_id', 'MISSING')}")

    slide_spec = request.get('slide_spec', {})
    print(f"   slide_title: {slide_spec.get('slide_title', 'MISSING')}")
    print(f"   slide_purpose: {slide_spec.get('slide_purpose', 'MISSING')[:50]}...")
    print(f"   key_message: {slide_spec.get('key_message', 'MISSING')[:50]}...")

    target_points = slide_spec.get('target_points', [])
    print(f"   target_points: {len(target_points)} items")
    for i, point in enumerate(target_points[:3]):
        print(f"      [{i}]: {str(point)[:60]}...")
    if len(target_points) > 3:
        print(f"      ... and {len(target_points) - 3} more")

    print(f"   tone: {slide_spec.get('tone', 'MISSING')}")
    print(f"   audience: {slide_spec.get('audience', 'MISSING')}")

    pres_spec = request.get('presentation_spec', {})
    print(f"   presentation_title: {pres_spec.get('presentation_title', 'MISSING')}")
    print(f"   presentation_type: {pres_spec.get('presentation_type', 'MISSING')}")
    print(f"   slide: {pres_spec.get('current_slide_number', '?')}/{pres_spec.get('total_slides', '?')}")


def main():
    """Main validation function."""
    debug_dir = Path(__file__).parent.parent / "debug_captures"

    print("=" * 70)
    print("Stage 6 Request Validation")
    print("=" * 70)
    print(f"Debug directory: {debug_dir}")
    print()

    if not debug_dir.exists():
        print("No debug_captures/ directory found.")
        print("Run Director Stage 6 first to generate capture files.")
        return

    captures = sorted(debug_dir.glob("*.json"))
    if not captures:
        print("No capture files found in debug_captures/.")
        print("Run Director Stage 6 first to generate capture files.")
        return

    print(f"Found {len(captures)} capture file(s)\n")
    print("-" * 70)

    total_errors = 0
    files_with_errors = 0

    for capture_file in captures:
        print(f"\n=== {capture_file.name} ===")

        try:
            data = json.loads(capture_file.read_text())
        except json.JSONDecodeError as e:
            print(f"   ERROR: Could not parse JSON: {e}")
            continue

        request = data.get('request', {})
        response = data.get('response')
        error = data.get('error')

        # Show capture metadata
        print(f"   Session: {data.get('session_id', 'unknown')}")
        print(f"   Slide index: {data.get('slide_index', '?')}")
        print(f"   Timestamp: {data.get('timestamp', 'unknown')}")

        if error:
            print(f"   ERROR recorded: {error[:200]}...")

        # Validate request
        errors = validate_request(request)

        if errors:
            files_with_errors += 1
            total_errors += len(errors)
            print("\n   VALIDATION ERRORS:")
            for err in errors:
                print(f"   - {err}")
        else:
            print("\n   Request format is valid")

        # Print request summary
        print("\n   REQUEST SUMMARY:")
        print_request_summary(request)

        # Show response status
        if response:
            content = response.get('content', '')
            print(f"\n   RESPONSE: {len(content)} chars")
            if content:
                print(f"   Preview: {content[:100]}...")
        elif error:
            print(f"\n   RESPONSE: FAILED (see error above)")
        else:
            print(f"\n   RESPONSE: Not captured")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total files: {len(captures)}")
    print(f"Files with errors: {files_with_errors}")
    print(f"Total errors: {total_errors}")

    if total_errors == 0:
        print("\nAll requests match the expected format!")
    else:
        print(f"\nFound {total_errors} format issues to investigate.")
        print("Compare with TEXT_LAYOUT_SERVICE_INTEGRATION_SPEC.md for correct format.")

    print("=" * 70)


if __name__ == "__main__":
    main()
