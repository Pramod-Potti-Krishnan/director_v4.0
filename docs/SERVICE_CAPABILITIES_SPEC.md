# Service Capabilities Endpoint Specification

## Overview

This document defines the standard endpoints that all services must implement for coordination with Strawman Service. These endpoints enable intelligent decision-making at strawman generation time.

**These endpoints support the 4-Step Strawman Process**:
1. **Step 1**: Determine Storyline & Messages → AI deep thought + playbooks
2. **Step 2**: Select Layouts → Use endpoints here for layout + grid size
3. **Step 3**: Select Content Variants → Use `/can-handle` and `/recommend-*` endpoints
4. **Step 4**: Refine & Personalize → Assemble final personalized content

**Related Documents**:
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - Phased rollout plan with team assignments
- [SERVICE_COORDINATION_REQUIREMENTS.md](./SERVICE_COORDINATION_REQUIREMENTS.md) - Architecture and playbook details

---

## Implementation Phases

| Phase | Endpoints | Purpose |
|-------|-----------|---------|
| **Phase 1** | `GET /capabilities` | Services describe what they can do |
| **Phase 2** | `POST /can-handle` | Services answer "can you handle this content?" |
| **Phase 3** | `POST /recommend-*` | Services recommend variants/layouts/charts |

See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for detailed team assignments and timeline.

---

## Critical Concept: Layout Grid Size

**Every layout provides exact content zone dimensions.** This is the foundational parameter that enables intelligent content placement.

When a layout is selected, it exposes:
- **Fixed zones**: Title, subtitle (optional), footer, logo (optional)
- **Content zones**: Main areas for text, images, charts, diagrams
- **Exact dimensions**: Width × Height in pixels for each zone

Content services use these dimensions to:
1. Recommend variants that fit the available space
2. Generate content sized correctly for the zone
3. Avoid overflow or underutilization

---

## Critical Concept: Layout-SlideType-Variant Hierarchy

**⚠️ IMPORTANT**: Layouts, slide types, and variants are **NOT independent**. They form a hierarchical constraint system:

```
Layout Template
    └── supports → Slide Types
                      └── have → Variants
```

### The Relationship

| Level | Description | Example |
|-------|-------------|---------|
| **Layout** | The visual template (L25, C01, H01, etc.) | L25, C01 |
| **Slide Type** | Category of content structure | matrix, grid, comparison, metrics |
| **Variant** | Specific configuration of a slide type | matrix_2x2, matrix_2x3, grid_2x3 |

### Example: Matrix Slide Type

```
L25 (Legacy Content Layout)
 └── supports: matrix, grid, comparison, sequential, metrics
       │
       └── matrix slide type
             └── variants: matrix_2x2, matrix_2x3, matrix_3x2, matrix_3x3

C01 (Content 3-Column)
 └── supports: matrix, comparison, metrics
       │
       └── matrix slide type
             └── variants: matrix_2x2, matrix_2x3 (NOT matrix_3x3 - doesn't fit)
```

### Constraint Rules

1. **Layout constrains Slide Types**: Not all slide types work with all layouts
   - Example: `H01` (Hero) only supports `hero` slide type, not `matrix`

2. **Layout constrains Variants**: Even if a slide type is supported, not all variants may fit
   - Example: `C01` supports `matrix`, but `matrix_3x3` may not fit in 3-column grid

3. **Slide Type constrains Variants**: Variants belong to a specific slide type
   - Example: `matrix_2x3` is a variant of `matrix`, NOT of `grid`

### Layout-SlideType Compatibility Matrix

| Layout | Supported Slide Types |
|--------|----------------------|
| **L25** | matrix, grid, comparison, sequential, metrics, table |
| **C01** | matrix, comparison, metrics (3-column optimized) |
| **C02** | grid, comparison (2-column optimized) |
| **H01** | hero (title slides only) |
| **H02** | hero (section dividers only) |
| **L02** | chart (analytics service) |

### Implications for the 4-Step Process

This hierarchy affects **Steps 2 and 3** of the Strawman process:

