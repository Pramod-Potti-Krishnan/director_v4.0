# Illustrator Service API Reference

**Version**: 1.0.1
**Base URL**: `http://localhost:8000` (local) | Production via Railway
**Last Updated**: December 2024

---

## Overview

The Illustrator Service (v1.0) provides visual infographic generation with template-based and dynamic SVG modes.

| Category | Endpoints | Purpose |
|----------|-----------|---------|
| **Director Coordination** | 3 | Service discovery, content routing |
| **Visual Generation** | 5 | Pyramid, funnel, concentric, concept spread |
| **Layout Service** | 4 | Unified generation, type metadata |
| **Root & Metadata** | 7 | Health, templates, themes, sizes |

**Total**: 19 endpoints, 14 visualization types

**Best For**: Hierarchies, levels, stages, layers, visual metaphors, organizational structures

**Not Ideal For**: Data-heavy content, charts, time series, detailed statistics

---

# PART 1: DIRECTOR COORDINATION ENDPOINTS

The Director Agent uses these 3 endpoints for intelligent service routing.

## 1.1 GET /capabilities

**Purpose**: Service discovery - what can this service do?

### Response Schema

```json
{
  "service": "illustrator-service",
  "version": "1.0.0",
  "status": "healthy",
  "capabilities": {
    "slide_types": ["infographic", "visual_metaphor"],
    "visualization_types": ["pyramid", "funnel", "concentric_circles"],
    "supports_themes": true,
    "ai_generated_content": true,
    "supported_layouts": ["L25", "L01", "L02"]
  },
  "content_signals": {
    "handles_well": [
      "hierarchies", "levels", "stages", "layers", "visual_metaphors",
      "progressions", "funnels", "concentric_concepts",
      "organizational_structures", "tiered_systems"
    ],
    "handles_poorly": [
      "data_heavy_content", "many_items", "tabular_data", "time_series",
      "numerical_comparisons", "charts", "graphs", "detailed_statistics"
    ],
    "keywords": [
      "pyramid", "funnel", "hierarchy", "levels", "stages",
      "core", "layers", "ecosystem", "tier", "foundation",
      "conversion", "pipeline", "narrowing", "concentric",
      "stakeholder", "organizational", "priority", "influence"
    ]
  },
  "specializations": {
    "pyramid": {
      "description": "Hierarchical structure from foundation to peak",
      "best_for": [
        "hierarchy", "levels", "foundation to peak", "priority",
        "organizational tiers", "strategic layers", "needs hierarchy (Maslow)"
      ],
      "keywords": [
        "pyramid", "levels", "hierarchy", "tier", "foundation",
        "top-down", "layers", "base", "peak", "strategic",
        "organizational", "priority", "structure"
      ],
      "ideal_item_count": {"min": 3, "max": 6, "optimal": 4},
      "space_requirements": {
        "min": {"width": 800, "height": 600},
        "optimal": {"width": 1200, "height": 700}
      }
    },
    "funnel": {
      "description": "Narrowing stages from wide to narrow",
      "best_for": [
        "conversion", "stages", "narrowing process", "pipeline",
        "sales funnel", "marketing funnel", "customer journey"
      ],
      "keywords": [
        "funnel", "conversion", "pipeline", "stages", "leads",
        "narrowing", "filtering", "awareness", "interest",
        "decision", "action", "AIDA", "sales", "marketing"
      ],
      "ideal_item_count": {"min": 3, "max": 5, "optimal": 4},
      "space_requirements": {
        "min": {"width": 700, "height": 600},
        "optimal": {"width": 1000, "height": 700}
      }
    },
    "concentric_circles": {
      "description": "Layers radiating from core outward",
      "best_for": [
        "core to periphery", "layers", "ecosystem", "influence zones",
        "stakeholder mapping", "spheres of influence", "target audiences"
      ],
      "keywords": [
        "core", "layers", "surrounding", "ecosystem", "center",
        "concentric", "radiate", "inner", "outer", "ring",
        "stakeholder", "influence", "sphere", "zone", "orbit"
      ],
      "ideal_item_count": {"min": 3, "max": 5, "optimal": 4},
      "space_requirements": {
        "min": {"width": 700, "height": 700},
        "optimal": {"width": 900, "height": 700}
      }
    }
  },
  "endpoints": {
    "capabilities": "GET /capabilities",
    "pyramid": "POST /v1.0/pyramid/generate",
    "funnel": "POST /v1.0/funnel/generate",
    "concentric": "POST /v1.0/concentric_circles/generate",
    "can_handle": "POST /v1.0/can-handle",
    "recommend_visual": "POST /v1.0/recommend-visual",
    "layout_service_generate": "POST /api/ai/illustrator/generate"
  }
}
```

