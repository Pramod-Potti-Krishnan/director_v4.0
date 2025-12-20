# Analytics Service API Reference

**Version**: 3.1.5
**Base URL**: `http://localhost:8080` (local) | `https://analytics-v30-production.up.railway.app` (Production)
**Last Updated**: December 2024 (Added response_format field aliases)

---

## Overview

The Analytics Service (v3.0) provides comprehensive chart generation and data visualization.

| Category | Endpoints | Purpose |
|----------|-----------|---------|
| **Service Coordination** | 3 | Director discovery, routing, recommendations |
| **Chart Discovery** | 4 | Chart catalog, type details, layout compatibility |
| **Analytics Generation** | 2 | Single and batch chart generation |
| **Synthetic Data** | 2 | Auto-generate realistic chart data |
| **Interactive Editor** | 2 | Real-time chart data editing |
| **Layout Service** | 3 | Grid-based chart generation |
| **Health & Monitoring** | 2 | Service health and stats |

**Total**: 18 endpoints, 20+ chart types

---

# PART 1: SERVICE COORDINATION ENDPOINTS

Director Agent coordination endpoints for Strawman Service integration (Phase 1-3).

---

## 1.1 GET /capabilities

**Purpose**: Service discovery - what can this service do?

### Response Schema

```json
{
  "service": "analytics-service",
  "version": "3.1.0",
  "status": "healthy",

  "capabilities": {
    "slide_types": ["chart", "visualization", "data_display"],
    "chart_types": [
      "line", "bar_vertical", "bar_horizontal", "pie", "doughnut",
      "scatter", "bubble", "radar", "polar_area", "area", "area_stacked",
      "bar_grouped", "bar_stacked", "waterfall",
      "d3_treemap", "d3_sunburst", "d3_choropleth_usa", "d3_sankey"
    ],
    "supported_layouts": ["L01", "L02", "L03"],
    "supports_themes": true,
    "can_generate_data": true,
    "chart_libraries": ["Chart.js", "D3.js"]
  },

  "response_format": {
    "content_fields": {
      "element_3": "Chart HTML (original field)",
      "element_2": "Observations/insights HTML (original field)",
      "chart_html": "Alias for element_3 (for C3-chart, V2-chart-text)",
      "element_4": "Alias for element_3 (for L02 SPEC compliance)",
      "body": "Alias for element_2 (for V2-chart-text)"
    },
    "field_mapping_guide": {
      "C3-chart": {"chart_html": "element_3"},
      "V2-chart-text": {"chart_html": "element_3", "body": "element_2"},
      "L02": {"element_4": "element_3", "element_2": "element_2"}
    },
    "note": "Director can use aliases directly without mapping. Original fields kept for backward compatibility."
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
      "growth", "decline", "revenue", "sales", "distribution",
      "metrics", "KPI", "data", "numbers", "statistics"
    ],
    "pattern_detection": {
      "time_series": ["over time", "by quarter", "by month", "trend", "growth", "quarterly", "monthly", "yearly"],
      "comparison": ["vs", "compared to", "difference between", "versus", "compare"],
      "composition": ["breakdown", "distribution", "share of", "percentage", "proportion", "parts of"]
    }
  },

  "chart_recommendations": {
    "time_series": ["line", "area"],
    "comparison": ["bar_vertical", "bar_horizontal", "bar_grouped"],
    "composition": ["pie", "doughnut", "d3_treemap"],
    "correlation": ["scatter", "bubble"],
    "hierarchy": ["d3_treemap", "d3_sunburst"],
    "flow": ["d3_sankey"],
    "geographic": ["d3_choropleth_usa"]
  },

  "endpoints": {
    "capabilities": "GET /capabilities",
    "generate": "POST /api/v1/analytics/{layout}/{analytics_type}",
    "can_handle": "POST /api/v1/analytics/can-handle",
    "recommend_chart": "POST /api/v1/analytics/recommend-chart",
    "chart_types": "GET /api/v1/chart-types",
    "synthetic_data": "POST /api/v1/synthetic/generate"
  }
}
```

---

## 1.2 POST /api/v1/analytics/can-handle

**Purpose**: Content negotiation - can service handle this content?

### Request Schema

