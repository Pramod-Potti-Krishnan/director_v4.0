# Text Service API Reference

**Version**: 1.2.2
**Base URL**: `http://localhost:8000` (local) | Production via Railway
**Last Updated**: December 2024

---

## Overview

The Text Service (v1.2) provides comprehensive text, table, and slide content generation.

| Category | Endpoints | Variations | Purpose |
|----------|-----------|------------|---------|
| **Unified Slides** | 14 | 46+ | Layout Service aligned (H1, H2, H3, C1, I1-I4) |
| **Coordination** | 3 | - | Service discovery, routing |
| **Content Generation** | 3 | 34 | Variant-based content |
| **Hero Slides** | 7 | 12 | Title, section, closing |
| **I-Series** | 7 | 12 | Image + text layouts |
| **Layout/Element API** | 14 | - | Granular generation |
| **Async Jobs** | 5 | - | Job-based processing |

**Total**: 53 endpoints, 70+ generation variations

---

# PART 1: UNIFIED SLIDES API (NEW - Layout Service Aligned)

The `/v1.2/slides/*` router provides Layout Service naming conventions with enhanced responses.

## Key Innovation: Combined Generation

C1-text generates title + subtitle + body in **ONE LLM call** (saves 2 calls per slide).

---

## 1.1 POST /v1.2/slides/H1-generated

**Purpose**: Title slide with AI-generated background image (alias: L29)

### Request Schema

```json
{
  "slide_number": 1,                           // Required: int >= 1
  "narrative": "AI revolutionizing healthcare", // Required: string, min 1 char

  // Optional fields
  "topics": ["diagnosis", "treatment", "research"],  // string[]
  "context": {"audience": "executives"},             // object
  "presentation_title": "The Future of Medicine",    // string
  "subtitle": "Transforming Patient Care",           // string
  "visual_style": "illustrated",                     // "professional"|"illustrated"|"kids"
  "image_prompt_hint": "futuristic hospital"         // string - hint for image gen
}
```

### Response Schema

```json
{
  // H1-generated uses hero_content (full-slide HTML with embedded background)
  // Per SLIDE_GENERATION_INPUT_SPEC.md: no separate background_color needed
  "hero_content": "<div style='width:100%;height:100%;background:linear-gradient(135deg,#1e3a5f,#3b82f6);display:flex;align-items:center;justify-content:center;'><h1 style='color:white;font-size:72px;'>The Future of Medicine</h1></div>",
  "content": "<div>...</div>",                  // Deprecated, kept for backward compat

  // Structured fields (extracted from HTML)
  "slide_title": "<h1 style='font-size:72px;color:#ffffff;'>The Future of Medicine</h1>",
  "subtitle": "<p style='font-size:32px;color:rgba(255,255,255,0.9);'>AI-Powered Healthcare</p>",
  "background_image": "https://storage.googleapis.com/...",  // string|null (if image-based bg)
  "background_color": null,                     // NOT used for H1-generated (in hero_content)
  "image_fallback": false,                      // boolean

  // Unused for this layout type
  "author_info": null,
  "date_info": null,
  "section_number": null,
  "contact_info": null,
  "closing_message": null,

  "metadata": {
    "slide_type": "H1-generated",
    "slide_number": 1,
    "visual_style": "illustrated",
    "generation_time_ms": 12500
  }
}
```

---

## 1.2 POST /v1.2/slides/H1-structured

**Purpose**: Title slide with gradient background (no image)

### Request Schema

```json
{
  "slide_number": 1,
  "narrative": "Annual company presentation",

  // H1-structured specific fields
  "presentation_title": "2024 Annual Report",
  "subtitle": "Building Tomorrow Together",
  "author_name": "Dr. Jane Smith",             // Author/presenter
  "date_info": "December 2024",                // Date or event

  "visual_style": "professional",
  "context": {"company": "TechCorp Inc"}
}
```

### Response Schema

```json
{
  "content": "<div style='...'>Complete HTML...</div>",  // Full HTML (for backward compat)

  // All text fields are HTML with inline CSS (per SLIDE_GENERATION_INPUT_SPEC.md)
  "slide_title": "<h1 style='font-size:72px;color:#ffffff;font-weight:700;'>2024 Annual Report</h1>",
  "subtitle": "<p style='font-size:32px;color:rgba(255,255,255,0.9);'>Building Tomorrow Together</p>",
  "author_info": "<div style='font-size:18px;color:rgba(255,255,255,0.7);'>Dr. Jane Smith <span style='opacity:0.7'>| December 2024</span></div>",
  "date_info": "<span style='font-size:16px;color:rgba(255,255,255,0.6);'>December 2024</span>",

  // CRITICAL: Background color for H1-structured (per SPEC)
  "background_color": "#1e3a5f",                // Default per SPEC
  "background_image": null,                     // Optional
  "image_fallback": false,                      // Always false (no image)

  "metadata": {
    "slide_type": "H1-structured",
    "slide_number": 1,
    "generation_time_ms": 2800
  }
}
```

---

## 1.3 POST /v1.2/slides/H2-section

**Purpose**: Section divider slide

### Request Schema