```
Step 2: Select Layout
    │
    ├── Layout choice CONSTRAINS available slide types
    │
    ▼
Step 3: Select Content Variant
    │
    ├── Must select from slide types supported by chosen layout
    ├── Must select variant that fits layout's grid size
    │
    ▼
Bidirectional Negotiation:
    - If message needs matrix_3x3, layout must support it
    - If layout is C01 (3-col), matrix_3x3 won't fit → adjust variant OR layout
```

### Service Response: Layout with Supported Types

Layout Service's `GET /api/layouts/{id}` should include:

```json
{
  "layout_id": "L25",
  "supported_slide_types": [
    {
      "slide_type": "matrix",
      "service": "text-service",
      "supported_variants": ["matrix_2x2", "matrix_2x3", "matrix_3x2", "matrix_3x3"]
    },
    {
      "slide_type": "grid",
      "service": "text-service",
      "supported_variants": ["grid_2x2", "grid_2x3", "grid_3x3"]
    },
    {
      "slide_type": "chart",
      "service": "analytics-service",
      "supported_variants": ["bar", "line", "pie", "doughnut"]
    }
  ]
}
```

### Text Service Response: Variants with Layout Compatibility

Text Service's `/capabilities` should include:

```json
{
  "slide_types": {
    "matrix": {
      "description": "2D grid of items with headers",
      "variants": [
        {
          "variant_id": "matrix_2x2",
          "item_count": 4,
          "compatible_layouts": ["L25", "C01", "C02"],
          "min_space_required": {"width": 1200, "height": 600}
        },
        {
          "variant_id": "matrix_2x3",
          "item_count": 6,
          "compatible_layouts": ["L25", "C01"],
          "min_space_required": {"width": 1600, "height": 600}
        },
        {
          "variant_id": "matrix_3x3",
          "item_count": 9,
          "compatible_layouts": ["L25"],
          "min_space_required": {"width": 1800, "height": 800}
        }
      ]
    }
  }
}
```

---

## Phase 1: Capabilities Endpoint

### Endpoint Definition

```
GET /capabilities
```

**Response Status**:
- `200 OK`: Returns capabilities object
- `503 Service Unavailable`: Service not ready

### Standard Response Schema

Every service MUST return a response conforming to this schema:

```json
{
  "service": "string",           // Service identifier (kebab-case)
  "version": "string",           // Semantic version (e.g., "1.2.0")
  "status": "healthy|degraded",  // Current operational status

  "capabilities": {
    // Service-specific capabilities
  },

  "content_signals": {
    "handles_well": ["string"],   // Content types this service excels at
    "handles_poorly": ["string"], // Content types to avoid routing here
    "keywords": ["string"]        // Keywords that suggest this service
  },

  "endpoints": {
    // Available endpoints for this service
  }
}
```

---

## Service-Specific Capabilities

### Layout Service v7.5

**Owner**: Layout Service Team

```json
{
  "service": "layout-service",
  "version": "7.5.0",
  "status": "healthy",

  "capabilities": {
    "layout_series": ["L", "C", "H"],
    "total_layouts": 99,
    "supports_themes": true,
    "theme_count": 5,
    "exposes_grid_size": true
  },

  "layout_series_info": {
    "L": {
      "name": "Legacy Series",
      "supports_themes": false,
      "count": 30,
      "use_for": ["backward_compatibility", "simple_layouts", "charts"]
    },
    "C": {
      "name": "Content Series",
      "supports_themes": true,
      "count": 25,
      "use_for": ["themed_content", "sidebars", "complex_layouts"]
    },
    "H": {
      "name": "Hero Series",
      "supports_themes": true,
      "count": 15,
      "use_for": ["title_slides", "section_dividers", "full_bleed_images"]
    }
  },

  "standard_zones": {
    "title": {"required": true, "description": "Slide title area"},
    "subtitle": {"required": false, "description": "Optional subtitle/tagline"},
    "footer": {"required": true, "description": "Footer with page number, date"},
    "logo": {"required": false, "description": "Company/client logo"},
    "main_content": {"required": true, "description": "Primary content area(s)"}
  },

  "endpoints": {
    "capabilities": "GET /capabilities",
    "list_layouts": "GET /api/layouts",
    "get_layout": "GET /api/layouts/{id}",
    "recommend_layout": "POST /api/recommend-layout",
    "can_fit": "POST /api/can-fit",
    "list_themes": "GET /api/themes",
    "get_theme": "GET /api/themes/{id}"
  }
}
```

