# Illustrator Service API Reference

**Version**: 1.2.0
**Base URL**: `http://localhost:8000` (local) | Production via Railway
**Last Updated**: December 2024

---

## Production URLs

**Illustrator Service**: `https://illustrator-v10-production.up.railway.app`

**Layout Service**: `https://web-production-f0d13.up.railway.app`

All endpoints below should be prefixed with the Illustrator Service base URL in production.

---

## GOLD STANDARD: 5 Tested & Approved Infographic Templates

These 5 infographic templates have been **tested and approved** for production use. They generate professional visual diagrams with LLM-powered content.

### Endpoint Summary

| Template Type | Endpoint | Variants | Layout Integration |
|---------------|----------|----------|-------------------|
| **Pyramid** | `POST /v1.0/pyramid/generate` | 3, 4, 5, 6 levels | C4-infographic |
| **Funnel** | `POST /v1.0/funnel/generate` | 3, 4, 5 stages | C4-infographic |
| **Concentric Circles** | `POST /v1.0/concentric_circles/generate` | 3, 4, 5 rings | C4-infographic |
| **Concept Spread** | `POST /concept-spread/generate` | 6 hexagons | C4-infographic |
| **Star Diagram** | `POST /v1.0/star-diagram/generate` | 5 elements | C4-infographic |

### Template Capabilities

| Template | Best For | Item Count | Color Scheme |
|----------|----------|------------|--------------|
| **Pyramid** | Hierarchies, levels, foundation-to-peak structures | 3-6 levels | Blue, Cyan, Green, Amber, Purple gradient |
| **Funnel** | Conversion stages, narrowing pipelines, AIDA | 3-5 stages | Same color palette |
| **Concentric Circles** | Core-to-periphery layers, ecosystems, influence zones | 3-5 rings | Same color palette |
| **Concept Spread** | Multi-faceted concepts, 6 interconnected ideas | 6 hexagons | Same color palette |
| **Star Diagram** | Radial concepts, 5 interconnected pillars, strategy elements | 5 elements | Purple, Blue, Red, Green, Yellow (themed) |

---

### Pyramid: Hierarchical Structure (3-6 Levels)

**Endpoint**: `POST /v1.0/pyramid/generate`

**Purpose**: Generate pyramid infographic showing hierarchical structure from foundation (base) to peak (top).

**Request**:
```json
{
  "num_levels": 4,
  "topic": "Digital Transformation Journey",
  "tone": "professional",
  "audience": "leadership",
  "theme": "professional",
  "size": "medium",
  "context": {
    "presentation_title": "Illustrator Test Suite",
    "slide_purpose": "Testing 4-level pyramid generation"
  }
}
```

**Response**:
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
    "topic": "Digital Transformation Journey",
    "code_version": "v1.0.1-bullets",
    "attempts": 1,
    "generation_time_ms": 2800,
    "model": "gemini-1.5-flash-002",
    "usage": {"prompt_tokens": 450, "completion_tokens": 180}
  },
  "generated_content": {
    "level_1_label": "Operations",
    "level_1_bullet_1": "Daily execution tasks",
    "level_1_bullet_2": "Process management",
    "level_2_label": "Tactics",
    "level_2_bullet_1": "Quarterly initiatives",
    "level_2_bullet_2": "Performance metrics"
  },
  "validation": {
    "valid": true,
    "violations": []
  },
  "generation_time_ms": 2800
}
```

**Layout Service Integration**:
```json
{
  "layout": "C4-infographic",
  "content": {
    "slide_title": "Digital Transformation Journey",
    "subtitle": "Pyramid - 4 Levels",
    "infographic_html": "<div class='pyramid-container'>...</div>",
    "presentation_name": "Enterprise Strategy",
    "logo": " "
  }
}
```

---

### Funnel: Conversion Stages (3-5 Stages)

**Endpoint**: `POST /v1.0/funnel/generate`

**Purpose**: Generate funnel infographic showing narrowing conversion stages from wide (top) to narrow (bottom).

**Request**:
```json
{
  "num_stages": 4,
  "topic": "Sales Conversion Funnel",
  "tone": "professional",
  "audience": "sales team",
  "theme": "professional",
  "size": "medium",
  "context": {
    "presentation_title": "Q4 Sales Strategy",
    "slide_purpose": "Testing 4-stage funnel generation"
  }
}
```

**Response**:
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
    "topic": "Sales Conversion Funnel",
    "code_version": "v1.0.1-bullets",
    "attempts": 1,
    "generation_time_ms": 2600,
    "model": "gemini-1.5-flash-002",
    "usage": {"prompt_tokens": 420, "completion_tokens": 165}
  },
  "generated_content": {
    "stage_1_name": "Lead Generation",
    "stage_1_bullet_1": "Inbound marketing campaigns",
    "stage_1_bullet_2": "Content marketing strategy",
    "stage_1_bullet_3": "SEO optimization",
    "stage_2_name": "Qualification",
    "stage_2_bullet_1": "Lead scoring system",
    "stage_2_bullet_2": "Initial outreach"
  },
  "validation": {
    "valid": true,
    "violations": []
  },
  "generation_time_ms": 2600
}
```