```json
{
  "slide_number": 5,
  "narrative": "Implementation roadmap overview",

  // H2-section specific fields
  "section_number": "02",                       // "01", "02", etc.
  "section_title": "Implementation",            // Section title

  "visual_style": "professional",
  "topics": ["Timeline", "Resources", "Milestones"]
}
```

### Response Schema

```json
{
  "content": "<div style='...'>Section divider HTML...</div>",  // Full HTML (for backward compat)

  // All text fields are HTML with inline CSS (per SLIDE_GENERATION_INPUT_SPEC.md)
  "slide_title": "<h2 style='font-size:48px;color:#ffffff;'>Implementation</h2>",
  "section_number": "<span style='font-size:120px;font-weight:800;color:#fbbf24;'>02</span>",
  "subtitle": "<p style='font-size:24px;color:rgba(255,255,255,0.8);'>Roadmap Overview</p>",

  // CRITICAL: Background color for H2-section (per SPEC)
  "background_color": "#374151",                // Default per SPEC (darker gray)
  "background_image": null,                     // Optional

  "metadata": {
    "slide_type": "H2-section",
    "slide_number": 5,
    "generation_time_ms": 2200
  }
}
```

---

## 1.4 POST /v1.2/slides/H3-closing

**Purpose**: Closing slide with contact information

### Request Schema

```json
{
  "slide_number": 12,
  "narrative": "Thank you and contact details",

  // H3-closing specific fields
  "closing_message": "Thank You",               // "Thank You", "Questions?", etc.
  "contact_email": "contact@example.com",
  "contact_phone": "+1 (555) 123-4567",
  "website_url": "https://example.com",

  "visual_style": "professional"
}
```

### Response Schema

```json
{
  "content": "<div style='...'>Closing slide HTML...</div>",  // Full HTML (for backward compat)

  // All text fields are HTML with inline CSS (per SLIDE_GENERATION_INPUT_SPEC.md)
  "slide_title": "<h1 style='font-size:72px;color:#ffffff;'>Thank You</h1>",
  "subtitle": "<p style='font-size:28px;color:rgba(255,255,255,0.9);'>Questions & Discussion</p>",
  "closing_message": "<p style='font-size:24px;color:rgba(255,255,255,0.8);'>Thank You</p>",
  "contact_info": "<div style='font-size:20px;'><a href='mailto:contact@example.com' style='color:#93c5fd;'>contact@example.com</a> <span style='opacity:0.6'>|</span> <span style='color:rgba(255,255,255,0.8);'>example.com</span></div>",

  // CRITICAL: Background color for H3-closing (per SPEC)
  "background_color": "#1e3a5f",                // Default per SPEC
  "background_image": null,                     // Optional

  "metadata": {
    "slide_type": "H3-closing",
    "slide_number": 12,
    "generation_time_ms": 2400
  }
}
```

---

## 1.5 POST /v1.2/slides/C1-text

**Purpose**: Content slide with COMBINED generation (1 LLM call instead of 3)

### Request Schema

```json
{
  "slide_number": 3,
  "narrative": "Our solution delivers three core advantages",

  // C1-text specific fields
  "variant_id": "bullets",                      // One of 34 variants (see list below)
  "slide_title": "Key Benefits",                // Optional override (otherwise generated)
  "subtitle": "Transform your operations",      // Optional override
  "content_style": "bullets",                   // "bullets"|"paragraphs"|"mixed"

  "topics": ["50% faster", "99.9% uptime", "30% savings"],
  "context": {"audience": "executives", "tone": "professional"}
}
```

### Supported variant_id Values (34 total)

| Category | variant_id values |
|----------|-------------------|
| **Matrix** | `matrix_2x2`, `matrix_2x3` |
| **Grid** | `grid_2x3`, `grid_3x2`, `grid_2x2_centered`, `grid_2x3_left`, `grid_3x2_left`, `grid_2x2_left`, `grid_2x3_numbered`, `grid_3x2_numbered`, `grid_2x2_numbered` |
| **Comparison** | `comparison_2col`, `comparison_3col`, `comparison_4col` |
| **Sequential** | `sequential_3col`, `sequential_4col`, `sequential_5col` |
| **Asymmetric** | `asymmetric_8_4_3section`, `asymmetric_8_4_4section`, `asymmetric_8_4_5section` |
| **Hybrid** | `hybrid_top_2x2`, `hybrid_left_2x2` |
| **Metrics** | `metrics_3col`, `metrics_4col`, `metrics_3x2_grid`, `metrics_2x2_grid` |
| **Impact Quote** | `impact_quote` |
| **Table** | `table_2col`, `table_3col`, `table_4col`, `table_5col` |
| **Single Column** | `single_column_3section`, `single_column_4section`, `single_column_5section` |
| **Default** | `bullets` (simple bullet list) |

### Response Schema