### Layout Service: GET /api/layouts/{id} (with Grid Size)

**This is the critical endpoint that exposes exact content zone dimensions.**

**Response**:
```json
{
  "layout_id": "C01",
  "name": "Three Column Content",
  "series": "C",
  "supports_themes": true,

  "slide_dimensions": {
    "width": 1920,
    "height": 1080,
    "unit": "pixels"
  },

  "content_zones": [
    {
      "zone_id": "title",
      "zone_type": "fixed",
      "required": true,
      "position": {"x": 60, "y": 40},
      "dimensions": {"width": 1800, "height": 80},
      "accepts": ["text"]
    },
    {
      "zone_id": "subtitle",
      "zone_type": "fixed",
      "required": false,
      "position": {"x": 60, "y": 130},
      "dimensions": {"width": 1800, "height": 50},
      "accepts": ["text"]
    },
    {
      "zone_id": "main_content",
      "zone_type": "content",
      "required": true,
      "position": {"x": 60, "y": 200},
      "dimensions": {"width": 1800, "height": 750},
      "accepts": ["text", "image", "chart", "diagram", "illustration"],
      "sub_zones": [
        {
          "zone_id": "col_1",
          "position": {"x": 60, "y": 200},
          "dimensions": {"width": 560, "height": 750}
        },
        {
          "zone_id": "col_2",
          "position": {"x": 640, "y": 200},
          "dimensions": {"width": 560, "height": 750}
        },
        {
          "zone_id": "col_3",
          "position": {"x": 1220, "y": 200},
          "dimensions": {"width": 560, "height": 750}
        }
      ]
    },
    {
      "zone_id": "footer",
      "zone_type": "fixed",
      "required": true,
      "position": {"x": 60, "y": 1020},
      "dimensions": {"width": 1800, "height": 40},
      "accepts": ["text"]
    },
    {
      "zone_id": "logo",
      "zone_type": "fixed",
      "required": false,
      "position": {"x": 1700, "y": 30},
      "dimensions": {"width": 180, "height": 60},
      "accepts": ["image"]
    }
  ],

  "content_capacity": {
    "max_columns": 3,
    "max_rows": 1,
    "ideal_topic_count": [3, 6],
    "supports_images": true,
    "supports_charts": false
  }
}
```

**Key Grid Size Fields**:
| Field | Purpose |
|-------|---------|
| `content_zones[].dimensions` | Exact width × height for each zone |
| `content_zones[].position` | X/Y coordinates on slide |
| `content_zones[].accepts` | What content types fit this zone |
| `sub_zones` | For multi-column/row layouts, individual cell dimensions |

---

### Text Service v1.2

**Owner**: Text Service Team

```json
{
  "service": "text-service",
  "version": "1.2.0",
  "status": "healthy",

  "capabilities": {
    "slide_types": [
      "matrix", "grid", "comparison", "sequential",
      "metrics", "table", "hero", "timeline", "process"
    ],
    "variants": [
      "matrix_2x2", "matrix_2x3", "grid_2x3", "grid_3x3",
      "comparison_2col", "comparison_3col", "sequential_4step",
      "metrics_3col", "metrics_4col", "table_standard"
    ],
    "max_items_per_slide": 8,
    "supports_themes": false,
    "parallel_generation": true
  },

  "content_signals": {
    "handles_well": [
      "structured_content", "bullet_points", "comparisons",
      "processes", "features_benefits", "step_by_step"
    ],
    "handles_poorly": [
      "charts", "data_visualization", "diagrams", "infographics"
    ],
    "keywords": [
      "compare", "features", "benefits", "steps", "process",
      "matrix", "grid", "table", "metrics", "KPIs"
    ]
  },

  "endpoints": {
    "capabilities": "GET /capabilities",
    "generate": "POST /v1.2/generate",
    "can_handle": "POST /v1.2/can-handle",
    "recommend_variant": "POST /v1.2/recommend-variant",
    "hero_title": "POST /v1.2/hero/title-with-image",
    "hero_section": "POST /v1.2/hero/section-with-image",
    "hero_closing": "POST /v1.2/hero/closing-with-image"
  }
}
```

---