**Layout Service Integration**:
```json
{
  "layout": "C4-infographic",
  "content": {
    "slide_title": "Sales Conversion Funnel",
    "subtitle": "Funnel - 4 Stages",
    "infographic_html": "<div class='funnel-container'>...</div>",
    "presentation_name": "Q4 Sales Strategy",
    "logo": " "
  }
}
```

---

### Concentric Circles: Core-to-Periphery Layers (3-5 Rings)

**Endpoint**: `POST /v1.0/concentric_circles/generate`

**Purpose**: Generate concentric circles infographic showing layers radiating from core (center) to periphery (outer).

**Request**:
```json
{
  "num_circles": 4,
  "topic": "Stakeholder Influence Mapping",
  "tone": "professional",
  "audience": "executives",
  "theme": "professional",
  "size": "medium",
  "context": {
    "presentation_title": "Strategic Partnerships",
    "slide_purpose": "Testing 4-circle concentric diagram generation"
  }
}
```

**Response**:
```json
{
  "success": true,
  "html": "<div class='concentric-container'>...</div>",
  "infographic_html": "<div class='concentric-container'>...</div>",
  "metadata": {
    "num_circles": 4,
    "template_file": "4.html",
    "theme": "professional",
    "size": "medium",
    "topic": "Stakeholder Influence Mapping",
    "attempts": 1,
    "generation_time_ms": 2900,
    "model": "gemini-1.5-flash-002"
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
  "validation": {
    "valid": true,
    "violations": []
  },
  "generation_time_ms": 2900
}
```

**Layout Service Integration**:
```json
{
  "layout": "C4-infographic",
  "content": {
    "slide_title": "Stakeholder Influence Mapping",
    "subtitle": "Concentric Circles - 4 Rings",
    "infographic_html": "<div class='concentric-container'>...</div>",
    "presentation_name": "Strategic Partnerships",
    "logo": " "
  }
}
```

---

### Concept Spread: Hexagon Grid (6 Hexagons)

**Endpoint**: `POST /concept-spread/generate`

**Purpose**: Generate hexagon-based concept spread showing 6 interconnected concepts with detailed description boxes.

**Request**:
```json
{
  "topic": "Digital Transformation Pillars",
  "num_hexagons": 6,
  "tone": "professional",
  "audience": "executives",
  "context": {
    "presentation_title": "Enterprise Digital Strategy",
    "slide_purpose": "Testing concept spread hexagon generation"
  }
}
```

