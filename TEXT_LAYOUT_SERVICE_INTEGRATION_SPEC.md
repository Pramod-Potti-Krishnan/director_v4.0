# Text Service + Layout Service Integration Specification

**Version**: 1.0
**Date**: 2024-12-13
**Purpose**: Reference document for Stage 6 Director Agent comparison

---

## Overview

This document describes the complete flow for generating presentation slides using Text Service and stitching them together using Layout Service.

### Service URLs

| Service | URL |
|---------|-----|
| Text Service | `https://web-production-5daf.up.railway.app` |
| Layout Service | `https://web-production-f0d13.up.railway.app` |

### Layout Types

| Layout | Description | Content Owner |
|--------|-------------|---------------|
| **L29** | Hero full-bleed layout | Text Service owns **entire slide** (hero_content) |
| **L25** | Main content shell | Text Service owns **main content** (rich_content), Layout Service owns **title/subtitle** |

---

## Step 1: Generate Slides from Text Service

### 1A. L29 Hero Slides (Title/Section/Closing)

**Endpoint**: `POST /v1.2/hero/title`
(Also available: `/v1.2/hero/section`, `/v1.2/hero/closing`)

**Request Body**:
```json
{
    "slide_number": 1,
    "slide_type": "title_slide",
    "narrative": "Introduce the epic story of Hanuman, the mighty monkey god",
    "topics": ["Hanuman", "Ramayana", "Hindu Mythology", "Adventure"],
    "visual_style": "kids",
    "context": {
        "theme": "kids",
        "audience": "children aged 6-12",
        "presentation_title": "The Story of Hanuman",
        "presenter": "Mythological Stories | For Kids"
    }
}
```

**Request Parameters Explained**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `slide_number` | int | Yes | Position in presentation (1-indexed) |
| `slide_type` | string | Yes | One of: `title_slide`, `section_divider`, `closing_slide` |
| `narrative` | string | Yes | Purpose/narrative for the slide content |
| `topics` | list[str] | Yes | Key topics to incorporate |
| `visual_style` | string | No | `illustrated` (default), `professional`, `kids` |
| `context` | object | No | Additional context for content generation |
| `context.theme` | string | No | Theme hint for styling |
| `context.audience` | string | No | Target audience description |
| `context.presentation_title` | string | No | Title of the presentation |
| `context.presenter` | string | No | Presenter info for attribution |

**Response Body**:
```json
{
    "content": "<div class=\"title-slide\">...complete HTML...</div>",
    "metadata": {
        "slide_type": "title_slide",
        "slide_number": 1,
        "validation": { ... },
        "character_counts": { ... }
    }
}
```

**Response Parameters Explained**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `content` | string | **Complete HTML** for the hero slide (full styling included) |
| `metadata` | object | Validation results, character counts, slide info |

---

### 1B. L25 Content Slides

**Endpoint**: `POST /v1.2/generate`

**Request Body**:
```json
{
    "variant_id": "grid_2x2_centered",
    "slide_spec": {
        "slide_title": "Who is Hanuman?",
        "slide_purpose": "Introduce Hanuman's key qualities",
        "key_message": "Hanuman represents devotion, strength, and humility",
        "target_points": [
            "Son of the Wind God Vayu",
            "Blessed with incredible strength",
            "Devoted follower of Lord Rama",
            "Master of shape-shifting"
        ],
        "tone": "fun and engaging",
        "audience": "children aged 6-12"
    },
    "presentation_spec": {
        "presentation_title": "The Story of Hanuman",
        "presentation_type": "educational storytelling",
        "current_slide_number": 2,
        "total_slides": 5
    },
    "enable_parallel": true,
    "validate_character_counts": false
}
```

**Request Parameters Explained**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `variant_id` | string | Yes | Template variant (see Available Variants below) |
| `slide_spec` | object | Yes | Slide-level specifications |
| `slide_spec.slide_title` | string | Yes | Title of the slide |
| `slide_spec.slide_purpose` | string | Yes | Purpose/goal of this slide |
| `slide_spec.key_message` | string | Yes | Main message to convey |
| `slide_spec.target_points` | list[str] | No | Specific points to include |
| `slide_spec.tone` | string | No | Desired tone (default: "professional") |
| `slide_spec.audience` | string | No | Target audience description |
| `presentation_spec` | object | No | Presentation-level context |
| `presentation_spec.presentation_title` | string | No | Title of the presentation |
| `presentation_spec.presentation_type` | string | No | Type (e.g., "educational") |
| `presentation_spec.current_slide_number` | int | No | Current slide number |
| `presentation_spec.total_slides` | int | No | Total slides in presentation |
| `enable_parallel` | bool | No | Enable parallel element generation |
| `validate_character_counts` | bool | No | Validate output character limits |

**Response Body**:
```json
{
    "success": true,
    "html": "<div style=\"display: grid;...>...content HTML...</div>",
    "elements": [ ... ],
    "metadata": {
        "variant_id": "grid_2x2_centered",
        "element_count": 4,
        "generation_time_ms": 1234
    },
    "validation": null,
    "variant_id": "grid_2x2_centered",
    "template_path": "..."
}
```