### Analytics Service v3

**Owner**: Analytics Service Team

```json
{
  "service": "analytics-service",
  "version": "3.0.0",
  "status": "healthy",

  "capabilities": {
    "slide_types": ["chart", "visualization", "data_display"],
    "chart_types": [
      "bar_vertical", "bar_horizontal", "bar_grouped",
      "line", "area", "pie", "doughnut",
      "scatter", "bubble", "radar",
      "treemap", "sankey", "funnel_chart"
    ],
    "supports_themes": true,
    "can_generate_data": true
  },

  "content_signals": {
    "handles_well": [
      "numerical_data", "time_series", "comparisons_with_numbers",
      "distributions", "trends", "percentages"
    ],
    "handles_poorly": [
      "pure_text_content", "bullet_points", "processes_without_data"
    ],
    "keywords": [
      "chart", "graph", "trend", "over time", "percentage",
      "growth", "decline", "revenue", "sales", "distribution"
    ],
    "pattern_detection": {
      "time_series": ["over time", "by quarter", "by month", "trend"],
      "comparison": ["vs", "compared to", "difference between"],
      "composition": ["breakdown", "distribution", "share of"]
    }
  },

  "chart_recommendations": {
    "time_series": ["line", "area"],
    "comparison": ["bar_vertical", "bar_horizontal", "bar_grouped"],
    "composition": ["pie", "doughnut", "treemap"],
    "correlation": ["scatter", "bubble"]
  },

  "endpoints": {
    "capabilities": "GET /capabilities",
    "generate": "POST /api/v1/analytics/L02/{chart_type}",
    "can_handle": "POST /api/v1/analytics/can-handle",
    "recommend_chart": "POST /api/v1/analytics/recommend-chart"
  }
}
```

---

### Illustrator Service v1.0

**Owner**: Illustrator Service Team

```json
{
  "service": "illustrator-service",
  "version": "1.0.0",
  "status": "healthy",

  "capabilities": {
    "slide_types": ["infographic", "visual_metaphor"],
    "visualization_types": ["pyramid", "funnel", "concentric_circles"],
    "supports_themes": true,
    "ai_generated_content": true
  },

  "content_signals": {
    "handles_well": [
      "hierarchies", "levels", "stages", "layers", "visual_metaphors"
    ],
    "handles_poorly": [
      "data_heavy_content", "many_items", "tabular_data"
    ],
    "keywords": [
      "pyramid", "funnel", "hierarchy", "levels", "stages",
      "core", "layers", "ecosystem"
    ]
  },

  "specializations": {
    "pyramid": {
      "best_for": ["hierarchy", "levels", "foundation to peak", "priority"],
      "keywords": ["pyramid", "levels", "hierarchy", "tier", "foundation"],
      "ideal_item_count": {"min": 3, "max": 6, "optimal": 4}
    },
    "funnel": {
      "best_for": ["conversion", "stages", "narrowing process", "pipeline"],
      "keywords": ["funnel", "conversion", "pipeline", "stages", "leads"],
      "ideal_item_count": {"min": 3, "max": 5, "optimal": 4}
    },
    "concentric_circles": {
      "best_for": ["core to periphery", "layers", "ecosystem"],
      "keywords": ["core", "layers", "surrounding", "ecosystem", "center"],
      "ideal_item_count": {"min": 3, "max": 5, "optimal": 4}
    }
  },

  "endpoints": {
    "capabilities": "GET /capabilities",
    "pyramid": "POST /v1.0/pyramid/generate",
    "funnel": "POST /v1.0/funnel/generate",
    "concentric": "POST /v1.0/concentric/generate",
    "can_handle": "POST /v1.0/can-handle",
    "recommend_visual": "POST /v1.0/recommend-visual"
  }
}
```

---

### Diagram Service v1.0

**Owner**: Diagram Service Team