```json
{
  // All text fields are HTML with inline CSS (per SLIDE_GENERATION_INPUT_SPEC.md)
  "slide_title": "<h2 style='font-size:42px;font-weight:600;'>Key Benefits of Integration</h2>",
  "subtitle": "<p style='font-size:24px;color:#6b7280;'>Transform operations with AI</p>",
  "body": "<ul class='content-list' style='list-style-type:disc;margin-left:24px;'><li>50% faster processing</li>...</ul>",
  "rich_content": "<ul class='content-list'>...</ul>",  // Alias for body (L25)
  "html": null,                                   // Optional assembled HTML

  // CRITICAL: Background color for C1-text (per SPEC)
  "background_color": "#ffffff",                  // Default per SPEC (white)
  "background_image": null,                       // Optional

  "metadata": {
    "slide_type": "C1-text",
    "slide_number": 3,
    "llm_calls": 1,                              // KEY: Only 1 call (not 3)
    "generation_mode": "combined",
    "variant_id": "bullets",
    "variant_description": "Simple bullet list",
    "content_style": "bullets",
    "title_length": 28,
    "subtitle_length": 32,
    "body_length": 245,
    "generation_time_ms": 2100
  }
}
```

---

## 1.6 POST /v1.2/slides/I1 through /I4

**Purpose**: Image + text side-by-side layouts

### Layout Specifications

| Layout | Image Position | Image Size | Content Area |
|--------|---------------|------------|--------------|
| **I1** | Left (wide) | 660×1080px | 1200×840px |
| **I2** | Right (wide) | 660×1080px | 1140×840px |
| **I3** | Left (narrow) | 360×1080px | 1500×840px |
| **I4** | Right (narrow) | 360×1080px | 1440×840px |

### Request Schema (same for I1, I2, I3, I4)

```json
{
  "slide_number": 4,
  "narrative": "Our team brings diverse expertise",

  // I-series fields
  "slide_title": "Meet the Team",               // Optional (otherwise from narrative)
  "subtitle": "Leadership & Innovation",        // Optional
  "topics": ["Engineering", "Design", "Operations"],
  "max_bullets": 5,                             // 3-8, default 5

  // Image configuration
  "visual_style": "illustrated",                // "professional"|"illustrated"|"kids"
  "image_prompt_hint": "professional team",     // Optional hint

  // Content configuration
  "content_style": "bullets",                   // "bullets"|"paragraphs"|"mixed"

  "context": {"company": "TechCorp"}
}
```

### Response Schema (ISeriesSlideResponse)

```json
{
  // HTML slots - ALL with inline CSS (per SLIDE_GENERATION_INPUT_SPEC.md)
  "image_html": "<div style='width:100%;height:100%'><img src='...' style='width:100%;height:100%;object-fit:cover'/></div>",
  "title_html": "<h2 style='font-size:2.5rem;font-weight:600;color:#1f2937;'>Meet the Team</h2>",
  "subtitle_html": "<p style='font-size:1.25rem;color:#6b7280;'>Leadership & Innovation</p>",
  "content_html": "<ul class='content-list' style='list-style-type:disc;margin-left:24px;'><li>Engineering excellence</li>...</ul>",

  // Image metadata
  "image_url": "https://storage.googleapis.com/deckster-hero-images/...",
  "image_fallback": false,

  // Layout Service aliases - also HTML with inline CSS
  "slide_title": "<h2 style='font-size:2.5rem;font-weight:600;color:#1f2937;'>Meet the Team</h2>",
  "subtitle": "<p style='font-size:1.25rem;color:#6b7280;'>Leadership & Innovation</p>",
  "body": "<ul class='content-list' style='list-style-type:disc;margin-left:24px;'>...</ul>",

  // CRITICAL: Background color for I-series (per SPEC)
  "background_color": "#ffffff",                // Default per SPEC (white)
  // background_image NOT recommended (conflicts with layout's primary image)

  "metadata": {
    "layout_type": "I1",
    "slide_number": 4,
    "image_position": "left",
    "image_dimensions": {"width": 660, "height": 1080},
    "content_dimensions": {"width": 1200, "height": 840},
    "visual_style": "illustrated",
    "content_style": "bullets",
    "generation_time_ms": 13500
  }
}
```

---

## 1.7 POST /v1.2/slides/L29

**Purpose**: Alias for H1-generated (backward compatibility)

Request/Response: Same as `/v1.2/slides/H1-generated`

---

## 1.8 POST /v1.2/slides/L25

**Purpose**: Alias for C1-text (backward compatibility)

Request/Response: Same as `/v1.2/slides/C1-text`

---

## 1.9 GET /v1.2/slides/health

**Purpose**: Health check for slides router

### Response

```json
{
  "status": "healthy",
  "router": "/v1.2/slides",
  "version": "1.2.1",
  "features": {
    "combined_generation": true,
    "structured_fields": true,
    "layout_aliases": ["L29", "L25"]
  },
  "layouts": {
    "h_series": ["H1-generated", "H1-structured", "H2-section", "H3-closing"],
    "c_series": ["C1-text"],
    "i_series": ["I1", "I2", "I3", "I4"],
    "aliases": {"L29": "H1-generated", "L25": "C1-text"}
  }
}
```

---

## 1.10 GET /v1.2/slides/layouts

**Purpose**: List all layout specifications

### Response