```json
{
  "slide_content": {
    "title": "Q4 Revenue Analysis",           // Required: string
    "topics": [                                // Required: string[]
      "Revenue grew 15%",
      "New markets contributed 30%",
      "Cost reduction achieved"
    ],
    "topic_count": 3                           // Required: int
  },
  "content_hints": {
    "has_numbers": true,                       // boolean - numerical data present
    "is_comparison": false,                    // boolean - comparing items
    "is_time_based": true,                     // boolean - time series data
    "detected_keywords": ["revenue", "growth", "percentage"]  // string[]
  },
  "available_space": {                         // Optional: layout constraints
    "width": 1800,                             // int - pixels
    "height": 750                              // int - pixels
  }
}
```

### Response Schema

```json
{
  "can_handle": true,
  "confidence": 0.95,
  "reason": "contains numerical data | time series detected | keywords matched: ['revenue', 'growth'] | 2 topics with numbers/percentages | title suggests data visualization",
  "suggested_approach": "chart",
  "space_utilization": {
    "fits_well": true,
    "estimated_fill_percent": 85
  }
}
```

### Confidence Score Guidelines

| Score | Meaning | Director Action |
|-------|---------|-----------------|
| 0.90+ | Excellent fit - strong chart signals | Use Analytics Service |
| 0.70-0.89 | Good fit - numerical/visual data | Use Analytics Service |
| 0.40-0.69 | Acceptable - some chart indicators | Consider alternatives |
| < 0.40 | Poor fit - likely text content | Route to Text Service |

### Confidence Scoring Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| `has_numbers` | +0.30 | Content contains numerical data |
| `is_time_based` | +0.25 | Time series or trend data |
| `is_comparison` | +0.20 | Comparative data |
| Keyword matches | +0.08 each (max 0.25) | Chart-related keywords detected |
| Numeric topics | +0.07 each (max 0.20) | Topics with numbers/percentages |
| Title signals | +0.10 | Title suggests data visualization |

---

## 1.3 POST /api/v1/analytics/recommend-chart

**Purpose**: Get ranked chart type recommendations for the content.

### Request Schema

```json
{
  "slide_content": {
    "title": "Revenue Trend",                  // Required: string
    "topics": ["Show revenue growth over 4 quarters"],  // Required: string[]
    "topic_count": 1                           // Required: int
  },
  "detected_patterns": ["time_series"]         // Optional: string[] - pattern hints
}
```

### Response Schema

```json
{
  "recommended_charts": [
    {
      "chart_type": "line",
      "confidence": 0.95,
      "reason": "Time series data best shown as line chart"
    },
    {
      "chart_type": "area",
      "confidence": 0.80,
      "reason": "Area chart also effective for trends over time"
    }
  ]
}
```

### Supported Patterns

| Pattern | Recommended Charts | Keywords Detected |
|---------|-------------------|-------------------|
| `time_series` | line, area | trend, over time, growth, monthly, quarterly, yearly |
| `comparison` | bar_vertical, bar_horizontal, bar_grouped | vs, compared to, versus, difference |
| `composition` | pie, doughnut, d3_treemap | share, percentage, breakdown, distribution |
| `correlation` | scatter, bubble | correlation, relationship, vs (numeric) |
| `hierarchy` | d3_treemap, d3_sunburst | hierarchy, levels, categories, nested |
| `flow` | d3_sankey | flow, process, pipeline, stages |
| `geographic` | d3_choropleth_usa | map, state, region, geographic |
| `distribution` | bar_vertical, pie | distribution, spread, range |

---

# PART 2: CHART DISCOVERY ENDPOINTS

Discover available chart types, constraints, and compatibility.

---

## 2.1 GET /api/v1/chart-types

**Purpose**: Get complete chart type catalog.

### Response Schema

```json
{
  "success": true,
  "summary": {
    "total": 18,
    "chartjs_count": 14,
    "d3_count": 4,
    "layouts": ["L01", "L02", "L03"]
  },
  "chart_types": [
    {
      "id": "line",
      "name": "Line Chart",
      "library": "Chart.js",
      "description": "Shows trends over time or continuous data",
      "use_cases": ["time series", "trends", "progress"],
      "min_data_points": 2,
      "max_data_points": 50,
      "supported_layouts": ["L01", "L02", "L03"],
      "data_format": "simple"
    }
    // ... 17 more chart types
  ]
}
```

---

## 2.2 GET /api/v1/chart-types/chartjs