---

## 1.2 POST /v1.0/can-handle

**Purpose**: Content negotiation - can service handle this content?

### Request Schema

```json
{
  "slide_content": {
    "title": "Marketing Funnel Stages",
    "topics": ["Awareness", "Interest", "Decision", "Action"],
    "topic_count": 4
  },
  "content_hints": {
    "has_numbers": false,
    "is_comparison": false,
    "is_time_based": false,
    "detected_keywords": ["funnel", "stages", "conversion"]
  },
  "available_space": {
    "width": 1800,
    "height": 750,
    "sub_zones": [
      {"zone_id": "main_content", "width": 1800, "height": 750}
    ],
    "layout_id": "L25"
  }
}
```

### Response Schema

```json
{
  "can_handle": true,
  "confidence": 0.92,
  "reason": "Keywords: funnel, conversion - Pattern: conversion stages - 4 items fits well",
  "suggested_approach": "funnel",
  "space_utilization": {
    "fits_well": true,
    "estimated_fill_percent": 85
  },
  "alternative_approaches": [
    {
      "visual_type": "pyramid",
      "confidence": 0.55,
      "reason": "Could represent as hierarchy, but funnel better fits conversion stages"
    }
  ]
}
```

### Confidence Score Guidelines

| Score | Meaning | Director Action |
|-------|---------|-----------------|
| 0.90+ | Excellent fit, high confidence | Use Illustrator Service |
| 0.70-0.89 | Good fit, can handle well | Use Illustrator Service |
| 0.50-0.69 | Acceptable, other services might be better | Consider alternatives |
| 0.35-0.49 | Poor fit, prefer other service | Route to Text/Analytics |
| < 0.35 | Cannot handle effectively | Route to another service |

### Keyword Matching Logic

**Strong Keywords (0.25 points each)**:
- Pyramid: pyramid, hierarchy, tier, foundation, organizational, top-down
- Funnel: funnel, conversion, pipeline, sales funnel, leads, marketing funnel
- Concentric: core, ecosystem, concentric, stakeholder, sphere

**Moderate Keywords (0.12 points each)**:
- Pyramid: level, layer, structure, base, peak, priority
- Funnel: stage, narrowing, filtering, flow, awareness, interest, decision, action
- Concentric: surrounding, center, radiate, influence, orbit, layers

**Negative Keywords (reduce confidence)**:
- chart, graph, trend, percentage, revenue, data
- vs, versus, compare, comparison, table, timeline
- over time, growth, decline, quarterly, monthly

---

## 1.3 POST /v1.0/recommend-visual

**Purpose**: Get ranked visual type recommendations for the content.

### Request Schema

```json
{
  "slide_content": {
    "title": "Product Strategy Layers",
    "topics": [
      "Core Product",
      "Extended Features",
      "Ecosystem Partners",
      "Market Influence"
    ],
    "topic_count": 4
  },
  "available_space": {
    "width": 1800,
    "height": 750,
    "layout_id": "L25"
  },
  "preferences": {
    "style": "professional",
    "complexity": "medium"
  }
}
```

### Response Schema

```json
{
  "recommended_visuals": [
    {
      "visual_type": "concentric_circles",
      "confidence": 0.88,
      "reason": "Keywords: core, layers - Pattern: layers - 4 items fits well",
      "variant": {
        "num_circles": 4,
        "style": "professional"
      },
      "space_requirements": {
        "width": 900,
        "height": 700,
        "fits_available": true
      },
      "generation_endpoint": "/v1.0/concentric_circles/generate"
    },
    {
      "visual_type": "pyramid",
      "confidence": 0.55,
      "reason": "Keywords: level - 4 items fits well",
      "variant": {
        "num_levels": 4,
        "style": "professional"
      },
      "space_requirements": {
        "width": 1200,
        "height": 700,
        "fits_available": true
      },
      "generation_endpoint": "/v1.0/pyramid/generate"
    }
  ],
  "not_recommended": [
    {
      "visual_type": "funnel",
      "reason": "No strong funnel indicators in content"
    }
  ],
  "fallback_recommendation": {
    "service": "text-service",
    "reason": "If visual not desired, text-service can render as structured content"
  }
}
```