```json
{
  "h_series": {
    "H1-generated": {
      "description": "Title slide with AI-generated background image",
      "alias": "L29",
      "features": ["background_image", "slide_title", "subtitle"]
    },
    "H1-structured": {...},
    "H2-section": {...},
    "H3-closing": {...}
  },
  "c_series": {
    "C1-text": {
      "description": "Content slide with combined generation",
      "alias": "L25",
      "features": ["slide_title", "subtitle", "body", "rich_content"],
      "innovation": "Single LLM call for title+subtitle+body (saves 2 calls)",
      "variants": 34,
      "variant_categories": ["matrix", "grid", "comparison", ...]
    }
  },
  "i_series": {
    "I1": {"image_position": "left", "image_width": 660, ...},
    "I2": {...},
    "I3": {...},
    "I4": {...}
  },
  "aliases": {"L29": "H1-generated", "L25": "C1-text"},
  "total_endpoints": 12,
  "total_variants": 46
}
```

---

## 1.11 GET /v1.2/slides/variants

**Purpose**: List all C1-text variants by category

### Response

```json
{
  "total": 34,
  "categories": {
    "matrix": ["matrix_2x2", "matrix_2x3"],
    "grid": ["grid_2x3", "grid_3x2", ...],
    "comparison": ["comparison_2col", "comparison_3col", "comparison_4col"],
    ...
  },
  "variants": {
    "matrix_2x2": {
      "description": "2x2 matrix with 4 cells",
      "body_template": "4 cells with title + description each"
    },
    "grid_2x3": {...},
    ...
  }
}
```

---

# PART 2: DIRECTOR COORDINATION ENDPOINTS

## 2.1 GET /v1.2/capabilities

**Purpose**: Service discovery - what can this service do?

### Response Schema

```json
{
  "service": "text-service",
  "version": "1.2.2",
  "status": "healthy",
  "capabilities": {
    "slide_types": ["matrix", "grid", "comparison", "sequential", "asymmetric",
                   "hybrid", "metrics", "impact_quote", "table", "single_column"],
    "variants": ["matrix_2x2", "matrix_2x3", "grid_2x3", ...],  // All 34
    "max_items_per_slide": 8,
    "supports_themes": false,
    "parallel_generation": true
  },
  "content_signals": {
    "handles_well": ["structured_content", "bullet_points", "comparisons",
                    "process_steps", "metrics_display", "tables"],
    "handles_poorly": ["charts", "data_visualization", "diagrams",
                      "complex_graphics", "icons", "images"],
    "keywords": ["compare", "versus", "benefits", "features", "steps",
                "process", "list", "overview", "summary"]
  },
  "endpoints": {
    // Coordination
    "capabilities": "GET /v1.2/capabilities",
    "generate": "POST /v1.2/generate",
    "can_handle": "POST /v1.2/can-handle",
    "recommend_variant": "POST /v1.2/recommend-variant",

    // UNIFIED SLIDES API (RECOMMENDED - Layout Service aligned)
    "slides_H1_generated": "POST /v1.2/slides/H1-generated",
    "slides_H1_structured": "POST /v1.2/slides/H1-structured",
    "slides_H2_section": "POST /v1.2/slides/H2-section",
    "slides_H3_closing": "POST /v1.2/slides/H3-closing",
    "slides_C1_text": "POST /v1.2/slides/C1-text",
    "slides_I1": "POST /v1.2/slides/I1",
    "slides_I2": "POST /v1.2/slides/I2",
    "slides_I3": "POST /v1.2/slides/I3",
    "slides_I4": "POST /v1.2/slides/I4",
    "slides_L29": "POST /v1.2/slides/L29",
    "slides_L25": "POST /v1.2/slides/L25",

    // DEPRECATED (use unified slides instead, removal ~March 2025)
    "hero_title": "POST /v1.2/hero/title-with-image",
    "hero_section": "POST /v1.2/hero/section-with-image",
    "hero_closing": "POST /v1.2/hero/closing-with-image",
    "iseries_generate": "POST /v1.2/iseries/generate",
    "iseries_I1": "POST /v1.2/iseries/I1",
    "iseries_I2": "POST /v1.2/iseries/I2",
    "iseries_I3": "POST /v1.2/iseries/I3",
    "iseries_I4": "POST /v1.2/iseries/I4",

    // Element-level
    "element_text": "POST /api/ai/element/text",
    "table_generate": "POST /api/ai/table/generate"
  }
}
```

> **Note**: The `endpoints` object now groups endpoints by category. The **UNIFIED SLIDES API** endpoints (Part 1) are the recommended choice for new integrations. Legacy hero and I-series endpoints remain available but are deprecated.

---

## 2.2 POST /v1.2/can-handle

**Purpose**: Content negotiation - can service handle this content?

### Request Schema

```json
{
  "slide_content": {
    "title": "Q4 Revenue Analysis",
    "topics": ["Revenue grew 15%", "New markets +30%", "Cost reduction"],
    "topic_count": 3
  },
  "content_hints": {
    "has_numbers": true,
    "is_comparison": false,
    "detected_keywords": ["revenue", "growth"]
  },
  "available_space": {
    "width": 1800,
    "height": 750,
    "layout_id": "C01"
  }
}
```

### Response Schema