**Response**:
```json
{
  "success": true,
  "html": "<div class='concept-spread-container'>...</div>",
  "infographic_html": "<div class='concept-spread-container'>...</div>",
  "generated_content": {
    "hex_1_label": "Vision",
    "hex_1_icon": "lightbulb",
    "box_1_bullet_1": "Define a clear future state for the organization",
    "box_1_bullet_2": "Align digital goals with overall business objectives",
    "box_1_bullet_3": "Inspire stakeholders with a compelling digital direction",
    "hex_2_label": "Strategy",
    "hex_2_icon": "cog",
    "box_2_bullet_1": "Develop a phased roadmap for digital initiatives",
    "box_2_bullet_2": "Identify key capabilities needed for transformation",
    "box_2_bullet_3": "Prioritize investments for maximum impact and ROI"
  },
  "metadata": {
    "model": "gemini-1.5-flash-002",
    "generation_time_ms": 3200,
    "attempts": 1
  },
  "validation": {
    "valid": true,
    "violations": []
  },
  "generation_time_ms": 3200
}
```

**Layout Service Integration**:
```json
{
  "layout": "C4-infographic",
  "content": {
    "slide_title": "Digital Transformation Pillars",
    "subtitle": "Concept Spread - 6 Hexagons",
    "infographic_html": "<div class='concept-spread-container'>...</div>",
    "presentation_name": "Enterprise Digital Strategy",
    "logo": " "
  }
}
```

---

### Star Diagram: Radial Concept Display (5 Elements)

**Endpoint**: `POST /v1.0/star-diagram/generate`

**Purpose**: Generate star diagram infographic showing 5 radial concepts arranged around a central star. Each element has a colored heading and 3 bullet points. Supports dark mode with themed accent text colors.

**Request**:
```json
{
  "num_elements": 5,
  "topic": "Digital Marketing Strategy",
  "tone": "professional",
  "audience": "marketing team",
  "theme": "professional",
  "size": "medium",
  "context": {
    "presentation_title": "Marketing Strategy Presentation",
    "slide_purpose": "Testing 5-element star diagram generation"
  }
}
```

**Response**:
```json
{
  "success": true,
  "html": "<div class='star-diagram-container'>...</div>",
  "infographic_html": "<div class='star-diagram-container'>...</div>",
  "metadata": {
    "num_elements": 5,
    "template_file": "5.html",
    "theme": "professional",
    "size": "medium",
    "topic": "Digital Marketing Strategy",
    "attempts": 1,
    "generation_time_ms": 4200,
    "model": "gemini-2.0-flash-exp"
  },
  "generated_content": {
    "element_1_label": "SEO",
    "element_1_bullet_1": "Optimize <strong>website content</strong> for search engines",
    "element_1_bullet_2": "Enhance <strong>organic visibility</strong> and traffic flow",
    "element_1_bullet_3": "Implement <strong>keyword research</strong> for better reach",
    "element_2_label": "Content Marketing",
    "element_2_bullet_1": "Create <strong>valuable content</strong> for target audience",
    "element_2_bullet_2": "Distribute <strong>engaging articles</strong> across platforms",
    "element_2_bullet_3": "Establish <strong>thought leadership</strong> through insights",
    "element_3_label": "Social Media",
    "element_3_bullet_1": "Build <strong>community engagement</strong> on social channels",
    "element_3_bullet_2": "Run <strong>targeted ad campaigns</strong> for conversions",
    "element_3_bullet_3": "Monitor <strong>brand sentiment</strong> and interactions",
    "element_4_label": "Paid Ads",
    "element_4_bullet_1": "Manage <strong>PPC campaigns</strong> for immediate impact",
    "element_4_bullet_2": "Optimize <strong>ad spend</strong> for maximum ROI",
    "element_4_bullet_3": "Utilize <strong>retargeting strategies</strong> effectively",
    "element_5_label": "Analytics",
    "element_5_bullet_1": "Track <strong>key performance indicators</strong> regularly",
    "element_5_bullet_2": "Analyze <strong>customer behavior patterns</strong> deeply",
    "element_5_bullet_3": "Derive <strong>actionable insights</strong> from data"
  },
  "validation": {
    "valid": true,
    "violations": []
  },
  "generation_time_ms": 4200
}
```

