# Layout Service Capabilities for Director Integration

**Version**: 7.5.7
**Base URL**: `http://localhost:8504` (local) | Production TBD
**Last Updated**: December 2024

---

## Overview

The Layout Service (v7.5-main) now exposes **Director coordination endpoints** that enable the Strawman system to:

1. Discover available layouts and their capabilities
2. Get exact content zone dimensions (grid + pixels) for any layout
3. Request layout recommendations based on content type
4. Validate if content fits in a specified layout
5. **NEW**: Generate dynamic X-series layouts with sub-zones

**Key Insight**: Grid size is the foundational parameter. Content services cannot recommend variants without knowing exact dimensions of content zones.

> **Note**: Theme capabilities (typography tokens, CSS variables) are documented in `layout_builder_main/v7.5-main/docs/THEME_SERVICE_CAPABILITIES.md`.

---

## Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/capabilities` | GET | Service discovery and capabilities |
| `/api/layouts` | GET | List all 22 templates with metadata |
| `/api/layouts/{id}` | GET | **Critical** - Full slot definitions with pixel dimensions |
| `/api/recommend-layout` | POST | Recommend layout based on content type |
| `/api/can-fit` | POST | Validate content fits in layout |
| `/api/dynamic-layouts/generate` | POST | **NEW** - Generate X-series dynamic layouts |
| `/api/dynamic-layouts/{layout_id}` | GET | **NEW** - Get dynamic layout details |
| `/api/dynamic-layouts` | GET | **NEW** - List all dynamic layouts |
| `/api/dynamic-layouts/patterns` | GET | **NEW** - List split patterns |
| `/api/dynamic-layouts/base-layouts` | GET | **NEW** - List base layouts for X-series |

---

## 1. GET /capabilities

Returns service capabilities for Director coordination.

### Response

```json
{
  "service": "layout-service",
  "version": "7.5.5",
  "status": "healthy",
  "capabilities": {
    "template_series": ["H", "C", "V", "I", "S", "B", "L"],
    "total_templates": 22,
    "supports_themes": true,
    "theme_count": 4,
    "exposes_grid_size": true,
    "grid_system": {
      "columns": 32,
      "rows": 18,
      "slide_width": 1920,
      "slide_height": 1080
    }
  },
  "template_series": {
    "H": {
      "name": "Hero Series",
      "description": "Full-bleed title, section, and closing slides",
      "count": 4,
      "use_for": ["title_slides", "section_dividers", "closing_slides"]
    },
    "C": {
      "name": "Content Series",
      "description": "Single content area slides",
      "count": 4,
      "use_for": ["text_content", "single_chart", "single_diagram", "infographic"]
    },
    "V": {
      "name": "Visual + Text Series",
      "description": "Visual element with text insights",
      "count": 4,
      "use_for": ["chart_analysis", "diagram_explanation", "image_description"]
    },
    "I": {
      "name": "Image Split Series",
      "description": "Full-height image with content",
      "count": 4,
      "use_for": ["image_heavy_content", "photo_stories"]
    },
    "S": {
      "name": "Split Series",
      "description": "Two-column layouts",
      "count": 2,
      "use_for": ["comparisons", "before_after", "two_charts"]
    },
    "B": {
      "name": "Blank Series",
      "description": "Empty canvas",
      "count": 1,
      "use_for": ["custom_layouts", "freeform"]
    },
    "L": {
      "name": "Backend Layout Series",
      "description": "Core backend layouts for Director/Text Service",
      "count": 3,
      "use_for": ["director_generated", "text_service", "analytics_service"]
    }
  },
  "standard_zones": {
    "title": {"required": true, "description": "Slide title area"},
    "subtitle": {"required": false, "description": "Optional subtitle"},
    "content": {"required": true, "description": "Primary content area"},
    "footer": {"required": false, "description": "Footer area"},
    "logo": {"required": false, "description": "Company logo area"}
  },
  "endpoints": {
    "capabilities": "GET /capabilities",
    "list_layouts": "GET /api/layouts",
    "get_layout": "GET /api/layouts/{layout_id}",
    "recommend_layout": "POST /api/recommend-layout",
    "can_fit": "POST /api/can-fit"
  }
}
```