**Purpose**: Get Chart.js chart types (L02 layout compatible).

### Response Schema

```json
{
  "success": true,
  "library": "Chart.js",
  "layouts": ["L02"],
  "count": 14,
  "chart_types": [
    // 14 Chart.js chart types
  ]
}
```

---

## 2.3 GET /api/v1/chart-types/{chart_id}

**Purpose**: Get detailed information about a specific chart type.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `chart_id` | string | Chart type ID (e.g., 'line', 'bar_vertical', 'd3_sankey') |

### Response Schema

```json
{
  "success": true,
  "chart_type": {
    "id": "bar_vertical",
    "name": "Vertical Bar Chart",
    "library": "Chart.js",
    "description": "Compares values across categories",
    "use_cases": ["category comparison", "ranking", "distribution"],
    "min_data_points": 2,
    "max_data_points": 20,
    "supported_layouts": ["L01", "L02", "L03"],
    "data_format": "simple",
    "example_data": [
      {"label": "Category A", "value": 100},
      {"label": "Category B", "value": 150}
    ]
  }
}
```

---

## 2.4 GET /api/v1/layouts/{layout}/chart-types

**Purpose**: Get chart types compatible with a specific layout.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `layout` | string | Layout type: L01, L02, or L03 |

### Response Schema

```json
{
  "success": true,
  "layout": "L02",
  "library": "Chart.js",
  "count": 14,
  "chart_types": [
    // Chart types compatible with L02
  ]
}
```

---

# PART 3: ANALYTICS GENERATION ENDPOINTS

Generate analytics slides with charts and insights (Director integration).

---

## 3.1 POST /api/v1/analytics/{layout}/{analytics_type}