**Layout Service Integration**:
```json
{
  "layout": "C4-infographic",
  "content": {
    "slide_title": "Digital Marketing Strategy",
    "subtitle": "Star Diagram - 5 Elements",
    "infographic_html": "<div class='star-diagram-container'>...</div>",
    "presentation_name": "Marketing Strategy Presentation",
    "logo": " "
  }
}
```

**Theming Features**:
- **Light Mode**: Colored headings (purple, blue, red, green, yellow) with dark text bullets
- **Dark Mode**: Light pastel headings with white bullets (auto-switches via CSS variables)
- Uses `--accent-text-purple`, `--accent-text-blue`, `--accent-text-red`, `--accent-text-green`, `--accent-text-yellow` CSS variables

---

## Layout Service Integration: C4-infographic

All 5 Gold Standard templates integrate with the Layout Service using the `C4-infographic` layout.

### Creating a Presentation with Infographics

**Endpoint**: `POST https://web-production-f0d13.up.railway.app/api/presentations`

**Request**:
```json
{
  "title": "Illustrator Infographics Presentation",
  "slides": [
    {
      "layout": "C4-infographic",
      "content": {
        "slide_title": "Product Development Strategy",
        "subtitle": "Pyramid - 4 Levels",
        "infographic_html": "<div class='pyramid-container'>...</div>",
        "presentation_name": "Strategy Presentation",
        "logo": " "
      }
    },
    {
      "layout": "C4-infographic",
      "content": {
        "slide_title": "Sales Conversion Funnel",
        "subtitle": "Funnel - 4 Stages",
        "infographic_html": "<div class='funnel-container'>...</div>",
        "presentation_name": "Strategy Presentation",
        "logo": " "
      }
    }
  ]
}
```

**Response**:
```json
{
  "id": "8fd87027-9a0b-4a9c-bcbc-4605d085decb",
  "title": "Illustrator Infographics Presentation",
  "slide_count": 2
}
```

**Presentation URL**: `https://web-production-f0d13.up.railway.app/p/{presentation_id}`

> **Important: Logo Placeholder**
>
> To prevent the Layout Service from showing a default logo placeholder icon, pass `"logo": " "` (a space character) in the content object. This tells the Layout Service to render an empty logo area instead of the placeholder.

---

## PART 1: DIRECTOR COORDINATION ENDPOINTS

The Director Agent uses these 3 endpoints for intelligent service routing.

### 1.1 GET /capabilities

**Purpose**: Service discovery - what can this service do?

**Response**:
```json
{
  "service": "illustrator-service",
  "version": "1.0.0",
  "status": "healthy",
  "capabilities": {
    "slide_types": ["infographic", "visual_metaphor"],
    "visualization_types": ["pyramid", "funnel", "concentric_circles", "concept_spread", "star_diagram"],
    "supports_themes": true,
    "ai_generated_content": true,
    "supported_layouts": ["C4-infographic"]
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
      "conversion", "pipeline", "narrowing", "concentric"
    ]
  },
  "endpoints": {
    "capabilities": "GET /capabilities",
    "pyramid": "POST /v1.0/pyramid/generate",
    "funnel": "POST /v1.0/funnel/generate",
    "concentric": "POST /v1.0/concentric_circles/generate",
    "concept_spread": "POST /concept-spread/generate",
    "star_diagram": "POST /v1.0/star-diagram/generate",
    "can_handle": "POST /v1.0/can-handle",
    "recommend_visual": "POST /v1.0/recommend-visual"
  }
}
```

---

### 1.2 POST /v1.0/can-handle

**Purpose**: Content negotiation - can service handle this content?