---

## 2. GET /api/layouts

Lists all available layouts/templates with metadata.

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | string | Filter by category: `hero`, `content`, `visual`, `image`, `split`, `blank`, `backend` |

### Response

```json
{
  "layouts": [
    {
      "layout_id": "L25",
      "name": "Main Content Shell",
      "series": "L",
      "category": "backend",
      "description": "Standard content slide with title, subtitle, and rich content area",
      "theming_enabled": true,
      "base_layout": null,
      "primary_content_types": ["content", "html"],
      "main_content_dimensions": {
        "x": 60.0,
        "y": 240.0,
        "width": 1800.0,
        "height": 720.0
      }
    }
    // ... more layouts
  ],
  "total": 22,
  "categories": {
    "hero": ["H1-generated", "H1-structured", "H2-section", "H3-closing"],
    "content": ["C1-text", "C3-chart", "C4-infographic", "C5-diagram"],
    "visual": ["V1-image-text", "V2-chart-text", "V3-diagram-text", "V4-infographic-text"],
    "image": ["I1-image-left", "I2-image-right", "I3-image-left-narrow", "I4-image-right-narrow"],
    "split": ["S3-two-visuals", "S4-comparison"],
    "blank": ["B1-blank"],
    "backend": ["L02", "L25", "L29"]
  }
}
```

---

## 3. GET /api/layouts/{layout_id}

**CRITICAL ENDPOINT** - Returns detailed layout specification with exact content zone dimensions.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `layout_id` | string | Layout ID (e.g., `L25`, `C1-text`, `H1-structured`) |

### Response

```json
{
  "layout_id": "L25",
  "name": "Main Content Shell",
  "series": "L",
  "category": "backend",
  "description": "Standard content slide with title, subtitle, and rich content area (Text Service)",
  "theming_enabled": true,
  "base_layout": null,
  "slide_dimensions": {
    "width": 1920,
    "height": 1080,
    "unit": "pixels"
  },
  "slots": {
    "title": {
      "grid_row": "2/3",
      "grid_column": "2/32",
      "tag": "title",
      "accepts": ["text"],
      "required": false,
      "description": null,
      "default_text": "Slide Title",
      "format_owner": null,
      "pixels": {
        "x": 60.0,
        "y": 60.0,
        "width": 1800.0,
        "height": 60.0
      }
    },
    "subtitle": {
      "grid_row": "3/4",
      "grid_column": "2/32",
      "tag": "subtitle",
      "accepts": ["text"],
      "required": false,
      "default_text": "Subtitle",
      "pixels": {
        "x": 60.0,
        "y": 120.0,
        "width": 1800.0,
        "height": 60.0
      }
    },
    "content": {
      "grid_row": "5/17",
      "grid_column": "2/32",
      "tag": "content",
      "accepts": ["content", "html"],
      "required": false,
      "description": "Main content area (1800x720px)",
      "format_owner": "text_service",
      "pixels": {
        "x": 60.0,
        "y": 240.0,
        "width": 1800.0,
        "height": 720.0
      }
    },
    "footer": {
      "grid_row": "18/19",
      "grid_column": "2/7",
      "tag": "footer",
      "accepts": ["text"],
      "pixels": {
        "x": 60.0,
        "y": 1020.0,
        "width": 300.0,
        "height": 60.0
      }
    },
    "logo": {
      "grid_row": "17/19",
      "grid_column": "30/32",
      "tag": "logo",
      "accepts": ["image", "emoji"],
      "pixels": {
        "x": 1740.0,
        "y": 960.0,
        "width": 120.0,
        "height": 120.0
      }
    }
  },
  "defaults": {
    "background_color": "#ffffff"
  }
}
```

### Slot Properties