**Purpose**: Generate analytics slide content (Text Service compatible).

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `layout` | string | Layout type: L01, L02, or L03 |
| `analytics_type` | string | Analytics visualization type |

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_synthetic` | boolean | false | Generate synthetic data if true |

### Request Schema

```json
{
  "presentation_id": "pres-123",               // Required: string, min 1 char
  "slide_id": "slide-7",                       // Required: string, min 1 char
  "slide_number": 7,                           // Required: int >= 1
  "narrative": "Show quarterly revenue growth highlighting strong Q3-Q4 performance",  // Required: string, 1-2000 chars
  "data": [                                    // Optional: 1-50 data points
    {"label": "Q1 2024", "value": 125000},
    {"label": "Q2 2024", "value": 145000},
    {"label": "Q3 2024", "value": 162000},
    {"label": "Q4 2024", "value": 178000}
  ],
  "context": {                                 // Optional: presentation context
    "theme": "professional",
    "audience": "Board of Directors",
    "slide_title": "Quarterly Revenue Growth",
    "subtitle": "FY 2024 Performance"
  },
  "constraints": {},                           // Optional: layout constraints
  "chart_type": "line"                         // Optional: chart type override
}
```

### Response Schema (L02 Layout)

```json
{
  "content": {
    "element_3": "<canvas id='chart_abc123'>...</canvas><script>new Chart(...)</script>",
    "element_2": "<div class='insights'><ul><li>Revenue grew 42% from Q1 to Q4</li><li>Strong acceleration in H2</li></ul></div>"
  },
  "metadata": {
    "service": "analytics_v3",
    "chart_type": "line",
    "layout": "L02",
    "data_source": "director",
    "synthetic_data_used": false,
    "data_points": 4,
    "generation_time_ms": 1250
  }
}
```

### Analytics Types

| Type | Description | Recommended Chart |
|------|-------------|-------------------|
| `revenue_over_time` | Revenue trends | line, area |
| `market_share` | Market composition | pie, doughnut |
| `performance_comparison` | Performance metrics | bar_vertical, bar_grouped |
| `geographic_distribution` | Regional data | d3_choropleth_usa |
| `hierarchy_breakdown` | Hierarchical data | d3_treemap, d3_sunburst |
| `process_flow` | Flow diagrams | d3_sankey |

---

## 3.2 POST /api/v1/analytics/batch

**Purpose**: Generate multiple analytics slides in batch (parallel processing).

### Request Schema

```json
{
  "presentation_id": "pres-123",
  "slides": [
    {
      "slide_id": "slide-3",
      "slide_number": 3,
      "analytics_type": "revenue_over_time",
      "layout": "L02",
      "narrative": "Q1-Q4 revenue growth",
      "data": [...]
    },
    {
      "slide_id": "slide-5",
      "slide_number": 5,
      "analytics_type": "market_share",
      "layout": "L02",
      "narrative": "Market share by segment",
      "data": [...]
    }
  ]
}
```

### Response Schema

```json
{
  "presentation_id": "pres-123",
  "slides": [
    {
      "success": true,
      "slide_id": "slide-3",
      "content": {...},
      "metadata": {...}
    },
    {
      "success": true,
      "slide_id": "slide-5",
      "content": {...},
      "metadata": {...}
    }
  ],
  "total": 2,
  "successful": 2
}
```

---

# PART 4: SYNTHETIC DATA GENERATION ENDPOINTS

Auto-generate realistic chart data for testing and previews.

---

## 4.1 POST /api/v1/synthetic/generate

**Purpose**: Generate synthetic data for any chart type.

### Request Schema

```json
{
  "chart_type": "line",                        // Required: valid chart type ID
  "narrative": "Show quarterly revenue growth for SaaS company",  // Optional: context
  "num_points": 8,                             // Optional: 1-50 data points
  "scenario": "revenue_growth"                 // Optional: business scenario
}
```

### Response Schema

```json
{
  "success": true,
  "data": [
    {"label": "Q1 2024", "value": 125000},
    {"label": "Q2 2024", "value": 145000},
    {"label": "Q3 2024", "value": 162000},
    {"label": "Q4 2024", "value": 178000},
    {"label": "Q1 2025", "value": 195000},
    {"label": "Q2 2025", "value": 215000},
    {"label": "Q3 2025", "value": 238000},
    {"label": "Q4 2025", "value": 265000}
  ],
  "metadata": {
    "chart_type": "line",
    "num_points": 8,
    "scenario": "revenue_growth",
    "generated_at": "2024-12-19T10:30:00Z"
  }
}
```

### Supported Scenarios

| Scenario | Description | Data Pattern |
|----------|-------------|--------------|
| `revenue_growth` | Growing revenue | Upward trend with variation |
| `seasonal_sales` | Seasonal patterns | Peaks in Q4, dips in Q1 |
| `market_comparison` | Competitive analysis | Multiple categories |
| `geographic_sales` | State-level data | 50 US states |
| `process_flow` | Pipeline stages | Funnel-like values |

---

## 4.2 POST /api/v1/preview/{chart_type}

**Purpose**: Generate preview slide for a chart type using synthetic data.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `chart_type` | string | Chart type ID to preview |

### Request Schema

```json
{
  "narrative": "Show sales by top 10 states",  // Optional: context for data
  "num_points": 10                             // Optional: data point count
}
```

### Response Schema

```json
{
  "content": {
    "element_3": "<canvas>...</canvas><script>...</script>",
    "element_2": "<div class='insights'>...</div>"
  },
  "metadata": {
    "chart_type": "d3_choropleth_usa",
    "slide_number": 1,
    "synthetic_data_used": true,
    "preview_mode": true,
    "generation_time_ms": 2100
  }
}
```

---

# PART 5: INTERACTIVE EDITOR ENDPOINTS

Edit chart data interactively (L02 charts).

---

## 5.1 POST /api/charts/update-data

**Purpose**: Save edited chart data.

### Request Schema - Simple Charts

```json
{
  "chart_id": "chart_abc123",                  // Required: chart identifier
  "presentation_id": "pres-123",               // Required: presentation UUID
  "chart_type": "bar_vertical",                // Required: chart type
  "labels": ["Q1", "Q2", "Q3", "Q4"],          // Required: 2-50 labels
  "values": [100, 150, 200, 175],              // Required: matching values
  "timestamp": "2024-12-19T10:30:00Z"          // Optional
}
```

### Request Schema - Multi-Series Charts

```json
{
  "chart_id": "chart_abc123",
  "presentation_id": "pres-123",
  "chart_type": "bar_grouped",
  "labels": ["Q1", "Q2", "Q3", "Q4"],
  "datasets": [
    {
      "label": "Product A",
      "data": [100, 120, 140, 160]
    },
    {
      "label": "Product B",
      "data": [80, 95, 110, 125]
    }
  ]
}
```

### Request Schema - Scatter/Bubble Charts

```json
{
  "chart_id": "chart_abc123",
  "presentation_id": "pres-123",
  "chart_type": "bubble",
  "data": [
    {"x": 10, "y": 20, "r": 15, "label": "Product A"},
    {"x": 25, "y": 35, "r": 25, "label": "Product B"},
    {"x": 40, "y": 15, "r": 10, "label": "Product C"}
  ]
}
```

### Response Schema

```json
{
  "success": true,
  "message": "Chart data updated successfully (single-series)",
  "chart_id": "chart_abc123",
  "presentation_id": "pres-123",
  "format": "single-series",
  "chart_type": "bar_vertical",
  "labels_count": 4,
  "values_count": 4
}
```

---

## 5.2 GET /api/charts/get-data/{presentation_id}

**Purpose**: Get all saved chart data for a presentation.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `presentation_id` | string | Presentation UUID |

### Response Schema

```json
{
  "success": true,
  "presentation_id": "pres-123",
  "charts": [
    {
      "chart_id": "chart_abc123",
      "chart_type": "bar_vertical",
      "labels": ["Q1", "Q2", "Q3", "Q4"],
      "values": [100, 150, 200, 175],
      "updated_at": "2024-12-19T10:30:00Z"
    }
  ]
}
```

---

# PART 6: LAYOUT SERVICE INTEGRATION ENDPOINTS

Chart generation for Layout Service with grid-based sizing constraints.

---

## 6.1 POST /api/ai/chart/generate

**Purpose**: Generate chart for Layout Service with grid constraints.

### Request Schema

```json
{
  "prompt": "Show quarterly revenue growth",   // Required: chart description
  "chartType": "bar",                          // Required: bar|line|pie|doughnut|area|scatter|radar|polarArea
  "presentationId": "pres-123",                // Required
  "slideId": "slide-7",                        // Required
  "elementId": "chart-1",                      // Required
  "context": {
    "presentationTitle": "Q4 Review",
    "slideTitle": "Revenue Analysis",
    "slideIndex": 6
  },
  "constraints": {
    "gridWidth": 8,                            // Required: 1-12 grid units
    "gridHeight": 4                            // Required: 1-8 grid units
  },
  "style": {
    "palette": "professional",                 // default|professional|vibrant|pastel|dark
    "showLegend": true,
    "legendPosition": "top",                   // top|bottom|left|right
    "showGrid": true,
    "showDataLabels": false,
    "customColors": null                       // Optional: hex color array
  },
  "axes": {
    "xLabel": "Quarter",
    "yLabel": "Revenue ($)",
    "yMin": 0,
    "yMax": null,
    "stacked": false
  },
  "config": {
    "animated": true,
    "aspectRatio": null
  },
  "data": [
    {"label": "Q1", "value": 125000},
    {"label": "Q2", "value": 145000}
  ],
  "generateData": false                        // If true, generates synthetic data
}
```

### Response Schema

```json
{
  "success": true,
  "data": {
    "generationId": "gen-uuid-123",
    "chartConfig": {
      "type": "bar",
      "data": {
        "labels": ["Q1", "Q2"],
        "datasets": [{
          "label": "Revenue Analysis",
          "data": [125000, 145000],
          "backgroundColor": ["#3b82f6", "#10b981"],
          "borderColor": ["#3b82f6", "#10b981"],
          "borderWidth": 2
        }]
      },
      "options": {
        "responsive": true,
        "maintainAspectRatio": false,
        "plugins": {
          "legend": {"display": true, "position": "top"},
          "tooltip": {"enabled": true}
        },
        "scales": {
          "x": {"display": true, "grid": {"display": true}},
          "y": {"display": true, "beginAtZero": true}
        }
      }
    },
    "rawData": {
      "labels": ["Q1", "Q2"],
      "datasets": [{
        "label": "Revenue Analysis",
        "data": [125000, 145000],
        "backgroundColor": ["#3b82f6", "#10b981"],
        "borderColor": ["#3b82f6", "#10b981"]
      }]
    },
    "metadata": {
      "chartType": "bar",
      "dataPointCount": 2,
      "datasetCount": 1,
      "suggestedTitle": "Quarterly Revenue",
      "dataRange": {
        "min": 125000,
        "max": 145000,
        "average": 135000
      }
    },
    "insights": {
      "trend": "increasing",
      "outliers": null,
      "highlights": ["16.0% growth over the period"]
    }
  }
}
```

### Grid Constraints

| Grid Area | Classification | Max Data Points |
|-----------|----------------|-----------------|
| ≤ 16 | Small | 6-8 |
| 17-48 | Medium | 10-15 |
| > 48 | Large | 20-50 |

### Minimum Grid Sizes by Chart Type

| Chart Type | Min Width | Min Height |
|------------|-----------|------------|
| bar | 3 | 2 |
| line | 3 | 2 |
| pie | 3 | 3 |
| doughnut | 3 | 3 |
| radar | 4 | 4 |
| polarArea | 4 | 4 |
| scatter | 4 | 3 |
| area | 3 | 2 |

---

## 6.2 GET /api/ai/chart/constraints

**Purpose**: Get grid constraints for all chart types.

### Response Schema

```json
{
  "success": true,
  "minimumGridSizes": {
    "bar": {"width": 3, "height": 2},
    "line": {"width": 3, "height": 2},
    "pie": {"width": 3, "height": 3},
    "doughnut": {"width": 3, "height": 3},
    "radar": {"width": 4, "height": 4},
    "polarArea": {"width": 4, "height": 4},
    "scatter": {"width": 4, "height": 3},
    "area": {"width": 3, "height": 2}
  },
  "dataLimits": {
    "small": {"maxPoints": 8, "maxSeries": 3},
    "medium": {"maxPoints": 15, "maxSeries": 5},
    "large": {"maxPoints": 50, "maxSeries": 10}
  },
  "gridRanges": {
    "width": {"min": 1, "max": 12},
    "height": {"min": 1, "max": 8}
  },
  "sizeThresholds": {
    "small": "area <= 16",
    "medium": "16 < area <= 48",
    "large": "area > 48"
  }
}
```

---

## 6.3 GET /api/ai/chart/palettes

**Purpose**: Get available color palettes for chart generation.

### Response Schema

```json
{
  "success": true,
  "palettes": [
    {
      "name": "default",
      "colors": ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"],
      "internalTheme": "professional",
      "colorCount": 5
    },
    {
      "name": "professional",
      "colors": ["#1e40af", "#059669", "#d97706", "#dc2626", "#7c3aed"],
      "internalTheme": "professional",
      "colorCount": 5
    },
    {
      "name": "vibrant",
      "colors": ["#06b6d4", "#22c55e", "#eab308", "#f43f5e", "#a855f7"],
      "internalTheme": "vibrant",
      "colorCount": 5
    }
  ],
  "defaultPalette": "default"
}
```

---

# PART 7: HEALTH & MONITORING ENDPOINTS

Service health checks and statistics.

---

## 7.1 GET /health

**Purpose**: Health check endpoint.

### Response Schema

```json
{
  "status": "healthy",
  "service": "analytics_microservice_v3",
  "jobs": {
    "active": 2,
    "completed": 145,
    "failed": 3
  }
}
```

---

## 7.2 GET /stats

**Purpose**: Get job statistics.

### Response Schema

```json
{
  "job_stats": {
    "active": 2,
    "completed": 145,
    "failed": 3,
    "average_time_ms": 1850
  },
  "storage_bucket": "analytics-charts"
}
```

---

# APPENDIX A: Chart Type Inventory (20 Total)

## Chart.js Types (14)

### Basic Charts

| Chart Type | ID | Data Points | Best For |
|------------|-----|-------------|----------|
| Line Chart | `line` | 2-50 | Time series, trends |
| Vertical Bar | `bar_vertical` | 2-20 | Category comparison |
| Horizontal Bar | `bar_horizontal` | 2-20 | Long labels, ranking |
| Pie Chart | `pie` | 2-8 | Parts of whole |
| Doughnut Chart | `doughnut` | 2-8 | Composition (clean) |
| Scatter Plot | `scatter` | 5-100 | Correlation |
| Bubble Chart | `bubble` | 5-50 | 3-variable correlation |
| Radar Chart | `radar` | 3-10 | Multi-metric comparison |
| Polar Area | `polar_area` | 3-8 | Cyclical data |

### Advanced Charts

| Chart Type | ID | Data Points | Best For |
|------------|-----|-------------|----------|
| Area Chart | `area` | 2-50 | Cumulative trends |
| Stacked Area | `area_stacked` | 2-50 | Composition over time |
| Grouped Bar | `bar_grouped` | 2-20 | Multi-series comparison |
| Stacked Bar | `bar_stacked` | 2-20 | Part-to-whole by category |
| Waterfall | `waterfall` | 3-15 | Cumulative effect |

## D3.js Types (4)

| Chart Type | ID | Data Points | Best For |
|------------|-----|-------------|----------|
| Treemap | `d3_treemap` | 3-50 | Hierarchical composition |
| Sunburst | `d3_sunburst` | 3-100 | Nested hierarchies |
| Choropleth USA | `d3_choropleth_usa` | 1-51 | US state data |
| Sankey Diagram | `d3_sankey` | 3-30 | Flow/process visualization |

## Plugin-Based Charts (2)

| Chart Type | ID | Data Points | Best For |
|------------|-----|-------------|----------|
| Treemap (Chart.js) | `treemap` | 3-50 | Hierarchical data |
| Boxplot | `boxplot` | 5-20 | Statistical distribution |

---

# APPENDIX B: Data Format Reference

## Simple Data (Most Chart Types)

```json
{
  "data": [
    {"label": "Category A", "value": 100},
    {"label": "Category B", "value": 150},
    {"label": "Category C", "value": 200}
  ]
}
```

## Multi-Series Data (Grouped/Stacked Charts)

```json
{
  "data": [
    {"label": "Q1", "series1": 100, "series2": 80},
    {"label": "Q2", "series1": 150, "series2": 120},
    {"label": "Q3", "series1": 200, "series2": 160}
  ]
}
```

## Bubble Chart Data

```json
{
  "data": [
    {"x": 10, "y": 20, "r": 15, "label": "Product A"},
    {"x": 25, "y": 35, "r": 25, "label": "Product B"}
  ]
}
```

## Sankey Diagram Data

```json
{
  "data": {
    "nodes": ["Source A", "Source B", "Target X", "Target Y"],
    "links": [
      {"source": 0, "target": 2, "value": 100},
      {"source": 1, "target": 3, "value": 80}
    ]
  }
}
```

## Choropleth Map Data

```json
{
  "data": [
    {"state": "CA", "value": 39500000},
    {"state": "TX", "value": 29000000},
    {"state": "FL", "value": 21500000}
  ]
}
```

---

# APPENDIX C: Error Responses

All endpoints return errors in this format:

```json
{
  "code": "INVALID_DATA_POINTS",
  "message": "At least 2 data points required",
  "category": "validation",
  "details": {
    "provided": 1,
    "minimum": 2
  },
  "suggestion": "Provide at least 2 data points or use use_synthetic=true",
  "retryable": true,
  "http_status": 400
}
```

### Error Codes

| Code | Category | HTTP Status | Description |
|------|----------|-------------|-------------|
| `INVALID_DATA_POINTS` | validation | 400 | Data point count out of range |
| `INVALID_CHART_TYPE` | validation | 400 | Unsupported chart type |
| `INVALID_LAYOUT` | validation | 400 | Invalid layout (not L01/L02/L03) |
| `INVALID_ANALYTICS_TYPE` | validation | 400 | Unsupported analytics type |
| `INVALID_GRID_SIZE` | validation | 400 | Grid too small for chart type |
| `MISSING_DATA` | validation | 400 | No data provided and generateData=false |
| `CHART_GENERATION_FAILED` | processing | 500 | Chart rendering failed |
| `JOB_NOT_FOUND` | resource | 404 | Job ID not found |

---

# APPENDIX D: Layout Compatibility

## L02 Layout (Primary - Chart with Insights)

**Dimensions**: 1260×720px (chart) + 540×720px (insights)
**Library**: Chart.js

| Features | Status |
|----------|--------|
| All Chart.js types | ✅ Full support |
| Interactive editing | ✅ Enabled |
| AI-generated insights | ✅ Included |
| Synthetic data | ✅ Available |

## L01 Layout (Centered Chart)

**Dimensions**: 1800×600px
**Library**: ApexCharts

| Features | Status |
|----------|--------|
| Basic chart types | ✅ Supported |
| Interactive editing | ❌ Not available |

## L03 Layout (Side-by-Side Comparison)

**Dimensions**: 2× 840×540px
**Library**: ApexCharts

| Features | Status |
|----------|--------|
| Comparison charts | ✅ Supported |
| Dual chart rendering | ✅ Available |

---

# APPENDIX E: Quick Reference

## Recommended Endpoints by Use Case

| Use Case | Recommended Endpoint |
|----------|---------------------|
| Service discovery | `GET /capabilities` |
| Content routing | `POST /api/v1/analytics/can-handle` |
| Chart recommendation | `POST /api/v1/analytics/recommend-chart` |
| Single chart generation | `POST /api/v1/analytics/{layout}/{type}` |
| Batch generation | `POST /api/v1/analytics/batch` |
| Preview chart type | `POST /api/v1/preview/{chart_type}` |
| Generate test data | `POST /api/v1/synthetic/generate` |
| Layout Service charts | `POST /api/ai/chart/generate` |

## Content Routing Signals

| Signal | Analytics Confidence | Text Confidence |
|--------|---------------------|-----------------|
| "Show revenue trend over time" | 0.95 | 0.20 |
| "Compare Q1 vs Q2 sales" | 0.85 | 0.40 |
| "Market share breakdown" | 0.90 | 0.30 |
| "Three key features" | 0.15 | 0.90 |
| "Step-by-step process" | 0.10 | 0.95 |

---

# APPENDIX F: Integration Example

```python
import requests