```json
{
  "can_handle": true,
  "confidence": 0.85,
  "reason": "3 metrics items - confidence 0.85",
  "suggested_approach": "metrics",
  "space_utilization": {
    "fits_well": true,
    "estimated_fill_percent": 85
  }
}
```

---

## 2.3 POST /v1.2/recommend-variant

**Purpose**: Get variant recommendations for content

### Request Schema

```json
{
  "slide_content": {
    "title": "Feature Comparison",
    "topics": ["Basic", "Pro", "Enterprise"],
    "topic_count": 3
  },
  "content_hints": {
    "is_comparison": true
  },
  "available_space": {
    "width": 1600,
    "height": 600
  }
}
```

### Response Schema

```json
{
  "recommended_variants": [
    {
      "variant_id": "comparison_3col",
      "confidence": 0.95,
      "reason": "3-column comparison perfect for 3 items",
      "requires_space": {"width": 1600, "height": 500}
    },
    {
      "variant_id": "grid_3x2",
      "confidence": 0.75,
      "reason": "Alternative grid layout",
      "requires_space": {"width": 1600, "height": 700}
    }
  ],
  "not_recommended": [
    {
      "variant_id": "matrix_2x2",
      "reason": "Needs 4 topics, only 3 provided"
    }
  ]
}
```

---

# PART 3: CONTENT GENERATION ENDPOINTS

## 3.1 POST /v1.2/generate

**Purpose**: Generate content using any of 34 variants

### Request Schema

```json
{
  "variant_id": "matrix_2x2",                   // Required: one of 34 variants
  "layout_id": "L25",                           // Optional: layout ID for context

  "slide_spec": {                               // Required
    "slide_id": "slide_003",
    "slide_number": 3,
    "slide_title": "SWOT Analysis",
    "narrative": "Comprehensive analysis of our market position",
    "topics": ["Strengths", "Weaknesses", "Opportunities", "Threats"]
  },

  "presentation_spec": {                        // Optional
    "presentation_id": "pres_12345",
    "theme": "professional",
    "audience": "executives",
    "tone": "data-driven"
  },

  "element_relationships": [],                  // Optional: element dependencies
  "validate_character_counts": true             // Optional: enable validation
}
```

### Response Schema

```json
{
  "success": true,
  "html": "<div class='matrix-grid'>...assembled HTML...</div>",
  "elements": [
    {
      "element_id": "cell_1",
      "content": "Our strong market presence...",
      "type": "text"
    },
    {
      "element_id": "cell_2",
      "content": "Limited resources in...",
      "type": "text"
    }
  ],
  "metadata": {
    "variant_id": "matrix_2x2",
    "template_path": "app/templates/matrix_2x2.html",
    "generation_time_ms": 3200,
    "llm_calls": 4,
    "parallel_generation": true
  },
  "validation": {
    "valid": true,
    "violations": []
  },
  "variant_id": "matrix_2x2",
  "template_path": "app/templates/matrix_2x2.html"
}
```

---

## 3.2 GET /v1.2/variants

**Purpose**: List all available variants

### Response Schema

```json
{
  "count": 34,
  "variants": [
    {
      "variant_id": "matrix_2x2",
      "slide_type": "matrix",
      "description": "2x2 matrix layout",
      "min_items": 4,
      "max_items": 4,
      "requires_space": {"width": 1200, "height": 600}
    },
    ...
  ]
}
```

---

## 3.3 GET /v1.2/variant/{variant_id}

**Purpose**: Get details for specific variant

### Response Schema

```json
{
  "variant_id": "comparison_3col",
  "slide_type": "comparison",
  "description": "3-column comparison layout",
  "min_items": 3,
  "max_items": 3,
  "requires_space": {"width": 1600, "height": 500},
  "element_specs": {
    "header_1": {"type": "title", "max_chars": 30},
    "header_2": {"type": "title", "max_chars": 30},
    "header_3": {"type": "title", "max_chars": 30},
    "content_1": {"type": "bullets", "max_items": 5},
    "content_2": {"type": "bullets", "max_items": 5},
    "content_3": {"type": "bullets", "max_items": 5}
  }
}
```

---

# PART 4: HERO SLIDE ENDPOINTS (DEPRECATED)

> **DEPRECATION NOTICE**: The endpoints in this section are deprecated and scheduled for removal around **March 2025** (~3 months). These endpoints remain fully functional for backward compatibility but should not be used in new integrations.
>
> **Migration Path**:
> | Deprecated Endpoint | Replacement Endpoint |
> |---------------------|---------------------|
> | `/v1.2/hero/title` | `/v1.2/slides/H1-structured` |
> | `/v1.2/hero/title-with-image` | `/v1.2/slides/H1-generated` |
> | `/v1.2/hero/section` | `/v1.2/slides/H2-section` |
> | `/v1.2/hero/section-with-image` | `/v1.2/slides/H2-section` |
> | `/v1.2/hero/closing` | `/v1.2/slides/H3-closing` |
> | `/v1.2/hero/closing-with-image` | `/v1.2/slides/H3-closing` |
>
> The replacement endpoints (Part 1) return structured fields (`slide_title`, `subtitle`, `background_color`, etc.) that align directly with the Layout Service SPEC, eliminating the need for field extraction.