| Property | Description |
|----------|-------------|
| `grid_row` | CSS grid row (e.g., "5/17" = rows 5-17) |
| `grid_column` | CSS grid column (e.g., "2/32" = columns 2-32) |
| `tag` | Content tag for styling (title, body, chart, etc.) |
| `accepts` | Array of accepted content types |
| `required` | Whether slot is required |
| `format_owner` | Service that owns the format (`text_service`, `analytics_service`) |
| `pixels` | Exact pixel dimensions (x, y, width, height) |

---

## 4. POST /api/recommend-layout

Recommend best layout for given content type and requirements.

### Request Body

```json
{
  "content_type": "chart",
  "topic_count": 1,
  "service": "director",
  "variant": "with_analysis",
  "preferences": {
    "image_position": "left"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content_type` | string | Yes | `chart`, `diagram`, `text`, `hero`, `section`, `closing`, `comparison`, `image`, `infographic` |
| `topic_count` | int | No | Number of topics/items (1-10), default: 1 |
| `service` | string | No | Requesting service: `director`, `text-service`, `analytics-service` |
| `variant` | string | No | Content variant: `with_analysis`, `single`, `split`, etc. |
| `preferences` | object | No | Additional preferences (e.g., `image_position`) |

### Response

```json
{
  "recommended_layouts": [
    {
      "layout_id": "V2-chart-text",
      "confidence": 0.98,
      "reason": "Chart on left with text insights on right",
      "main_content_slots": [
        {
          "grid_row": "4/18",
          "grid_column": "2/20",
          "tag": "chart",
          "accepts": ["chart"],
          "description": "Chart area (1080x840px)",
          "pixels": {
            "x": 60.0,
            "y": 180.0,
            "width": 1080.0,
            "height": 840.0
          },
          "slot_name": "content_left"
        },
        {
          "grid_row": "4/18",
          "grid_column": "20/32",
          "tag": "body",
          "accepts": ["body", "table", "html"],
          "description": "Text/observations (720x840px)",
          "pixels": {
            "x": 1140.0,
            "y": 180.0,
            "width": 720.0,
            "height": 840.0
          },
          "slot_name": "content_right"
        }
      ]
    },
    {
      "layout_id": "C3-chart",
      "confidence": 0.95,
      "reason": "Single chart with full-width content area",
      "main_content_slots": [...]
    }
  ],
  "fallback": "L25",
  "request_summary": {
    "content_type": "chart",
    "topic_count": 1,
    "service": "director",
    "variant": "with_analysis"
  }
}
```

### Recommendation Logic

| Content Type | Topic Count | Recommended Layout |
|--------------|-------------|-------------------|
| `hero` | - | H1-structured, L29 |
| `section` | - | H2-section |
| `closing` | - | H3-closing |
| `chart` | 1 | C3-chart |
| `chart` | 2 | S3-two-visuals |
| `chart` + `with_analysis` | 1 | V2-chart-text |
| `diagram` | 1 | C5-diagram, L02 |
| `diagram` + `with_analysis` | 1 | V3-diagram-text |
| `text` | - | C1-text, L25 |
| `infographic` | 1 | C4-infographic |
| `infographic` + `with_analysis` | 1 | V4-infographic-text |
| `image` | - | I1-image-left, I2-image-right |
| `comparison` | - | S4-comparison |

---

## 5. POST /api/can-fit

Validate if content can fit in the specified layout.

### Request Body