BASE_URL = "https://analytics-v30-production.up.railway.app"

# 1. Director gets content from storyline
content = {
    "title": "Quarterly Revenue Trend",
    "topics": ["Show revenue growth from Q1 to Q4 2024"],
    "topic_count": 1
}

# 2. Ask Analytics Service if it can handle this content
can_handle_response = requests.post(
    f"{BASE_URL}/api/v1/analytics/can-handle",
    json={
        "slide_content": content,
        "content_hints": {
            "has_numbers": True,
            "is_comparison": False,
            "is_time_based": True,
            "detected_keywords": ["revenue", "growth", "quarterly"]
        },
        "available_space": {"width": 1260, "height": 720}
    }
).json()

# Response: {"can_handle": true, "confidence": 0.95, ...}

# 3. If confident, get chart recommendation
if can_handle_response["can_handle"] and can_handle_response["confidence"] >= 0.7:
    chart_response = requests.post(
        f"{BASE_URL}/api/v1/analytics/recommend-chart",
        json={
            "slide_content": content,
            "detected_patterns": ["time_series"]
        }
    ).json()

    best_chart = chart_response["recommended_charts"][0]
    # chart_type: "line", confidence: 0.95

# 4. Generate the chart
chart_result = requests.post(
    f"{BASE_URL}/api/v1/analytics/L02/{best_chart['chart_type']}",
    json={
        "presentation_id": "pres-123",
        "slide_id": "slide-7",
        "slide_number": 7,
        "narrative": "Show quarterly revenue growth highlighting strong Q3-Q4 performance",
        "data": [
            {"label": "Q1 2024", "value": 125000},
            {"label": "Q2 2024", "value": 145000},
            {"label": "Q3 2024", "value": 162000},
            {"label": "Q4 2024", "value": 178000}
        ]
    }
).json()