---

## 4.1 POST /v1.2/hero/title (DEPRECATED)

**Purpose**: Title slide with gradient background

**Deprecation**: Use `/v1.2/slides/H1-structured` instead (see Part 1.2)

### Request Schema

```json
{
  "slide_number": 1,
  "slide_type": "title_slide",
  "narrative": "Company annual overview presentation",
  "topics": ["growth", "innovation", "future"],
  "context": {
    "presentation_title": "2024 Annual Report",
    "subtitle": "Building Tomorrow",
    "theme": "professional",
    "audience": "investors"
  },
  "visual_style": "professional"
}
```

### Response Schema

```json
{
  "content": "<div style='width:100%;height:100%;background:linear-gradient(135deg,#1a1a2e,#16213e);...'><h1>2024 Annual Report</h1>...</div>",
  "metadata": {
    "slide_type": "title_slide",
    "slide_number": 1,
    "validation": {"valid": true, "violations": [], "warnings": []},
    "generation_mode": "hero_slide_async"
  }
}
```

---

## 4.2 POST /v1.2/hero/section (DEPRECATED)

**Purpose**: Section divider with gradient

**Deprecation**: Use `/v1.2/slides/H2-section` instead (see Part 1.3)

### Request Schema

```json
{
  "slide_number": 5,
  "slide_type": "section_divider",
  "narrative": "Financial performance review",
  "topics": ["revenue", "profit", "growth"],
  "context": {
    "section_number": "02",
    "section_title": "Financial Results"
  },
  "visual_style": "professional"
}
```

---

## 4.3 POST /v1.2/hero/closing (DEPRECATED)

**Purpose**: Closing slide with gradient

**Deprecation**: Use `/v1.2/slides/H3-closing` instead (see Part 1.4)

### Request Schema

```json
{
  "slide_number": 15,
  "slide_type": "closing_slide",
  "narrative": "Thank you and next steps",
  "topics": [],
  "context": {
    "contact_email": "contact@company.com",
    "contact_phone": "+1-555-123-4567",
    "website_url": "https://company.com"
  },
  "visual_style": "professional"
}
```

---

## 4.4 POST /v1.2/hero/title-with-image (DEPRECATED)

**Purpose**: Title slide with AI-generated background

**Deprecation**: Use `/v1.2/slides/H1-generated` instead (see Part 1.1)

### Request Schema

```json
{
  "slide_number": 1,
  "slide_type": "title_slide",
  "narrative": "Healthcare innovation summit keynote",
  "topics": ["AI", "diagnostics", "patient care"],
  "context": {
    "presentation_title": "The Future of Medicine",
    "subtitle": "AI-Powered Healthcare",
    "domain": "healthcare"
  },
  "visual_style": "illustrated"           // "professional"|"illustrated"|"kids"
}
```

### Response Schema

```json
{
  "content": "<div style='...background-image:url(https://storage.googleapis.com/...)'><h1>The Future of Medicine</h1>...</div>",
  "metadata": {
    "slide_type": "title_slide",
    "slide_number": 1,
    "image_url": "https://storage.googleapis.com/deckster-hero-images/...",
    "image_fallback": false,
    "visual_style": "illustrated",
    "generation_mode": "hero_slide_with_image",
    "image_generation_time_ms": 8500,
    "total_generation_time_ms": 11200
  }
}
```

---

## 4.5 POST /v1.2/hero/section-with-image (DEPRECATED)

**Purpose**: Section divider with AI background

**Deprecation**: Use `/v1.2/slides/H2-section` instead (see Part 1.3)

Same request/response pattern as title-with-image.

---

## 4.6 POST /v1.2/hero/closing-with-image (DEPRECATED)

**Purpose**: Closing slide with AI background

**Deprecation**: Use `/v1.2/slides/H3-closing` instead (see Part 1.4)

Same request/response pattern as title-with-image.

---

## 4.7 GET /v1.2/hero/health

**Purpose**: Hero service health check

### Response

```json
{
  "status": "healthy",
  "service": "hero-slides",
  "endpoints": {
    "standard": ["/title", "/section", "/closing"],
    "image_enhanced": ["/title-with-image", "/section-with-image", "/closing-with-image"]
  },
  "visual_styles": ["professional", "illustrated", "kids"],
  "image_service": "connected"
}
```

---

# PART 5: I-SERIES ENDPOINTS

## 5.1 POST /v1.2/iseries/generate

**Purpose**: Generate any I-series layout (layout_type in body)

### Request Schema

```json
{
  "slide_number": 4,
  "layout_type": "I1",                          // "I1"|"I2"|"I3"|"I4"
  "title": "Key Benefits",
  "narrative": "Our solution provides three advantages",
  "topics": ["Speed", "Reliability", "Cost"],
  "subtitle": "Why Choose Us",

  "image_prompt_hint": "modern technology abstract",
  "visual_style": "illustrated",                // "professional"|"illustrated"|"kids"

  "content_style": "bullets",                   // "bullets"|"paragraphs"|"mixed"
  "max_bullets": 5,                             // 3-8

  "context": {
    "theme": "professional",
    "audience": "business executives"
  }
}
```