```json
{
  "layout_id": "S3-two-visuals",
  "content_zones_needed": 2,
  "content_type": "chart"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `layout_id` | string | Yes | Layout ID to check |
| `content_zones_needed` | int | No | Number of zones required (1-10), default: 1 |
| `content_type` | string | Yes | `text`, `chart`, `diagram`, `image`, `body`, `html`, etc. |

### Response

```json
{
  "can_fit": true,
  "layout_id": "S3-two-visuals",
  "content_zones_available": 2,
  "content_zones_needed": 2,
  "suggested_layout": null,
  "reason": "Layout 'S3-two-visuals' has 2 zone(s) accepting 'chart', need 2"
}
```

### When Content Doesn't Fit

```json
{
  "can_fit": false,
  "layout_id": "C1-text",
  "content_zones_available": 0,
  "content_zones_needed": 2,
  "suggested_layout": "S3-two-visuals",
  "reason": "Layout 'C1-text' has 0 zone(s) accepting 'chart', need 2"
}
```

---

## 6. X-Series Dynamic Layouts (NEW v7.5.7)

X-series layouts dynamically split base template content areas into sub-zones.

### X-Series Mapping

| X-Series | Base Template | Content Area |
|----------|---------------|--------------|
| X1 | C1-text | 1800×840px |
| X2 | I1-image-left | 1200×840px |
| X3 | I2-image-right | 1140×840px |
| X4 | I3-image-left-narrow | 1500×840px |
| X5 | I4-image-right-narrow | 1440×840px |

### GET /api/dynamic-layouts/patterns

List available split patterns.

**Response:**
```json
{
  "patterns": {
    "agenda-3-item": {"zones": 3, "direction": "horizontal", "description": "3 rows for agenda"},
    "comparison-2col": {"zones": 2, "direction": "vertical", "description": "Left/right comparison"},
    "grid-2x2": {"zones": 4, "direction": "grid", "description": "2×2 balanced grid"}
  }
}
```

### POST /api/dynamic-layouts/generate

Generate a new dynamic layout.

**Request:**
```json
{
  "base_layout": "C1-text",
  "content_type": "agenda",
  "split_pattern": "agenda-3-item"
}
```

**Response:**
```json
{
  "layout_id": "X1-84d76fe0",
  "base_layout": "C1-text",
  "name": "Agenda Layout (3 zones)",
  "zones": [
    {
      "zone_id": "zone_1",
      "grid_row": "4/8",
      "grid_column": "2/32",
      "pixels": {"x": 60, "y": 180, "width": 1800, "height": 240}
    },
    {
      "zone_id": "zone_2",
      "grid_row": "8/13",
      "grid_column": "2/32",
      "pixels": {"x": 60, "y": 420, "width": 1800, "height": 300}
    },
    {
      "zone_id": "zone_3",
      "grid_row": "13/18",
      "grid_column": "2/32",
      "pixels": {"x": 60, "y": 720, "width": 1800, "height": 300}
    }
  ]
}
```

### GET /api/dynamic-layouts/{layout_id}

Get details of a dynamic layout.

### GET /api/dynamic-layouts

List all dynamic layouts.

---

## Template Inventory

### Hero Series (H)

| ID | Name | Use Case |
|----|------|----------|
| H1-generated | Title Slide (AI Generated) | Full-bleed AI-generated hero |
| H1-structured | Title Slide (Manual) | Editable title, subtitle, author |
| H2-section | Section Divider | Chapter/section breaks |
| H3-closing | Closing Slide | Thank you, contact info |

### Content Series (C)

| ID | Name | Use Case |
|----|------|----------|
| C1-text | Text Content | Paragraphs, bullets |
| C3-chart | Single Chart | Full-width chart |
| C4-infographic | Single Infographic | Full-width infographic |
| C5-diagram | Single Diagram | Full-width diagram |

### Visual + Text Series (V)

| ID | Name | Use Case |
|----|------|----------|
| V1-image-text | Image + Text | Image left, insights right |
| V2-chart-text | Chart + Text | Chart left, insights right |
| V3-diagram-text | Diagram + Text | Diagram left, insights right |
| V4-infographic-text | Infographic + Text | Infographic left, insights right |

### Image Split Series (I)

| ID | Name | Use Case |
|----|------|----------|
| I1-image-left | Image Left (Wide) | Full-height image left (12 cols) |
| I2-image-right | Image Right (Wide) | Full-height image right (12 cols) |
| I3-image-left-narrow | Image Left (Narrow) | Narrow image left (6 cols) |
| I4-image-right-narrow | Image Right (Narrow) | Narrow image right (6 cols) |

### Split Series (S)

| ID | Name | Use Case |
|----|------|----------|
| S3-two-visuals | Two Visuals | Side-by-side charts/diagrams |
| S4-comparison | Comparison | Before/after, pros/cons |

### Backend Series (L)

| ID | Name | Main Content Dimensions | Format Owner |
|----|------|------------------------|--------------|
| L02 | Left Diagram + Right Text | 1260 x 720 px + 540 x 720 px | analytics_service |
| L25 | Main Content Shell | 1800 x 720 px | text_service |
| L29 | Hero Full-Bleed | 1920 x 1080 px | text_service |

> **Note**: L01, L03, and L27 have been decommissioned. Use frontend templates (C3-chart, S3-two-visuals, I1-image-left) for equivalent functionality.

---

## Grid System Reference

The Layout Service uses a **32 x 18 grid** on **1920 x 1080** slide resolution.

- **Column width**: 60 px (1920 / 32)
- **Row height**: 60 px (1080 / 18)
- **Grid notation**: `"start/end"` format (1-indexed)

### Example: Grid to Pixels

```
grid_row: "5/17"    → y: 240px, height: 720px
grid_column: "2/32" → x: 60px, width: 1800px
```

---

## Integration Example

### Director Workflow

```python
# 1. Get layout recommendation
response = requests.post(
    "http://localhost:8504/api/recommend-layout",
    json={
        "content_type": "chart",
        "topic_count": 1,
        "variant": "with_analysis",
        "service": "director"
    }
)
recommendation = response.json()
layout_id = recommendation["recommended_layouts"][0]["layout_id"]  # "V2-chart-text"