---

# PART 2: VISUAL GENERATION ENDPOINTS

These endpoints generate LLM-powered infographic HTML.

## 2.1 POST /v1.0/pyramid/generate

**Purpose**: Generate pyramid infographic (3-6 levels)

### Request Schema

```json
{
  "num_levels": 4,
  "topic": "Product Development Strategy",
  "context": {
    "presentation_title": "Q4 Strategic Plan",
    "slide_purpose": "Show hierarchical development approach",
    "key_message": "Building from foundation to market leadership",
    "industry": "Technology"
  },
  "target_points": [
    "User Research",
    "Product Design",
    "Development & Testing",
    "Market Launch"
  ],
  "tone": "professional",
  "audience": "executives",
  "theme": "professional",
  "size": "medium",
  "validate_constraints": true,
  "presentation_id": "pres_12345",
  "slide_id": "slide_003",
  "slide_number": 3
}
```

### Response Schema

```json
{
  "success": true,
  "html": "<div class='pyramid-container'>...</div>",
  "infographic_html": "<div class='pyramid-container'>...</div>",
  "metadata": {
    "num_levels": 4,
    "template_file": "4.html",
    "theme": "professional",
    "size": "medium",
    "topic": "Product Development Strategy",
    "code_version": "v1.0.1-bullets"
  },
  "generated_content": {
    "level_1_label": "Market Launch",
    "level_1_bullet_1": "Go-to-market strategy",
    "level_1_bullet_2": "Customer acquisition",
    "level_2_label": "Development & Testing",
    "level_2_bullet_1": "Agile development cycles",
    "level_2_bullet_2": "Quality assurance"
  },
  "character_counts": {
    "level_1": {"label": 13, "bullet_1": 20, "bullet_2": 20},
    "level_2": {"label": 21, "bullet_1": 24, "bullet_2": 17}
  },
  "validation": {
    "valid": true,
    "violations": []
  },
  "generation_time_ms": 2800,
  "presentation_id": "pres_12345",
  "slide_id": "slide_003",
  "slide_number": 3
}
```

### Pyramid Template Specifications

| Levels | Template | Min Space | Description |
|--------|----------|-----------|-------------|
| 3 | `3.html` | 800x600 | Simple 3-tier hierarchy |
| 4 | `4.html` | 1000x650 | Standard 4-tier (most common) |
| 5 | `5.html` | 1100x700 | Extended 5-tier |
| 6 | `6.html` | 1200x750 | Full 6-tier hierarchy |

---

## 2.2 POST /v1.0/funnel/generate

**Purpose**: Generate funnel infographic (3-5 stages)

### Request Schema

```json
{
  "num_stages": 4,
  "topic": "Sales Conversion Funnel",
  "context": {
    "presentation_title": "Q4 Sales Strategy",
    "slide_purpose": "Show our sales pipeline stages",
    "key_message": "Systematic approach from lead to customer",
    "industry": "B2B SaaS"
  },
  "target_points": [
    "Lead Generation",
    "Qualification",
    "Proposal",
    "Closed-Won"
  ],
  "tone": "professional",
  "audience": "sales team",
  "theme": "professional",
  "size": "medium",
  "validate_constraints": true,
  "presentation_id": "pres_12345",
  "slide_id": "slide_005",
  "slide_number": 5
}
```

### Response Schema