# Result contains:
# - content.element_3: Chart HTML with Canvas and Chart.js script
# - content.element_2: AI-generated insights HTML
# - metadata: Service info, chart type, data source
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.1.5 | Dec 2024 | Added `response_format` with field aliases in /capabilities |
| 3.1.4 | Dec 2024 | Complete API reference documentation |
| 3.0.0 | Dec 2024 | Added 3 Director coordination endpoints |
| 2.0.0 | Nov 2024 | Chart.js migration, synthetic data |
| 1.0.0 | Oct 2024 | Initial release with ApexCharts |

---

## Related Documents

- [SERVICE_CAPABILITIES_SPEC.md](./SERVICE_CAPABILITIES_SPEC.md) - Coordination endpoint specification
- [SERVICE_COORDINATION_REQUIREMENTS.md](./SERVICE_COORDINATION_REQUIREMENTS.md) - Architecture overview
- [SERVICE_REQUIREMENTS_ANALYTICS.md](./SERVICE_REQUIREMENTS_ANALYTICS.md) - Layout field mapping
- [TEXT_SERVICE_CAPABILITIES.md](./TEXT_SERVICE_CAPABILITIES.md) - Text Service integration
- [SLIDE_GENERATION_INPUT_SPEC.md](./SLIDE_GENERATION_INPUT_SPEC.md) - Grid system reference