# 2. Get exact slot dimensions
layout_details = requests.get(f"http://localhost:8504/api/layouts/{layout_id}").json()

# 3. Extract content zone dimensions for Text Service / Analytics Service
chart_slot = layout_details["slots"]["content_left"]
chart_dimensions = chart_slot["pixels"]  # {"x": 60, "y": 180, "width": 1080, "height": 840}

text_slot = layout_details["slots"]["content_right"]
text_dimensions = text_slot["pixels"]  # {"x": 1140, "y": 180, "width": 720, "height": 840}

# 4. Pass dimensions to content services
analytics_service.generate_chart(
    width=chart_dimensions["width"],
    height=chart_dimensions["height"]
)
text_service.generate_insights(
    max_width=text_dimensions["width"],
    max_height=text_dimensions["height"]
)
```

---

## Error Handling

### 404 - Layout Not Found

```json
{
  "detail": "Layout 'INVALID' not found. Valid layouts: ['H1-generated', 'H1-structured', ...]"
}
```

### 422 - Validation Error

```json
{
  "detail": [
    {
      "loc": ["body", "content_type"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Changelog

### v7.5.7 (December 2024)
- Added X-series dynamic layout system (X1-X5)
- 5 base layouts: X1 (C1-text), X2 (I1), X3 (I2), X4 (I3), X5 (I4)
- 10 preconfigured split patterns (agenda, comparison, grid)
- Dynamic zone generation with pixel dimensions
- Theme typography moved to separate `THEME_SERVICE_CAPABILITIES.md`

### v7.5.6 (December 2024)
- Decommissioned L01, L03, L27 backend layouts
- Reduced template count from 25 to 22
- Updated recommendations to use frontend templates for charts/images

### v7.5.5 (December 2024)
- Added 5 Director coordination endpoints
- Created unified template registry (25 templates)
- Exposed grid-to-pixel conversion for all slots
- Added layout recommendation engine
- Added can-fit validation endpoint

---

## Related Documents

| Document | Description |
|----------|-------------|
| `layout_builder_main/v7.5-main/docs/THEME_SERVICE_CAPABILITIES.md` | Theme typography, CSS variables, custom themes |
| [TEXT_SERVICE_CAPABILITIES.md](./TEXT_SERVICE_CAPABILITIES.md) | Text generation and formatting |
| [DIAGRAM_SERVICE_CAPABILITIES.md](./DIAGRAM_SERVICE_CAPABILITIES.md) | Diagram types and generation |
| [ANALYTICS_SERVICE_CAPABILITIES.md](./ANALYTICS_SERVICE_CAPABILITIES.md) | Charts and data visualization |