```json
{
  "success": true,
  "html": "<div class='funnel-container'>...</div>",
  "infographic_html": "<div class='funnel-container'>...</div>",
  "metadata": {
    "num_stages": 4,
    "template_file": "4.html",
    "theme": "professional",
    "size": "medium",
    "topic": "Sales Conversion Funnel"
  },
  "generated_content": {
    "stage_1_name": "Lead Generation",
    "stage_1_bullet_1": "Inbound marketing campaigns",
    "stage_1_bullet_2": "Content marketing strategy",
    "stage_1_bullet_3": "SEO optimization",
    "stage_2_name": "Qualification",
    "stage_2_bullet_1": "Lead scoring system",
    "stage_2_bullet_2": "Initial outreach",
    "stage_2_bullet_3": "Discovery calls"
  },
  "character_counts": {
    "stage_1": {"name": 15, "bullet_1": 26, "bullet_2": 26, "bullet_3": 16},
    "stage_2": {"name": 13, "bullet_1": 19, "bullet_2": 16, "bullet_3": 15}
  },
  "validation": {
    "valid": true,
    "violations": []
  },
  "generation_time_ms": 2600,
  "presentation_id": "pres_12345",
  "slide_id": "slide_005",
  "slide_number": 5
}
```

### Funnel Template Specifications

| Stages | Template | Min Space | Description |
|--------|----------|-----------|-------------|
| 3 | `3.html` | 700x550 | Quick conversion funnel |
| 4 | `4.html` | 800x600 | AIDA funnel (standard) |
| 5 | `5.html` | 900x650 | Extended sales funnel |

---

## 2.3 POST /v1.0/concentric_circles/generate

**Purpose**: Generate concentric circles infographic (3-5 rings)

### Request Schema

```json
{
  "num_circles": 4,
  "topic": "Stakeholder Ecosystem",
  "context": {
    "presentation_title": "Strategic Partnerships",
    "slide_purpose": "Show influence zones",
    "key_message": "From core team to market ecosystem"
  },
  "target_points": [
    "Core Team",
    "Partners",
    "Customers",
    "Market"
  ],
  "tone": "professional",
  "audience": "executives",
  "theme": "professional",
  "size": "medium",
  "validate_constraints": true,
  "presentation_id": "pres_12345",
  "slide_id": "slide_007",
  "slide_number": 7
}
```

### Response Schema

```json
{
  "success": true,
  "html": "<div class='concentric-circles-container'>...</div>",
  "infographic_html": "<div class='concentric-circles-container'>...</div>",
  "metadata": {
    "num_circles": 4,
    "template_file": "4.html",
    "theme": "professional",
    "size": "medium",
    "topic": "Stakeholder Ecosystem"
  },
  "generated_content": {
    "circle_1_label": "Core Team",
    "legend_1_bullet_1": "Product development",
    "legend_1_bullet_2": "Engineering excellence",
    "legend_1_bullet_3": "Design innovation",
    "legend_1_bullet_4": "Quality assurance",
    "circle_2_label": "Partners",
    "legend_2_bullet_1": "Technology partners",
    "legend_2_bullet_2": "Integration ecosystem"
  },
  "character_counts": {
    "circle_1_label": 9,
    "legend_1_bullet_1": 19,
    "legend_1_bullet_2": 22,
    "circle_2_label": 8,
    "legend_2_bullet_1": 20
  },
  "validation": {
    "valid": true,
    "violations": []
  },
  "generation_time_ms": 2900,
  "presentation_id": "pres_12345",
  "slide_id": "slide_007",
  "slide_number": 7
}
```

### Concentric Circles Template Specifications

| Rings | Template | Min Space | Bullets per Legend |
|-------|----------|-----------|-------------------|
| 3 | `3.html` | 700x700 | 5 bullets |
| 4 | `4.html` | 800x750 | 4 bullets |
| 5 | `5.html` | 900x800 | 3 bullets |

---

## 2.4 POST /concept-spread/generate

**Purpose**: Generate hexagon-based concept spread (6 hexagons)

### Request Schema

```json
{
  "topic": "Digital Transformation Strategy",
  "num_hexagons": 6,
  "context": {
    "presentation_title": "Enterprise Digital Strategy",
    "previous_slides": ["Executive Summary", "Current State"]
  },
  "tone": "professional",
  "audience": "executives",
  "validate_constraints": true,
  "presentation_id": "pres_12345",
  "slide_id": "slide_009",
  "slide_number": 9
}
```

### Response Schema