```json
{
  "service": "diagram-service",
  "version": "1.0.0",
  "status": "healthy",

  "capabilities": {
    "slide_types": ["diagram", "flowchart", "architecture"],
    "diagram_types": [
      "flowchart", "block_diagram", "sequence_diagram", "entity_relationship"
    ],
    "supports_themes": true,
    "mermaid_output": true
  },

  "content_signals": {
    "handles_well": [
      "processes", "workflows", "decision_trees",
      "system_architecture", "relationships", "sequences"
    ],
    "handles_poorly": [
      "pure_data", "bullet_lists", "comparisons_without_flow"
    ],
    "keywords": [
      "flow", "process", "workflow", "architecture", "components",
      "sequence", "interaction", "diagram"
    ]
  },

  "diagram_type_signals": {
    "flowchart": {
      "best_for": ["process", "workflow", "decision tree"],
      "keywords": ["flow", "process", "steps", "if/then", "decision"]
    },
    "block_diagram": {
      "best_for": ["architecture", "system components"],
      "keywords": ["architecture", "components", "system", "modules"]
    },
    "sequence_diagram": {
      "best_for": ["interactions", "message flow", "API calls"],
      "keywords": ["sequence", "interaction", "message", "request/response"]
    },
    "entity_relationship": {
      "best_for": ["data models", "relationships", "database schema"],
      "keywords": ["entity", "relationship", "database", "model"]
    }
  },

  "endpoints": {
    "capabilities": "GET /capabilities",
    "generate": "POST /v1.0/generate",
    "can_handle": "POST /v1.0/can-handle",
    "recommend_diagram": "POST /v1.0/recommend-diagram"
  }
}
```

---

## Phase 2: Content Negotiation Endpoints

### POST /can-handle

**Purpose**: Answer "Can you handle this specific content within the given space?"

**Request Schema** (standard for all content services):
```json
{
  "slide_content": {
    "title": "Q4 Revenue Analysis",
    "topics": ["Revenue grew 15%", "New markets contributed 30%", "Cost reduction achieved"],
    "topic_count": 3
  },
  "content_hints": {
    "has_numbers": true,
    "is_comparison": false,
    "is_time_based": false,
    "detected_keywords": ["revenue", "growth", "percentage"]
  },
  "available_space": {
    "width": 1800,
    "height": 750,
    "sub_zones": [
      {"zone_id": "col_1", "width": 560, "height": 750},
      {"zone_id": "col_2", "width": 560, "height": 750},
      {"zone_id": "col_3", "width": 560, "height": 750}
    ]
  }
}
```

**Response Schema** (standard for all content services):
```json
{
  "can_handle": true,
  "confidence": 0.85,
  "reason": "3 KPI metrics with numerical data - fits well in 3-column 560px zones",
  "suggested_approach": "metrics",
  "space_utilization": {
    "fits_well": true,
    "estimated_fill_percent": 85
  }
}
```

**Confidence Score Guidelines**:
| Score | Meaning |
|-------|---------|
| 0.90+ | Excellent fit, high confidence |
| 0.70-0.89 | Good fit, can handle well |
| 0.50-0.69 | Acceptable, but other services might be better |
| < 0.50 | Poor fit, prefer other service |

---

## Phase 3: Recommendation Endpoints

### Text Service: POST /recommend-variant

**Request** (includes available space from layout):
```json
{
  "slide_content": {
    "title": "Key Metrics",
    "topics": ["Revenue: $4.2M", "Users: 50K", "NPS: 72"],
    "topic_count": 3
  },
  "available_space": {
    "width": 1800,
    "height": 750,
    "layout_id": "C01"
  }
}
```

**Response**:
```json
{
  "recommended_variants": [
    {
      "variant_id": "metrics_3col",
      "confidence": 0.92,
      "reason": "3 KPIs with numbers, fits perfectly in 1800×750 space",
      "requires_space": {"width": 1680, "height": 600}
    },
    {
      "variant_id": "comparison_3col",
      "confidence": 0.70,
      "reason": "3 items could compare",
      "requires_space": {"width": 1680, "height": 650}
    }
  ],
  "not_recommended": [
    {"variant_id": "grid_2x3", "reason": "Needs 6 topics, only 3 provided"}
  ]
}
```

---

### Analytics Service: POST /recommend-chart

**Request**:
```json
{
  "slide_content": {
    "title": "Revenue Trend",
    "topics": ["Show revenue growth over 4 quarters"],
    "detected_patterns": ["time_series"]
  }
}
```