### Response Schema

```json
{
  "image_html": "<div style='width:100%;height:100%'><img src='https://...' style='width:100%;height:100%;object-fit:cover'/></div>",
  "title_html": "<h2 style='font-size:2.5rem;font-weight:600;color:#1a1a2e'>Key Benefits</h2>",
  "subtitle_html": "<p style='font-size:1.25rem;color:#6b7280'>Why Choose Us</p>",
  "content_html": "<ul class='content-list' style='list-style-type:disc'><li>50% faster processing times</li><li>99.9% uptime guarantee</li><li>30% cost reduction</li></ul>",

  "image_url": "https://storage.googleapis.com/deckster-hero-images/...",
  "image_fallback": false,

  "metadata": {
    "layout_type": "I1",
    "slide_number": 4,
    "image_position": "left",
    "image_dimensions": {"width": 660, "height": 1080},
    "content_dimensions": {"width": 1200, "height": 840},
    "visual_style": "illustrated",
    "content_style": "bullets",
    "image_generation_time_ms": 8200,
    "content_generation_time_ms": 2100,
    "total_generation_time_ms": 10500
  }
}
```

---

## 5.2-5.5 POST /v1.2/iseries/I1, /I2, /I3, /I4

**Purpose**: Generate specific I-series layout (layout_type implied by endpoint)

Same request schema as `/generate` but without `layout_type` field.

---

## 5.6 GET /v1.2/iseries/health

**Purpose**: I-series service health

### Response

```json
{
  "status": "healthy",
  "service": "i-series",
  "layouts": ["I1", "I2", "I3", "I4"],
  "visual_styles": ["professional", "illustrated", "kids"],
  "content_styles": ["bullets", "paragraphs", "mixed"],
  "image_service": "connected"
}
```

---

## 5.7 GET /v1.2/iseries/layouts

**Purpose**: Get all layout specifications

### Response

```json
{
  "I1": {
    "image_position": "left",
    "image_width": 660,
    "image_height": 1080,
    "content_width": 1200,
    "content_height": 840,
    "description": "Wide image left, content right"
  },
  "I2": {...},
  "I3": {...},
  "I4": {...}
}
```

---

# PART 6: LAYOUT/ELEMENT API ENDPOINTS

## 6.1 POST /api/ai/text/generate

**Purpose**: Generate text with grid constraints

### Request Schema

```json
{
  "prompt": "Write an introduction about cloud computing benefits",
  "grid_width": 16,                             // Grid units (1-32)
  "grid_height": 6,                             // Grid units (1-18)
  "text_type": "paragraph",                     // "title"|"subtitle"|"paragraph"|"bullets"
  "max_chars": 400,                             // Optional override
  "context": {
    "audience": "executives",
    "tone": "professional"
  }
}
```

### Response Schema

```json
{
  "content": "<p>Cloud computing transforms how organizations operate...</p>",
  "text_type": "paragraph",
  "char_count": 285,
  "fits_grid": true,
  "metadata": {
    "grid_constraints": {"width": 16, "height": 6},
    "max_chars_calculated": 480,
    "generation_time_ms": 1200
  }
}
```

---

## 6.2 POST /api/ai/text/transform

**Purpose**: Transform existing text

### Request Schema

```json
{
  "original_text": "Cloud computing provides many benefits including cost savings, scalability, and flexibility.",
  "transformation": "expand",                   // "expand"|"condense"|"rephrase"|"simplify"
  "target_chars": 300,
  "preserve_meaning": true
}
```

### Response Schema

```json
{
  "transformed_text": "Cloud computing revolutionizes business operations through significant cost savings, seamless scalability that grows with your needs, and unprecedented flexibility in resource allocation.",
  "original_chars": 89,
  "new_chars": 175,
  "transformation_applied": "expand"
}
```

---

## 6.3 POST /api/ai/text/autofit

**Purpose**: Fit text to element dimensions

### Request Schema

```json
{
  "text": "Long text that needs to fit...",
  "grid_width": 12,
  "grid_height": 4,
  "strategy": "truncate"                        // "truncate"|"summarize"|"split"
}
```

---

## 6.4-6.8 Slide-Specific Text Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/ai/slide/title` | Generate h2 title (60 chars max) |
| `POST /api/ai/slide/subtitle` | Generate subtitle (100 chars max) |
| `POST /api/ai/slide/title-slide` | Complete title slide content |
| `POST /api/ai/slide/section` | Section divider content |
| `POST /api/ai/slide/closing` | Closing slide content |

### Common Request Schema

```json
{
  "narrative": "Topic description",
  "context": {"theme": "professional"},
  "grid_width": 24,
  "grid_height": 3
}
```

---

## 6.9 POST /api/ai/element/text

**Purpose**: Generic text element for any grid position

### Request Schema

```json
{
  "prompt": "Create a compelling value proposition",
  "grid_width": 10,
  "grid_height": 8,
  "element_type": "content_box",                // "title"|"subtitle"|"content_box"|"bullet_list"
  "context": {"slide_title": "Our Value"}
}
```