```json
{
  "success": true,
  "html": "<div class='concept-spread-container'>...</div>",
  "infographic_html": "<div class='concept-spread-container'>...</div>",
  "generated_content": {
    "hex_1_label": "INNOVATION",
    "hex_1_icon": "lightbulb",
    "box_1_bullet_1": "Continuous improvement culture",
    "box_1_bullet_2": "Emerging technology adoption",
    "box_1_bullet_3": "R&D investment strategy",
    "hex_2_label": "AUTOMATION",
    "hex_2_icon": "cog"
  },
  "character_counts": {
    "hex_1_label": {"label": 10, "icon": 9},
    "box_1": {"bullet_1": 30, "bullet_2": 27, "bullet_3": 22}
  },
  "validation": {
    "valid": true,
    "violations": []
  },
  "metadata": {
    "model": "gemini-1.5-flash-002",
    "generation_time_ms": 3200,
    "attempts": 1
  },
  "generation_time_ms": 3200,
  "presentation_id": "pres_12345",
  "slide_id": "slide_009",
  "slide_number": 9
}
```

---

## 2.5 GET /concept-spread/health

**Purpose**: Health check for concept spread endpoint

### Response Schema

```json
{
  "status": "healthy",
  "service": "concept-spread",
  "supported_variants": [6]
}
```

---

# PART 3: LAYOUT SERVICE INTEGRATION

These endpoints provide unified access for the Layout Service orchestrator.

## 3.1 POST /api/ai/illustrator/generate

**Purpose**: Unified infographic generation for Layout Service

Supports 14 infographic types:
- **Template-based (HTML)**: pyramid, funnel, concentric_circles, concept_spread, venn, comparison
- **Dynamic SVG (Gemini 2.5 Pro)**: timeline, process, statistics, hierarchy, list, cycle, matrix, roadmap

### Request Schema

```json
{
  "prompt": "Create a sales funnel showing AIDA stages",
  "type": "funnel",
  "constraints": {
    "gridWidth": 20,
    "gridHeight": 12,
    "itemCount": 4
  },
  "options": {
    "colorScheme": "professional",
    "includeIcons": true
  },
  "presentationId": "pres_12345",
  "slideId": "slide_005",
  "elementId": "elem_001"
}
```

### Response Schema

```json
{
  "success": true,
  "data": {
    "generationId": "gen_abc123",
    "renderedOutput": {
      "svg": null,
      "html": "<div class='funnel-container'>...</div>",
      "format": "html",
      "width": 1200,
      "height": 720
    },
    "infographic": {
      "type": "funnel",
      "title": "Sales Conversion Funnel",
      "items": [
        {"id": "item_1", "label": "Awareness", "description": "..."},
        {"id": "item_2", "label": "Interest", "description": "..."},
        {"id": "item_3", "label": "Decision", "description": "..."},
        {"id": "item_4", "label": "Action", "description": "..."}
      ],
      "colorPalette": ["#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE"]
    },
    "metadata": {
      "modelUsed": "gemini-1.5-flash-002",
      "tokenCount": 450,
      "generationTimeMs": 2800
    },
    "editInfo": {
      "editableFields": ["items[*].label", "items[*].description"],
      "constraints": {
        "maxLabelLength": 25,
        "maxDescriptionLength": 100
      }
    }
  },
  "presentationId": "pres_12345",
  "slideId": "slide_005",
  "elementId": "elem_001",
  "generationTimeMs": 2800
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "CONSTRAINT_VIOLATION",
    "message": "Grid dimensions too small for funnel type",
    "retryable": false,
    "suggestion": "Check the grid constraints for this infographic type"
  },
  "presentationId": "pres_12345",
  "slideId": "slide_005",
  "elementId": "elem_001",
  "generationTimeMs": 50
}
```

---

## 3.2 GET /api/ai/illustrator/types

**Purpose**: List all supported infographic types with constraints

### Response Schema