**Response**:
```json
{
  "recommended_charts": [
    {"chart_type": "line", "confidence": 0.95, "reason": "Time series best shown as line"},
    {"chart_type": "area", "confidence": 0.80, "reason": "Area also works for trends"}
  ]
}
```

---

### Illustrator Service: POST /recommend-visual

**Request**:
```json
{
  "slide_content": {
    "title": "Marketing Funnel",
    "topics": ["Awareness", "Interest", "Decision", "Action"],
    "topic_count": 4
  }
}
```

**Response**:
```json
{
  "recommended_visuals": [
    {"visual_type": "funnel", "confidence": 0.95, "reason": "Classic funnel stages"},
    {"visual_type": "pyramid", "confidence": 0.60, "reason": "Could show as hierarchy"}
  ]
}
```

---

### Diagram Service: POST /recommend-diagram

**Request**:
```json
{
  "slide_content": {
    "title": "User Registration Flow",
    "topics": ["User enters email", "System validates", "Send confirmation", "User activates"],
    "topic_count": 4
  }
}
```

**Response**:
```json
{
  "recommended_diagrams": [
    {"diagram_type": "flowchart", "confidence": 0.90, "reason": "Sequential process flow"},
    {"diagram_type": "sequence_diagram", "confidence": 0.70, "reason": "Could show as interactions"}
  ]
}
```

---

### Layout Service: POST /recommend-layout

**Request**:
```json
{
  "content_type": "metrics",
  "topic_count": 3,
  "service": "text-service",
  "variant": "metrics_3col",
  "preferences": {
    "series_preference": ["C", "L"],
    "supports_theme": true
  }
}
```

**Response** (includes content zones with grid dimensions):
```json
{
  "recommended_layouts": [
    {
      "layout_id": "C01",
      "series": "C",
      "confidence": 0.90,
      "reason": "3-column themed layout, 560px per column ideal for metrics",
      "content_zones": {
        "main_content": {
          "width": 1800,
          "height": 750,
          "columns": 3,
          "column_width": 560
        }
      }
    },
    {
      "layout_id": "L25",
      "series": "L",
      "confidence": 0.75,
      "reason": "Standard content layout",
      "content_zones": {
        "main_content": {
          "width": 1700,
          "height": 700,
          "columns": 1,
          "column_width": 1700
        }
      }
    }
  ]
}
```

**Important**: The `content_zones` in the response gives content services the exact space available, enabling them to recommend variants that fit.

---

### Layout Service: POST /can-fit

**Request**:
```json
{
  "layout_id": "C01",
  "content_zones_needed": 3,
  "content_type": "text"
}
```

**Response**:
```json
{
  "can_fit": true,
  "layout_id": "C01",
  "content_zones_available": 4,
  "suggested_layout": null
}
```

---

## Strawman Integration Pattern

### Phase 1: Capabilities Discovery (Startup)

```python
class StrawmanService:
    async def initialize(self):
        """Cache capabilities from all services at startup."""
        self.service_capabilities = {}

        services = [
            ("layout-service", self.config.layout_service_url),
            ("text-service", self.config.text_service_url),
            ("analytics-service", self.config.analytics_service_url),
            ("illustrator-service", self.config.illustrator_service_url),
            ("diagram-service", self.config.diagram_service_url),
        ]

        for service_name, url in services:
            try:
                response = await self.http.get(f"{url}/capabilities")
                self.service_capabilities[service_name] = response
                logger.info(f"Loaded capabilities: {service_name} v{response['version']}")
            except Exception as e:
                logger.warning(f"Could not load {service_name}: {e}")
```

### Phase 2: Service Selection (Per-Slide)

```python
async def select_service(self, slide_content: dict) -> dict:
    """Query all content services, return highest confidence."""
    content_services = ["text-service", "analytics-service",
                        "illustrator-service", "diagram-service"]

    candidates = []
    for service in content_services:
        url = self.service_urls[service]
        response = await self.http.post(
            f"{url}/can-handle",
            json={"slide_content": slide_content, "content_hints": self.analyze_content(slide_content)}
        )
        if response["can_handle"]:
            candidates.append({
                "service": service,
                "confidence": response["confidence"],
                "reason": response["reason"]
            })

    if candidates:
        return max(candidates, key=lambda x: x["confidence"])

    # Fallback to text-service
    return {"service": "text-service", "confidence": 0.5, "reason": "fallback"}
```