**Response Parameters Explained**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `success` | bool | Whether generation succeeded |
| `html` | string | **Main content HTML** (NOT the full slide - no title/subtitle) |
| `elements` | list | Individual element contents |
| `metadata` | object | Generation metadata |
| `validation` | object | Validation results (if requested) |
| `variant_id` | string | The variant used |

**Available Variants** (subset):

| Category | Variant IDs |
|----------|-------------|
| Grid | `grid_2x2_centered`, `grid_2x3`, `grid_3x2`, `grid_2x2_numbered`, `grid_2x3_numbered` |
| Sequential | `sequential_3col`, `sequential_4col`, `sequential_5col` |
| Comparison | `comparison_2col`, `comparison_3col`, `comparison_4col` |
| Metrics | `metrics_3col`, `metrics_4col`, `metrics_2x2_grid` |
| Matrix | `matrix_2x2`, `matrix_2x3` |
| Table | `table_2col`, `table_3col`, `table_4col` |

---

## Step 2: Assemble Slides for Layout Service

After receiving responses from Text Service, assemble slides in the format expected by Layout Service.

### L29 Slide Assembly

```python
# Text Service returns:
text_service_response = {
    "content": "<div class=\"title-slide\">...</div>",
    "metadata": { ... }
}

# Assemble for Layout Service:
l29_slide = {
    "layout": "L29",
    "content": {
        "hero_content": text_service_response["content"]
    }
}
```

### L25 Slide Assembly

```python
# Text Service returns:
text_service_response = {
    "html": "<div style=\"display: grid;...\">...</div>",
    "metadata": { ... }
}

# Assemble for Layout Service:
# NOTE: slide_title and subtitle come from YOUR slide definition, NOT from Text Service
l25_slide = {
    "layout": "L25",
    "content": {
        "slide_title": "Who is Hanuman?",           # From your slide spec
        "subtitle": "The greatest devotee of Lord Rama",  # From your slide spec
        "rich_content": text_service_response["html"]     # From Text Service
    }
}
```

**Key Distinction**:
- **L29**: `hero_content` = Text Service's `content` field (complete HTML)
- **L25**: `rich_content` = Text Service's `html` field (main content only)
- **L25**: `slide_title` and `subtitle` are provided by the caller (not Text Service)

---

## Step 3: Create Presentation in Layout Service

**Endpoint**: `POST /api/presentations`

**Request Body**:
```json
{
    "title": "The Story of Hanuman",
    "slides": [
        {
            "layout": "L29",
            "content": {
                "hero_content": "<div class=\"title-slide\">...</div>"
            }
        },
        {
            "layout": "L25",
            "content": {
                "slide_title": "Who is Hanuman?",
                "subtitle": "The greatest devotee of Lord Rama",
                "rich_content": "<div style=\"display: grid;...\">...</div>"
            }
        },
        {
            "layout": "L25",
            "content": {
                "slide_title": "Hanuman's Greatest Adventures",
                "subtitle": "From birth to becoming a hero",
                "rich_content": "<div>...</div>"
            }
        }
    ]
}
```

**Request Parameters Explained**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | Presentation title (max 200 chars) |
| `slides` | list[Slide] | Yes | Array of slide objects (min 1) |

**Slide Object (L29)**:

| Field | Type | Description |
|-------|------|-------------|
| `layout` | string | Must be `"L29"` |
| `content.hero_content` | string | Complete HTML for full-bleed hero slide |

**Slide Object (L25)**:

| Field | Type | Description |
|-------|------|-------------|
| `layout` | string | Must be `"L25"` |
| `content.slide_title` | string | Slide title (max 80 chars) |
| `content.subtitle` | string | Subtitle (max 120 chars, optional) |
| `content.rich_content` | string | Main content HTML from Text Service |

**Response Body**:
```json
{
    "id": "d3a41a07-0683-4e87-b262-b09e64a1055c",
    "url": "/p/d3a41a07-0683-4e87-b262-b09e64a1055c",
    "message": "Presentation created successfully"
}
```

**Response Parameters Explained**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | UUID of the created presentation |
| `url` | string | Relative URL path to view the presentation |
| `message` | string | Success message |

---

## Step 4: Construct Full Presentation URL

The Layout Service returns a **relative URL**. Construct the full URL:

```python
layout_service_base = "https://web-production-f0d13.up.railway.app"
relative_url = response["url"]  # "/p/d3a41a07-0683-4e87-b262-b09e64a1055c"

full_url = f"{layout_service_base}{relative_url}"
# Result: "https://web-production-f0d13.up.railway.app/p/d3a41a07-0683-4e87-b262-b09e64a1055c"
```

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DIRECTOR AGENT                               │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1: Generate Slides from Text Service                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  For L29 (Hero) slides:                                              │
│    POST /v1.2/hero/title                                             │
│    ├── Input: slide_number, slide_type, narrative, topics, context  │
│    └── Output: content (complete HTML)                               │
│                                                                      │
│  For L25 (Content) slides:                                           │
│    POST /v1.2/generate                                               │
│    ├── Input: variant_id, slide_spec, presentation_spec             │
│    └── Output: html (main content only)                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2: Assemble Slides                                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  L29 Slide:                                                          │
│    {                                                                 │
│      "layout": "L29",                                                │
│      "content": { "hero_content": <Text Service content> }           │
│    }                                                                 │
│                                                                      │
│  L25 Slide:                                                          │
│    {                                                                 │
│      "layout": "L25",                                                │
│      "content": {                                                    │
│        "slide_title": <from Director's slide plan>,                  │
│        "subtitle": <from Director's slide plan>,                     │
│        "rich_content": <Text Service html>                           │
│      }                                                               │
│    }                                                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3: Create Presentation in Layout Service                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  POST /api/presentations                                             │
│    Input: { "title": "...", "slides": [...] }                        │
│    Output: { "id": "uuid", "url": "/p/uuid", "message": "..." }      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 4: Return Full URL                                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Full URL = Layout Service Base URL + Response URL                   │
│  Example: https://web-production-f0d13.up.railway.app/p/{uuid}       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Content Ownership Summary

| Layout | Component | Owner | Format |
|--------|-----------|-------|--------|
| L29 | Entire slide | Text Service | `hero_content` (complete HTML with styling) |
| L25 | Title | Director/Caller | `slide_title` (plain text, max 80 chars) |
| L25 | Subtitle | Director/Caller | `subtitle` (plain text, max 120 chars) |
| L25 | Main content | Text Service | `rich_content` (HTML with styling) |

---

## Example: Complete Python Implementation

```python
import httpx

TEXT_SERVICE_URL = "https://web-production-5daf.up.railway.app"
LAYOUT_SERVICE_URL = "https://web-production-f0d13.up.railway.app"

async def generate_presentation(presentation_title: str, slides_config: list) -> str:
    """
    Generate a presentation and return the URL.

    Args:
        presentation_title: Title of the presentation
        slides_config: List of slide configurations

    Returns:
        Full URL to view the presentation
    """
    layout_slides = []

    async with httpx.AsyncClient(timeout=120.0) as client:

        # Step 1: Generate each slide from Text Service
        for i, slide in enumerate(slides_config, 1):

            if slide["layout"] == "L29":
                # Hero slide - call /v1.2/hero/title
                response = await client.post(
                    f"{TEXT_SERVICE_URL}/v1.2/hero/title",
                    json={
                        "slide_number": i,
                        "slide_type": slide["slide_type"],
                        "narrative": slide["narrative"],
                        "topics": slide["topics"],
                        "context": slide.get("context", {})
                    }
                )
                result = response.json()

                layout_slides.append({
                    "layout": "L29",
                    "content": {
                        "hero_content": result["content"]
                    }
                })

            else:  # L25
                # Content slide - call /v1.2/generate
                response = await client.post(
                    f"{TEXT_SERVICE_URL}/v1.2/generate",
                    json={
                        "variant_id": slide["variant_id"],
                        "slide_spec": {
                            "slide_title": slide["slide_title"],
                            "slide_purpose": slide["slide_purpose"],
                            "key_message": slide["key_message"],
                            "target_points": slide["target_points"],
                            "tone": slide.get("tone", "professional"),
                            "audience": slide.get("audience", "general")
                        },
                        "presentation_spec": {
                            "presentation_title": presentation_title,
                            "current_slide_number": i,
                            "total_slides": len(slides_config)
                        }
                    }
                )
                result = response.json()

                layout_slides.append({
                    "layout": "L25",
                    "content": {
                        "slide_title": slide["slide_title"],
                        "subtitle": slide.get("subtitle", ""),
                        "rich_content": result["html"]
                    }
                })

        # Step 2: Create presentation in Layout Service
        response = await client.post(
            f"{LAYOUT_SERVICE_URL}/api/presentations",
            json={
                "title": presentation_title,
                "slides": layout_slides
            }
        )
        result = response.json()

        # Step 3: Return full URL
        return f"{LAYOUT_SERVICE_URL}{result['url']}"
```

---

## Test Results (2024-12-13)

Successfully generated presentation with 5 slides:

| Slide | Layout | Variant | Content Size |
|-------|--------|---------|--------------|
| 1 | L29 | hero/title | 1,123 chars |
| 2 | L25 | grid_2x2_centered | 4,713 chars |
| 3 | L25 | sequential_4col | 6,256 chars |
| 4 | L25 | comparison_2col | 2,097 chars |
| 5 | L25 | grid_2x3_numbered | 8,738 chars |

**Presentation URL**: `https://web-production-f0d13.up.railway.app/p/d3a41a07-0683-4e87-b262-b09e64a1055c`

---

## Files Created

| File | Purpose |
|------|---------|
| `tools/test_text_layout_integration.py` | Working test script implementing this flow |
| `TEXT_LAYOUT_SERVICE_INTEGRATION_SPEC.md` | This specification document |