**Request**:
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
    "layout_id": "C4-infographic"
  }
}
```

**Response**:
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

---

### 1.3 POST /v1.0/recommend-visual

**Purpose**: Get ranked visual type recommendations for the content.

**Request**:
```json
{
  "slide_content": {
    "title": "Product Strategy Layers",
    "topics": ["Core Product", "Extended Features", "Ecosystem Partners", "Market Influence"],
    "topic_count": 4
  },
  "available_space": {
    "width": 1800,
    "height": 750,
    "layout_id": "C4-infographic"
  },
  "preferences": {
    "style": "professional",
    "complexity": "medium"
  }
}
```

**Response**:
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

## PART 2: TEMPLATE SPECIFICATIONS

### Pyramid Template Specifications

| Levels | Template | Min Space | Bullets per Level |
|--------|----------|-----------|------------------|
| 3 | `3.html` | 800x600 | 4 bullets |
| 4 | `4.html` | 1000x650 | 4 bullets |
| 5 | `5.html` | 1100x700 | 3 bullets |
| 6 | `6.html` | 1200x750 | 2 bullets |

### Funnel Template Specifications

| Stages | Template | Min Space | Bullets per Stage |
|--------|----------|-----------|------------------|
| 3 | `3.html` | 700x550 | 3 bullets |
| 4 | `4.html` | 800x600 | 3 bullets |
| 5 | `5.html` | 900x650 | 3 bullets |

### Concentric Circles Template Specifications

| Rings | Template | Min Space | Bullets per Legend |
|-------|----------|-----------|-------------------|
| 3 | `3.html` | 700x700 | 5 bullets |
| 4 | `4.html` | 800x750 | 4 bullets |
| 5 | `5.html` | 900x800 | 3 bullets |

### Concept Spread Template Specifications

| Hexagons | Template | Min Space | Bullets per Box |
|----------|----------|-----------|-----------------|
| 6 | `6.html` | 1600x720 | 3 bullets |

### Star Diagram Template Specifications

| Elements | Template | Min Space | Bullets per Element | Theming |
|----------|----------|-----------|---------------------|---------|
| 5 | `5.html` | 1800x720 | 3 bullets | Dark mode support via CSS variables |

**Content Fields**:
- `element_N_label`: 1-2 words (5-20 characters)
- `element_N_bullet_1/2/3`: 35-40 characters each with one `<strong>` tag

---

## PART 3: ROOT & METADATA ENDPOINTS

### GET /

**Purpose**: Root endpoint with service information

**Response**:
```json
{
  "service": "Illustrator Service",
  "version": "1.2.0",
  "architecture": "Template-based + LLM-powered content generation",
  "endpoints": {
    "capabilities": "GET /capabilities (Director coordination)",
    "can_handle": "POST /v1.0/can-handle (Director coordination)",
    "recommend_visual": "POST /v1.0/recommend-visual (Director coordination)",
    "pyramid_generate": "POST /v1.0/pyramid/generate (LLM-powered)",
    "funnel_generate": "POST /v1.0/funnel/generate (LLM-powered)",
    "concentric_circles_generate": "POST /v1.0/concentric_circles/generate (LLM-powered)",
    "concept_spread_generate": "POST /concept-spread/generate (LLM-powered)",
    "list_themes": "GET /v1.0/themes",
    "list_sizes": "GET /v1.0/sizes",
    "health_check": "GET /health"
  },
  "features": {
    "template_based_generation": true,
    "llm_content_generation": true,
    "html_css_rendering": true,
    "theme_support": 4,
    "size_presets": 3,
    "gold_standard_templates": 5,
    "director_integration": true
  }
}
```

---

### GET /health

**Purpose**: Service health check

**Response**:
```json
{
  "status": "healthy",
  "version": "1.2.0",
  "templates_directory": "/app/templates",
  "templates_exist": true
}
```

---

### GET /v1.0/themes

**Purpose**: List all available color themes

**Response**:
```json
{
  "total_themes": 4,
  "themes": [
    {
      "name": "professional",
      "palette": {
        "primary": "#0066CC",
        "secondary": "#FF6B00",
        "accent": "#0066CC",
        "background": "#FFFFFF",
        "text": "#333333"
      }
    },
    {
      "name": "bold",
      "palette": {
        "primary": "#dc2626",
        "secondary": "#ea580c",
        "accent": "#dc2626",
        "background": "#fef2f2",
        "text": "#1f2937"
      }
    },
    {
      "name": "minimal",
      "palette": {
        "primary": "#374151",
        "secondary": "#6b7280",
        "accent": "#374151",
        "background": "#ffffff",
        "text": "#111827"
      }
    },
    {
      "name": "playful",
      "palette": {
        "primary": "#7c3aed",
        "secondary": "#ec4899",
        "accent": "#7c3aed",
        "background": "#faf5ff",
        "text": "#1e1b4b"
      }
    }
  ]
}
```

---

### GET /v1.0/sizes

**Purpose**: List all available size presets

**Response**:
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

## APPENDIX A: Quick Reference

### Endpoints by Use Case

| Use Case | Recommended Endpoint |
|----------|---------------------|
| Service discovery | `GET /capabilities` |
| Can service handle this? | `POST /v1.0/can-handle` |
| Get visual recommendations | `POST /v1.0/recommend-visual` |
| Pyramid (3-6 levels) | `POST /v1.0/pyramid/generate` |
| Funnel (3-5 stages) | `POST /v1.0/funnel/generate` |
| Concentric circles (3-5 rings) | `POST /v1.0/concentric_circles/generate` |
| Concept spread (6 hexagons) | `POST /concept-spread/generate` |
| Star diagram (5 elements) | `POST /v1.0/star-diagram/generate` |
| List themes | `GET /v1.0/themes` |
| List sizes | `GET /v1.0/sizes` |

### Gold Standard Template Summary

| Template | Variants | Item Range | Best For |
|----------|----------|------------|----------|
| **Pyramid** | 3, 4, 5, 6 | 3-6 levels | Hierarchies, organizational structures |
| **Funnel** | 3, 4, 5 | 3-5 stages | Conversion, sales pipelines, AIDA |
| **Concentric Circles** | 3, 4, 5 | 3-5 rings | Core-periphery, ecosystems, influence |
| **Concept Spread** | 6 | 6 hexagons | Multi-faceted concepts, pillars |
| **Star Diagram** | 5 | 5 elements | Radial concepts, strategy pillars, marketing mix |

---

## APPENDIX B: Error Responses

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
| 400 | Bad Request - Invalid input |
| 404 | Not Found - Template or type not found |
| 422 | Unprocessable Entity - Data validation failed |
| 500 | Internal Server Error |

---

## APPENDIX C: Service Routing Decision Tree

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
              +-------------------+-------------------+
              v                   v                   v
        +----------+        +----------+        +----------+
        | Pyramid  |        |  Funnel  |        |Concentric|
        | (3-6)    |        |  (3-5)   |        | Circles  |
        +----------+        +----------+        |  (3-5)   |
                                                +----------+
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.3.0 | Dec 2024 | **Star Diagram Addition**: Added Star Diagram as 5th Gold Standard template. Features dark mode theming with accent text color CSS variables (purple, blue, red, green, yellow). Updated all template counts and endpoint lists. |
| 1.2.0 | Dec 2024 | **Major update**: (1) Renamed from ILLUSTRATOR_SERVICE_CAPABILITIES.md to ILLUSTRATOR_API_REFERENCE.md. (2) Added GOLD STANDARD section for 4 tested & approved templates (Pyramid, Funnel, Concentric Circles, Concept Spread). (3) Added production URLs. (4) Added exact request/response schemas from working test scripts. (5) Added Layout Service integration with C4-infographic layout. (6) Followed TEXT_SERVICE_API_REFERENCE.md format. |
| 1.1.0 | Dec 2024 | Contract alignment: Added diagnostic metadata fields, updated themes endpoint. |
| 1.0.0 | Dec 2024 | Initial release with Director coordination endpoints. |

---

## Related Documents

- [TEXT_SERVICE_API_REFERENCE.md](./TEXT_SERVICE_API_REFERENCE.md) - Text Service API Reference
- [SERVICE_CAPABILITIES_SPEC.md](./SERVICE_CAPABILITIES_SPEC.md) - Coordination endpoint specification
- [SLIDE_GENERATION_INPUT_SPEC.md](./SLIDE_GENERATION_INPUT_SPEC.md) - Canonical slide generation reference