### Phase 3: Recommendations (Per-Slide)

```python
async def get_recommendations(self, service: str, slide_content: dict) -> dict:
    """Get variant and layout recommendations."""
    url = self.service_urls[service]

    # Get variant recommendation from content service
    variant_response = await self.http.post(
        f"{url}/recommend-variant",  # or recommend-chart, recommend-visual, etc.
        json={"slide_content": slide_content}
    )

    # Get layout recommendation from Layout Service
    layout_response = await self.http.post(
        f"{self.service_urls['layout-service']}/api/recommend-layout",
        json={
            "content_type": variant_response.get("suggested_approach"),
            "topic_count": len(slide_content.get("topics", [])),
            "service": service,
            "variant": variant_response["recommended_variants"][0]["variant_id"]
        }
    )

    return {
        "variant": variant_response["recommended_variants"][0],
        "layout": layout_response["recommended_layouts"][0]
    }
```

---

## Implementation Checklist by Team

### Layout Service Team

| Phase | Endpoint | Status |
|-------|----------|--------|
| 1 | `GET /capabilities` | [ ] |
| 1 | `GET /api/layouts` | [ ] |
| 3 | `POST /api/recommend-layout` | [ ] |
| 3 | `POST /api/can-fit` | [ ] |

### Text Service Team

| Phase | Endpoint | Status |
|-------|----------|--------|
| 1 | `GET /capabilities` | [ ] |
| 2 | `POST /v1.2/can-handle` | [ ] |
| 3 | `POST /v1.2/recommend-variant` | [ ] |

### Analytics Service Team

| Phase | Endpoint | Status |
|-------|----------|--------|
| 1 | `GET /capabilities` | [ ] |
| 2 | `POST /api/v1/analytics/can-handle` | [ ] |
| 3 | `POST /api/v1/analytics/recommend-chart` | [ ] |

### Illustrator Service Team

| Phase | Endpoint | Status |
|-------|----------|--------|
| 1 | `GET /capabilities` | [ ] |
| 2 | `POST /v1.0/can-handle` | [ ] |
| 3 | `POST /v1.0/recommend-visual` | [ ] |

### Diagram Service Team

| Phase | Endpoint | Status |
|-------|----------|--------|
| 1 | `GET /capabilities` | [ ] |
| 2 | `POST /v1.0/can-handle` | [ ] |
| 3 | `POST /v1.0/recommend-diagram` | [ ] |

---

## Error Handling

### Timeout Handling
```json
{
  "error": "timeout",
  "service": "analytics-service",
  "fallback_used": true,
  "fallback_service": "text-service"
}
```

### Service Unavailable
```json
{
  "error": "service_unavailable",
  "service": "illustrator-service",
  "cached_capabilities_used": true
}
```

### Fallback Strategy
1. If a service times out (>2s), skip and try next
2. If no service responds, use text-service as default
3. If layout recommendation fails, use L25 as default
4. Cache last-known capabilities for degraded mode

---

## Versioning

When capabilities change:
1. Increment service version in response
2. Strawman will re-fetch on next startup
3. New capabilities are additive (don't break existing)
4. Deprecation: Add to `deprecated` array before removal

---

*Document Version: 5.0*
*Updated: December 2024*
*Changes in v5.0:*
- *Added Critical Concept: Layout-SlideType-Variant Hierarchy*
- *Documented constraint rules (layout constrains slide types and variants)*
- *Added Layout-SlideType Compatibility Matrix*
- *Updated Layout Service response to include supported_slide_types*
- *Updated Text Service capabilities to include variant layout compatibility*

*Changes in v4.0:*
- *Added 4-Step Strawman Process reference in Overview*
- *Aligned with SERVICE_COORDINATION_REQUIREMENTS.md v6.0*

*Changes in v3.0:*
- *Added Critical Concept: Layout Grid Size section*
- *Added content_zones with exact dimensions to Layout Service responses*
- *Updated /can-handle to accept available_space parameter*
- *Updated /recommend-variant to include space requirements*
- *Updated /recommend-layout to return content_zones*

*Related: IMPLEMENTATION_PLAN.md, SERVICE_COORDINATION_REQUIREMENTS.md*