```json
{
  "total_types": 14,
  "template_types": ["pyramid", "funnel", "concentric_circles", "concept_spread", "venn", "comparison"],
  "svg_types": ["timeline", "process", "statistics", "hierarchy", "list", "cycle", "matrix", "roadmap"],
  "grid_unit_pixels": 60,
  "types": {
    "pyramid": {
      "description": "Hierarchical structure from foundation to peak",
      "min_grid_width": 12,
      "min_grid_height": 10,
      "max_grid_width": 32,
      "max_grid_height": 18,
      "aspect_ratio_type": "flexible",
      "output_mode": "html",
      "item_limits": {"min": 3, "max": 6, "default": 4}
    },
    "funnel": {
      "description": "Narrowing stages from wide to narrow",
      "min_grid_width": 10,
      "min_grid_height": 10,
      "max_grid_width": 24,
      "max_grid_height": 18,
      "aspect_ratio_type": "flexible",
      "output_mode": "html",
      "item_limits": {"min": 3, "max": 5, "default": 4}
    },
    "timeline": {
      "description": "Chronological progression of events",
      "min_grid_width": 16,
      "min_grid_height": 6,
      "max_grid_width": 32,
      "max_grid_height": 12,
      "aspect_ratio_type": "wide",
      "output_mode": "svg",
      "item_limits": {"min": 3, "max": 8, "default": 5}
    }
  }
}
```

---

## 3.3 GET /api/ai/illustrator/types/{infographic_type}

**Purpose**: Get detailed constraints for a specific type

### Response Schema

```json
{
  "type": "funnel",
  "description": "Narrowing stages from wide to narrow",
  "grid_constraints": {
    "min_width": 10,
    "min_height": 10,
    "max_width": 24,
    "max_height": 18,
    "min_pixels": {"width": 600, "height": 600},
    "max_pixels": {"width": 1440, "height": 1080}
  },
  "aspect_ratio": {
    "type": "flexible",
    "value": "flexible"
  },
  "output_mode": "html",
  "item_limits": {
    "min": 3,
    "max": 5,
    "default": 4
  }
}
```

---

## 3.4 GET /api/ai/illustrator/health

**Purpose**: Health check for Layout Service integration

### Response Schema

```json
{
  "status": "healthy",
  "endpoint": "/api/ai/illustrator/generate",
  "supported_types": 14,
  "template_types": 6,
  "svg_types": 8
}
```

---

# PART 4: ROOT & METADATA ENDPOINTS

## 4.1 GET /

**Purpose**: Root endpoint with service information

### Response Schema

```json
{
  "service": "Illustrator Service",
  "version": "1.1.0",
  "architecture": "Template-based + Dynamic SVG generation",
  "endpoints": {
    "capabilities": "GET /capabilities (Director coordination)",
    "can_handle": "POST /v1.0/can-handle (Director coordination)",
    "recommend_visual": "POST /v1.0/recommend-visual (Director coordination)",
    "layout_service_generate": "POST /api/ai/illustrator/generate (Layout Service)",
    "layout_service_types": "GET /api/ai/illustrator/types",
    "layout_service_type_details": "GET /api/ai/illustrator/types/{type}",
    "generate": "POST /v1.0/generate",
    "pyramid_generate": "POST /v1.0/pyramid/generate (LLM-powered)",
    "funnel_generate": "POST /v1.0/funnel/generate (LLM-powered)",
    "concentric_circles_generate": "POST /v1.0/concentric_circles/generate (LLM-powered)",
    "concept_spread_generate": "POST /concept-spread/generate (LLM-powered)",
    "list_illustrations": "GET /v1.0/illustrations",
    "illustration_details": "GET /v1.0/illustration/{type}",
    "list_themes": "GET /v1.0/themes",
    "list_sizes": "GET /v1.0/sizes",
    "health_check": "GET /health"
  },
  "features": {
    "template_based_generation": true,
    "dynamic_svg_generation": true,
    "html_css_rendering": true,
    "png_conversion": false,
    "theme_support": 4,
    "size_presets": 3,
    "infographic_types": 14,
    "director_integration": true
  },
  "phase": "Phase 3 - Director Integration"
}
```

---

## 4.2 GET /health

**Purpose**: Service health check

