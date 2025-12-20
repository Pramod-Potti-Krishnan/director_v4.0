# Text Service - Director Integration Requirements

**Version**: 2.0 (Updated for Text Service v1.2.2)
**Date**: December 2024
**Priority**: HIGH (Major efficiency improvements)
**Status**: FULLY ALIGNED - No mapping needed with unified slides API

## Summary

Director Agent v4.3 integrates with Text Service v1.2.2 using the **NEW unified slides API** (`/v1.2/slides/*`). This router returns spec-compliant responses with correct field names.

**Key Improvements**:
- **67% LLM call reduction**: C1-text uses 1 call instead of 3
- **Structured H-series**: Returns individual fields, not full HTML
- **I-series aliases**: `slide_title`, `body` included directly
- **background_color**: Returned with correct defaults

---

## NEW: Unified Slides Router (`/v1.2/slides/*`)

Text Service v1.2.2 introduced a unified slides router that returns **spec-compliant responses** matching SLIDE_GENERATION_INPUT_SPEC.md exactly.

### Endpoint Summary

| Layout | Endpoint | Response Fields | LLM Calls |
|--------|----------|-----------------|-----------|
| H1-generated | `POST /v1.2/slides/H1-generated` | `hero_content`, `slide_title`, `subtitle`, `background_image` | 1 |
| H1-structured | `POST /v1.2/slides/H1-structured` | `slide_title`, `subtitle`, `author_info`, `background_color` | 1 |
| H2-section | `POST /v1.2/slides/H2-section` | `section_number`, `slide_title`, `subtitle`, `background_color` | 1 |
| H3-closing | `POST /v1.2/slides/H3-closing` | `slide_title`, `subtitle`, `contact_info`, `background_color` | 1 |
| C1-text | `POST /v1.2/slides/C1-text` | `slide_title`, `subtitle`, `body`, `rich_content`, `background_color` | **1** |
| L25 | `POST /v1.2/slides/L25` | Same as C1-text | 1 |
| L29 | `POST /v1.2/slides/L29` | Same as H1-generated | 1 |
| I1-I4 | `POST /v1.2/slides/I{1-4}` | `slide_title`, `subtitle`, `body`, `image_url`, `background_color` | 2 |

### Combined Generation (C1-text)

**OLD approach** (3 LLM calls per slide):
```
1. POST /api/ai/slide/title      → slide_title
2. POST /api/ai/slide/subtitle   → subtitle
3. POST /v1.2/generate           → body/rich_content
```

**NEW approach** (1 LLM call per slide):
```
1. POST /v1.2/slides/C1-text     → slide_title + subtitle + body + background_color
```

**Savings**: 12 fewer LLM calls per 10-slide deck (assuming 6 content slides).

---

## Response Formats

### C1-text Response
```json
{
  "slide_title": "<h2 class='slide-title' style='...'>Market Analysis</h2>",
  "subtitle": "<p class='slide-subtitle' style='...'>Q4 2024 Performance</p>",
  "body": "<div class='content-grid'>...</div>",
  "rich_content": "<div class='content-grid'>...</div>",
  "background_color": "#ffffff",
  "metadata": {
    "variant_id": "sequential_3col",
    "llm_calls": 1,
    "generation_time_ms": 1200
  }
}
```

### H1-structured Response
```json
{
  "slide_title": "<h1 class='presentation-title' style='...'>Annual Report 2024</h1>",
  "subtitle": "<p class='presentation-subtitle' style='...'>Building Tomorrow Together</p>",
  "author_info": "<div class='author-info' style='...'>Dr. Jane Smith | December 2024</div>",
  "background_color": "#1e3a5f",
  "metadata": {
    "llm_calls": 1
  }
}
```

### H2-section Response
```json
{
  "section_number": "<span class='section-number'>01</span>",
  "slide_title": "<h2 class='section-title' style='...'>Market Overview</h2>",
  "subtitle": "<p class='section-subtitle' style='...'>Understanding the landscape</p>",
  "background_color": "#374151",
  "metadata": {
    "llm_calls": 1
  }
}
```

### I-series Response
```json
{
  "slide_title": "<h2 class='slide-title' style='...'>Meet the Team</h2>",
  "subtitle": "<p class='slide-subtitle' style='...'>Leadership Excellence</p>",
  "body": "<ul class='bullet-list'>...</ul>",
  "image_url": "https://storage.example.com/images/team.jpg",
  "background_color": "#ffffff",
  "metadata": {
    "layout_type": "I1",
    "llm_calls": 2,
    "image_source": "ai_generated"
  }
}
```

---

## Background Color Defaults

Each layout type has a default background color per SPEC:

| Layout | Default Background | Description |
|--------|-------------------|-------------|
| H1-structured | `#1e3a5f` | Deep blue gradient |
| H2-section | `#374151` | Dark gray |
| H3-closing | `#1e3a5f` | Deep blue gradient |
| C1-text / L25 | `#ffffff` | White |
| I1-I4 | `#ffffff` | White |