---

## 6.10-6.12 Table Endpoints

### POST /api/ai/table/generate

```json
{
  "prompt": "Create pricing comparison for 3 tiers",
  "columns": ["Feature", "Basic", "Pro", "Enterprise"],
  "row_count": 5,
  "grid_width": 20,
  "grid_height": 10
}
```

### POST /api/ai/table/transform

```json
{
  "table_html": "<table>...</table>",
  "transformation": "add_column",
  "column_name": "Premium"
}
```

### POST /api/ai/table/analyze

```json
{
  "table_html": "<table>...</table>",
  "analysis_type": "summary"                    // "summary"|"trends"|"insights"
}
```

---

## 6.13-6.14 Utility Endpoints

### GET /api/ai/health

```json
{"status": "healthy", "service": "layout-ai"}
```

### GET /api/ai/constraints/{grid_width}/{grid_height}

```json
{
  "grid_width": 12,
  "grid_height": 6,
  "pixel_width": 720,
  "pixel_height": 360,
  "recommended_chars": 400,
  "max_chars": 500
}
```

---

# PART 7: ASYNC JOB ENDPOINTS

## 7.1 POST /v1.2/async/generate

**Purpose**: Submit async generation job

### Request Schema

```json
{
  "job_type": "content",                        // "content"|"hero"|"iseries"
  "request_data": {
    "variant_id": "matrix_2x2",
    "slide_spec": {...}
  },
  "priority": "normal",                         // "low"|"normal"|"high"
  "callback_url": "https://..."                 // Optional webhook
}
```

### Response Schema

```json
{
  "job_id": "job_abc123xyz",
  "status": "queued",
  "estimated_time_seconds": 5,
  "poll_url": "/v1.2/async/status/job_abc123xyz"
}
```

---

## 7.2 GET /v1.2/async/status/{job_id}

### Response Schema

```json
{
  "job_id": "job_abc123xyz",
  "status": "processing",                       // "queued"|"processing"|"completed"|"failed"
  "progress": 0.6,
  "created_at": "2024-12-19T10:00:00Z",
  "started_at": "2024-12-19T10:00:02Z"
}
```

---

## 7.3 GET /v1.2/async/result/{job_id}

### Response (when completed)

```json
{
  "job_id": "job_abc123xyz",
  "status": "completed",
  "result": {
    "success": true,
    "html": "...",
    "metadata": {...}
  },
  "completed_at": "2024-12-19T10:00:05Z"
}
```

---

## 7.4 DELETE /v1.2/async/job/{job_id}

### Response

```json
{
  "job_id": "job_abc123xyz",
  "cancelled": true
}
```

---

## 7.5 GET /v1.2/async/queue/stats

### Response

```json
{
  "queue_length": 12,
  "processing": 3,
  "completed_last_hour": 145,
  "failed_last_hour": 2,
  "average_processing_time_ms": 3200
}
```

---

# APPENDIX A: Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error message describing the issue",
  "status_code": 400,
  "error_type": "validation_error"
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad Request - Invalid input |
| 404 | Not Found - Variant or resource not found |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |
| 504 | Gateway Timeout - LLM timeout |

---

# APPENDIX B: Visual Styles Reference

| Style | Archetype | Use Case |
|-------|-----------|----------|
| `professional` | photorealistic | Corporate, business, formal |
| `illustrated` | spot_illustration | Creative, engaging, Ghibli-style |
| `kids` | spot_illustration | Educational, playful, children |

---

# APPENDIX C: Quick Reference

## Recommended Endpoints by Use Case

| Use Case | Recommended Endpoint |
|----------|---------------------|
| Title slide with image | `POST /v1.2/slides/H1-generated` |
| Title slide (gradient) | `POST /v1.2/slides/H1-structured` |
| Section divider | `POST /v1.2/slides/H2-section` |
| Closing slide | `POST /v1.2/slides/H3-closing` |
| Content (bullets, grid, etc.) | `POST /v1.2/slides/C1-text` |
| Image + text (left) | `POST /v1.2/slides/I1` or `/I3` |
| Image + text (right) | `POST /v1.2/slides/I2` or `/I4` |
| Layout Service L29 | `POST /v1.2/slides/L29` |
| Layout Service L25 | `POST /v1.2/slides/L25` |

---

# APPENDIX D: LLM Call Efficiency

| Endpoint | LLM Calls | Savings |
|----------|-----------|---------|
| `/v1.2/slides/C1-text` | 1 | 67% vs separate title+subtitle+body |
| `/v1.2/generate` (old) | 1-4 | Per element |
| Hero slides | 1 | - |
| I-series | 2 | Image + content in parallel |

**For a 10-slide deck with 6 content slides:**
- Old approach: 18 LLM calls (3 per content slide)
- New C1-text: 6 LLM calls (1 per content slide)
- **Savings: 12 LLM calls per deck**

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.2.2 | Dec 2024 | Added unified /v1.2/slides/* router with complete contracts |
| 1.2.1 | Dec 2024 | Added I-series, Layout/Element API documentation |
| 1.2.0 | Dec 2024 | Initial v1.2 with coordination endpoints |