### Response Schema

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "templates_directory": "/app/templates",
  "templates_exist": true,
  "phase": "Phase 1 - Infrastructure Setup"
}
```

---

## 4.3 POST /v1.0/generate (Legacy)

**Purpose**: Generate illustration from template (legacy endpoint)

**Note**: Only supports approved types: `pyramid`, `pyramid_3tier`, `funnel`, `funnel_4stage`

### Request Schema

```json
{
  "illustration_type": "pyramid",
  "variant_id": "base",
  "data": {
    "levels": [
      {"label": "Vision", "description": "Long-term goals"},
      {"label": "Strategy", "description": "Approach to achieve vision"},
      {"label": "Tactics", "description": "Specific actions"},
      {"label": "Operations", "description": "Day-to-day execution"}
    ]
  },
  "theme": "professional",
  "size": "medium",
  "output_format": "html"
}
```

### Response Schema

```json
{
  "illustration_type": "pyramid",
  "variant_id": "base",
  "format": "html",
  "data": "<div class='pyramid-container'>...</div>",
  "metadata": {
    "width": 1200,
    "height": 800,
    "theme": "professional",
    "rendering_method": "html_css"
  },
  "generation_time_ms": 145
}
```

---

## 4.4 GET /v1.0/illustrations

**Purpose**: List all available illustration types and variants

### Response Schema

```json
{
  "total_templates": 4,
  "illustrations": [
    {
      "illustration_type": "pyramid",
      "variants": ["base", "rounded", "minimal"]
    },
    {
      "illustration_type": "funnel",
      "variants": ["base", "gradient"]
    }
  ]
}
```

---

## 4.5 GET /v1.0/illustration/{illustration_type}

**Purpose**: Get details about a specific illustration type

### Response Schema

```json
{
  "illustration_type": "pyramid",
  "variants": ["base", "rounded", "minimal"],
  "supported_themes": ["professional", "bold", "minimal", "playful"],
  "supported_sizes": ["small", "medium", "large"]
}
```

---

## 4.6 GET /v1.0/themes

**Purpose**: List all available color themes

### Response Schema

```json
{
  "total_themes": 4,
  "themes": [
    {
      "name": "professional",
      "description": "Corporate blue palette",
      "colors": {
        "primary": "#1e3a5f",
        "secondary": "#3b82f6",
        "accent": "#fbbf24",
        "background": "#f8fafc"
      }
    },
    {
      "name": "bold",
      "description": "High contrast vibrant colors",
      "colors": {
        "primary": "#dc2626",
        "secondary": "#ea580c",
        "accent": "#facc15",
        "background": "#fef2f2"
      }
    },
    {
      "name": "minimal",
      "description": "Clean grayscale palette",
      "colors": {
        "primary": "#374151",
        "secondary": "#6b7280",
        "accent": "#9ca3af",
        "background": "#ffffff"
      }
    },
    {
      "name": "playful",
      "description": "Fun colorful palette",
      "colors": {
        "primary": "#7c3aed",
        "secondary": "#ec4899",
        "accent": "#06b6d4",
        "background": "#faf5ff"
      }
    }
  ]
}
```

---

## 4.7 GET /v1.0/sizes

**Purpose**: List all available size presets

### Response Schema

```json
{
  "total_sizes": 3,
  "sizes": [
    {
      "name": "small",
      "width": 800,
      "height": 600,
      "description": "Compact view"
    },
    {
      "name": "medium",
      "width": 1200,
      "height": 800,
      "description": "Standard presentation size"
    },
    {
      "name": "large",
      "width": 1920,
      "height": 1080,
      "description": "Full HD display"
    }
  ]
}
```

---

# APPENDIX A: Visualization Types Reference

## Template-Based Types (HTML)

| Type | Items | Output | Description |
|------|-------|--------|-------------|
| `pyramid` | 3-6 | HTML | Hierarchical structure |
| `funnel` | 3-5 | HTML | Narrowing stages |
| `concentric_circles` | 3-5 | HTML | Core-to-periphery layers |
| `concept_spread` | 6 | HTML | Hexagon grid layout |
| `venn` | 2-4 | HTML | Overlapping concepts |
| `comparison` | 2-4 | HTML | Side-by-side comparison |

## Dynamic SVG Types (Gemini)

| Type | Items | Output | Description |
|------|-------|--------|-------------|
| `timeline` | 3-8 | SVG | Chronological events |
| `process` | 3-7 | SVG | Step-by-step flow |
| `statistics` | 3-6 | SVG | Data metrics display |
| `hierarchy` | 3-6 | SVG | Organizational chart |
| `list` | 3-8 | SVG | Bulleted items |
| `cycle` | 3-6 | SVG | Circular process |
| `matrix` | 4-9 | SVG | Grid layout |
| `roadmap` | 3-6 | SVG | Future planning |

---

# APPENDIX B: Quick Reference

## Endpoints by Use Case

| Use Case | Recommended Endpoint |
|----------|---------------------|
| Service discovery | `GET /capabilities` |
| Can service handle this? | `POST /v1.0/can-handle` |
| Get visual recommendations | `POST /v1.0/recommend-visual` |
| Pyramid (LLM-powered) | `POST /v1.0/pyramid/generate` |
| Funnel (LLM-powered) | `POST /v1.0/funnel/generate` |
| Concentric circles (LLM-powered) | `POST /v1.0/concentric_circles/generate` |
| Concept spread (hexagons) | `POST /concept-spread/generate` |
| Layout Service unified | `POST /api/ai/illustrator/generate` |
| List infographic types | `GET /api/ai/illustrator/types` |
| Type constraints | `GET /api/ai/illustrator/types/{type}` |

## Space Requirements by Visual Type

| Visual Type | Min Width | Min Height | Optimal Width | Optimal Height |
|-------------|-----------|------------|---------------|----------------|
| Pyramid | 800px | 600px | 1200px | 700px |
| Funnel | 700px | 600px | 1000px | 700px |
| Concentric | 700px | 700px | 900px | 700px |

---

# APPENDIX C: Error Responses

All endpoints return errors in this format:

```json
{
  "detail": {
    "error_type": "validation_error",
    "message": "Description of the error",
    "suggestions": ["Suggestion 1", "Suggestion 2"]
  }
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad Request - Invalid input or archived template |
| 404 | Not Found - Template or type not found |
| 422 | Unprocessable Entity - Data validation failed |
| 500 | Internal Server Error |

---

# APPENDIX D: Service Routing Decision Tree

```
                        +-------------------+
                        |  Analyze Content  |
                        +---------+---------+
                                  |
            +---------------------+---------------------+
            v                     v                     v
    +---------------+     +---------------+     +---------------+
    | Numbers +     |     | Pyramid,      |     | Process,      |
    | Time-based    |     | Funnel,       |     | Matrix,       |
    | Charts        |     | Hierarchy     |     | Grid, etc     |
    +-------+-------+     +-------+-------+     +-------+-------+
            |                     |                     |
            v                     v                     v
    +---------------+     +---------------+     +---------------+
    | Analytics     |     | ILLUSTRATOR   |     |   Text        |
    | Service       |     |   SERVICE     |     |   Service     |
    +---------------+     +-------+-------+     +---------------+
                                  |
                    +-------------+-------------+
                    v             v             v
              +----------+ +----------+ +----------+
              | Pyramid  | |  Funnel  | |Concentric|
              | (3-6)    | |  (3-5)   | | Circles  |
              +----------+ +----------+ |  (3-5)   |
                                        +----------+
```

---

# Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.2 | Dec 2024 | Added `infographic_html` field to Concept Spread response schema (was missing in v1.0.1 documentation). All 4 visual generation endpoints now fully aligned. |
| 1.0.1 | Dec 2024 | Added `infographic_html` field to all generation responses for Layout Service compatibility. Documented all 19 endpoints comprehensively. |
| 1.0.0 | Dec 2024 | Initial release with 3 Director coordination endpoints, pyramid/funnel/concentric_circles generation, concept spread, and Layout Service integration |

---

# Related Documents

- [SERVICE_CAPABILITIES_SPEC.md](./SERVICE_CAPABILITIES_SPEC.md) - Coordination endpoint specification
- [SERVICE_COORDINATION_REQUIREMENTS.md](./SERVICE_COORDINATION_REQUIREMENTS.md) - Architecture overview
- [TEXT_SERVICE_CAPABILITIES.md](./TEXT_SERVICE_CAPABILITIES.md) - Text Service integration
- [SLIDE_GENERATION_INPUT_SPEC.md](./SLIDE_GENERATION_INPUT_SPEC.md) - Canonical slide generation reference