---

## Director Integration

### Feature Flag

Director v4.3 uses `USE_UNIFIED_SLIDES_API` setting (default: `True`):

```python
# config/settings.py
USE_UNIFIED_SLIDES_API: bool = Field(
    default=True,  # Use new efficient endpoints
    env="USE_UNIFIED_SLIDES_API"
)
```

### Client Methods

Director's `TextServiceClientV1_2` class provides:

```python
# New unified methods (v4.3)
await client.generate_h1_generated(slide_number, narrative, ...)
await client.generate_h1_structured(slide_number, narrative, presentation_title, ...)
await client.generate_h2_section(slide_number, narrative, section_number, ...)
await client.generate_h3_closing(slide_number, narrative, closing_message, ...)
await client.generate_c1_text(slide_number, narrative, variant_id, ...)
await client.generate_slide_unified(layout, slide_number, narrative, **kwargs)
```

### Payload Assembly

Director's `LayoutPayloadAssembler` wraps the Text Service response in Layout Service format:

```python
# Text Service returns:
{
  "slide_title": "<h2>Title</h2>",
  "subtitle": "<p>Subtitle</p>",
  "body": "<ul>...</ul>",
  "background_color": "#ffffff"
}

# Director assembles:
{
  "layout": "C1-text",
  "content": {
    "slide_title": "<h2>Title</h2>",
    "subtitle": "<p>Subtitle</p>",
    "body": "<ul>...</ul>"
  },
  "background_color": "#ffffff"
}
```

---

## Request Schemas

### C1-text Request
```json
{
  "slide_number": 3,
  "narrative": "Our solution delivers three core advantages",
  "variant_id": "bullets",
  "slide_title": "Key Benefits",
  "subtitle": "Transform your operations",
  "topics": ["50% faster", "99.9% uptime", "30% savings"],
  "content_style": "bullets",
  "context": {"audience": "executives", "tone": "professional"}
}
```

### H1-structured Request
```json
{
  "slide_number": 1,
  "narrative": "Annual company presentation",
  "presentation_title": "2024 Annual Report",
  "subtitle": "Building Tomorrow Together",
  "author_name": "Dr. Jane Smith",
  "date_info": "December 2024",
  "visual_style": "professional"
}
```

### I-series Request
```json
{
  "slide_number": 4,
  "narrative": "Our team brings diverse expertise",
  "slide_title": "Meet the Team",
  "subtitle": "Leadership & Innovation",
  "topics": ["Engineering", "Design", "Operations"],
  "visual_style": "illustrated",
  "content_style": "bullets",
  "max_bullets": 5
}
```

---

## Legacy Endpoints (Still Available)

The following endpoints are still available for backward compatibility:

### Hero Endpoints
- `POST /v1.2/hero/title` - Standard title slide
- `POST /v1.2/hero/section` - Section divider
- `POST /v1.2/hero/closing` - Closing slide
- `POST /v1.2/hero/title-with-image` - Title with AI background
- `POST /v1.2/hero/section-with-image` - Section with AI background
- `POST /v1.2/hero/closing-with-image` - Closing with AI background

### Content Endpoints
- `POST /v1.2/generate` - Main content generation (34 variants)

### Title/Subtitle Endpoints
- `POST /api/ai/slide/title` - Generate slide title
- `POST /api/ai/slide/subtitle` - Generate slide subtitle

### I-Series Endpoints
- `POST /v1.2/iseries/I1-I4` - Image + text slides

---

## Text Service Variants (34 total)

**Column Layouts**:
- sequential_2col, sequential_3col, sequential_4col, sequential_5col
- comparison_2col, comparison_3col, comparison_4col

**Grid Layouts**:
- grid_2x2, grid_2x2_centered, grid_2x3, grid_3x2, grid_3x3

**Matrix Layouts**:
- matrix_2x2, matrix_2x3, matrix_3x2

**Metrics Layouts**:
- metrics_3col, metrics_4col, metrics_5col

**Specialty Layouts**:
- timeline, process_linear, process_circular
- features_grid, benefits_grid

---

## Efficiency Summary

| Metric | Before (v1.2.1) | After (v1.2.2) | Improvement |
|--------|-----------------|----------------|-------------|
| LLM calls per content slide | 3 | 1 | **67% reduction** |
| Field mapping for I-series | Required | Not needed | Simpler code |
| H-series workarounds | Multiple approaches | Unified | Cleaner logic |
| Background color handling | Manual | Automatic | Less error-prone |

---

## Contact

For questions about this integration:
- Director Agent: `director_agent/v4.0/`
- Text Service: `text_table_builder/v1.2/`
- Spec Reference: `docs/SLIDE_GENERATION_INPUT_SPEC.md`
- Alignment Analysis: `docs/THREE_WAY_ALIGNMENT_ANALYSIS.md`
