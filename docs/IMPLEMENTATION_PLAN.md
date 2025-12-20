# Service Coordination Implementation Plan

## Overview

This document outlines the phased implementation plan for evolving Director Agent's Strawman Service to coordinate with Layout Service and Content Services. The goal is to make intelligent layout/service/variant decisions at strawman generation time.

**Key Principle**: Build a working **per-slide decision engine** first (Phases 1-4), then layer **playbooks** on top as an optimization (Phase 5+).

---

## Team Responsibilities

| Team | Primary Service | Key Deliverables |
|------|-----------------|------------------|
| **Director Team** | Strawman Service | Per-slide decision engine, playbook integration |
| **Layout Service Team** | Layout Service v7.5 | Layout discovery, recommendations, validation |
| **Text Service Team** | Text Service v1.2 | Capabilities, variant recommendations |
| **Analytics Service Team** | Analytics Service v3 | Capabilities, chart recommendations |
| **Illustrator Service Team** | Illustrator v1.0 | Capabilities, visual type recommendations |
| **Diagram Service Team** | Diagram Service v1.0 | Capabilities, diagram recommendations |

---

## Phase 1: Service Capabilities

**Duration**: 1-2 weeks
**Goal**: All services expose `/capabilities` endpoint describing what they can do

### Critical Concept: Layout Grid Size

> **⚠️ IMPORTANT**: The Layout Service must expose **exact content zone dimensions** (grid size) for every layout. This is the foundational parameter that enables intelligent content placement.

Every layout provides:
- **Fixed zones**: Title (required), subtitle (optional), footer (required), logo (optional)
- **Main content zone**: Primary area for text, images, charts, diagrams, illustrations
- **Exact dimensions**: Width × Height in pixels for each zone

Content services use these dimensions to:
1. Recommend variants that fit the available space
2. Generate content sized correctly for the zone
3. Avoid overflow or underutilization

### Director Team
- [ ] Define standard capabilities response schema
- [ ] Create capabilities caching mechanism in Strawman
- [ ] Build service discovery on Strawman startup
- [ ] **Cache layout grid dimensions** for content routing
- [ ] Add logging for service capabilities

### Layout Service Team
| Task | Endpoint | Priority |
|------|----------|----------|
| Expose layout capabilities | `GET /capabilities` | P0 |
| List all layouts with metadata | `GET /layouts` | P0 |
| **Return layout with content zones** | `GET /layouts/{id}` | **P0** |

**Critical Deliverable**: `GET /layouts/{id}` must return `content_zones` array with:
- `zone_id`: Identifier (title, subtitle, main_content, footer, logo)
- `dimensions`: `{width: px, height: px}`
- `position`: `{x: px, y: px}`
- `accepts`: Content types allowed (text, image, chart, etc.)
- `sub_zones`: For multi-column layouts, individual cell dimensions

**Capabilities Response**:
```json
{
  "service": "layout-service",
  "version": "7.5.0",
  "capabilities": {
    "layout_series": ["L", "C", "H"],
    "total_layouts": 99,
    "supports_themes": true
  },
  "layout_series_info": {
    "L": {"name": "Legacy", "supports_themes": false, "count": 30},
    "C": {"name": "Content", "supports_themes": true, "count": 25},
    "H": {"name": "Hero", "supports_themes": true, "count": 15}
  }
}
```

### Text Service Team
| Task | Endpoint | Priority |
|------|----------|----------|
| Expose capabilities | `GET /capabilities` | P0 |

**Capabilities Response**:
```json
{
  "service": "text-service",
  "version": "1.2.0",
  "capabilities": {
    "slide_types": ["matrix", "grid", "comparison", "sequential", "metrics", "table", "hero"],
    "variants": ["matrix_2x2", "matrix_2x3", "grid_2x3", "comparison_3col", "metrics_3col", "..."],
    "max_items_per_slide": 8
  },
  "content_signals": {
    "handles_well": ["structured_content", "bullet_points", "comparisons", "processes"],
    "handles_poorly": ["charts", "data_visualization", "diagrams"]
  }
}
```

### Analytics Service Team
| Task | Endpoint | Priority |
|------|----------|----------|
| Expose capabilities | `GET /capabilities` | P0 |

**Capabilities Response**:
```json
{
  "service": "analytics-service",
  "version": "3.0.0",
  "capabilities": {
    "chart_types": ["bar_vertical", "bar_horizontal", "line", "pie", "doughnut", "scatter", "treemap"],
    "can_generate_data": true
  },
  "content_signals": {
    "handles_well": ["numerical_data", "time_series", "comparisons_with_numbers", "trends"],
    "handles_poorly": ["pure_text", "bullet_points", "processes_without_data"],
    "pattern_detection": {
      "time_series": ["over time", "by quarter", "trend"],
      "comparison": ["vs", "compared to"],
      "composition": ["breakdown", "distribution", "share"]
    }
  }
}
```

### Illustrator Service Team
| Task | Endpoint | Priority |
|------|----------|----------|
| Expose capabilities | `GET /capabilities` | P0 |

**Capabilities Response**:
```json
{
  "service": "illustrator-service",
  "version": "1.0.0",
  "capabilities": {
    "visualization_types": ["pyramid", "funnel", "concentric_circles"]
  },
  "content_signals": {
    "handles_well": ["hierarchies", "levels", "stages", "layers"],
    "handles_poorly": ["data_heavy", "many_items", "tabular_data"]
  },
  "specializations": {
    "pyramid": {"keywords": ["pyramid", "hierarchy", "levels", "tier"], "ideal_items": [3, 6]},
    "funnel": {"keywords": ["funnel", "conversion", "pipeline"], "ideal_items": [3, 5]},
    "concentric_circles": {"keywords": ["core", "layers", "ecosystem"], "ideal_items": [3, 5]}
  }
}
```

### Diagram Service Team
| Task | Endpoint | Priority |
|------|----------|----------|
| Expose capabilities | `GET /capabilities` | P0 |

**Capabilities Response**:
```json
{
  "service": "diagram-service",
  "version": "1.0.0",
  "capabilities": {
    "diagram_types": ["flowchart", "block_diagram", "sequence_diagram", "entity_relationship"]
  },
  "content_signals": {
    "handles_well": ["processes", "workflows", "decision_trees", "architecture"],
    "handles_poorly": ["pure_data", "bullet_lists"]
  },
  "diagram_type_signals": {
    "flowchart": {"keywords": ["flow", "process", "steps", "decision"]},
    "block_diagram": {"keywords": ["architecture", "components", "system"]},
    "sequence_diagram": {"keywords": ["sequence", "interaction", "message"]},
    "entity_relationship": {"keywords": ["entity", "relationship", "database"]}
  }
}
```

### Phase 1 Completion Criteria
- [ ] All 5 services expose `GET /capabilities`
- [ ] Strawman can query and cache all capabilities at startup
- [ ] Capabilities logged for debugging

---

## Phase 2: Content Negotiation

**Duration**: 2-3 weeks
**Goal**: Services answer "can you handle this specific content?" with confidence scores

### Director Team
- [ ] Build content analysis in Strawman (extract topics, keywords, numbers, patterns)
- [ ] Implement parallel `/can-handle` queries to all content services
- [ ] Build service selection logic (pick highest confidence)
- [ ] Add logging for routing decisions

### All Content Services (Text, Analytics, Illustrator, Diagram)
| Task | Endpoint | Priority |
|------|----------|----------|
| Content negotiation | `POST /can-handle` | P0 |

**Request Schema** (same for all):
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
  }
}
```

**Response Schema** (same for all):
```json
{
  "can_handle": true,
  "confidence": 0.85,
  "reason": "3 KPI metrics with numerical data - good fit for metrics layout",
  "suggested_approach": "metrics"
}
```

### Service-Specific Logic

**Text Service** `/can-handle`:
- Check topic count against variant requirements
- Detect if content is structured (bullets, comparisons, processes)
- Return high confidence for text-heavy content
- Return low confidence for chart/data requests

**Analytics Service** `/can-handle`:
- Detect numerical patterns in topics
- Look for time-series keywords
- Return high confidence for data visualization requests
- Return low confidence for pure text content

**Illustrator Service** `/can-handle`:
- Look for hierarchy/funnel/layer keywords
- Check topic count fits ideal range (3-6)
- Return high confidence for visual metaphor content
- Return low confidence for data-heavy content

**Diagram Service** `/can-handle`:
- Detect process/workflow keywords
- Look for decision/branching patterns
- Return high confidence for flow/architecture content
- Return low confidence for pure text

### Phase 2 Completion Criteria
- [ ] All 4 content services implement `POST /can-handle`
- [ ] Strawman queries all services in parallel
- [ ] Strawman selects highest confidence service
- [ ] Routing decisions logged with reasons

---

## Phase 3: Variant & Layout Recommendation

**Duration**: 2-3 weeks
**Goal**: Services recommend specific variants/layouts (instead of Strawman guessing)

### Director Team
- [ ] Implement variant recommendation flow (call winning service)
- [ ] Implement layout recommendation flow (call Layout Service)
- [ ] Integrate recommendations into strawman output
- [ ] Add fallback logic if recommendations fail

### Text Service Team
| Task | Endpoint | Priority |
|------|----------|----------|
| Variant recommendation | `POST /recommend-variant` | P0 |

**Request**:
```json
{
  "slide_content": {
    "title": "Key Metrics",
    "topics": ["Revenue: $4.2M", "Users: 50K", "NPS: 72"],
    "topic_count": 3
  }
}
```

**Response**:
```json
{
  "recommended_variants": [
    {"variant_id": "metrics_3col", "confidence": 0.92, "reason": "3 KPIs with numbers"},
    {"variant_id": "comparison_3col", "confidence": 0.70, "reason": "3 items could compare"}
  ],
  "not_recommended": [
    {"variant_id": "grid_2x3", "reason": "Needs 6 topics, only 3 provided"}
  ]
}
```

### Analytics Service Team
| Task | Endpoint | Priority |
|------|----------|----------|
| Chart recommendation | `POST /recommend-chart` | P0 |

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
    {"chart_type": "line", "confidence": 0.95, "reason": "Time series data best shown as line"},
    {"chart_type": "area", "confidence": 0.80, "reason": "Area also works for trends"}
  ]
}
```

### Illustrator Service Team
| Task | Endpoint | Priority |
|------|----------|----------|
| Visual type recommendation | `POST /recommend-visual` | P0 |

**Response**:
```json
{
  "recommended_visuals": [
    {"visual_type": "pyramid", "confidence": 0.88, "reason": "Hierarchy with 4 levels"},
    {"visual_type": "funnel", "confidence": 0.65, "reason": "Could represent stages"}
  ]
}
```

### Diagram Service Team
| Task | Endpoint | Priority |
|------|----------|----------|
| Diagram type recommendation | `POST /recommend-diagram` | P0 |

**Response**:
```json
{
  "recommended_diagrams": [
    {"diagram_type": "flowchart", "confidence": 0.90, "reason": "Process with decision points"},
    {"diagram_type": "block_diagram", "confidence": 0.60, "reason": "Could show components"}
  ]
}
```

### Layout Service Team
| Task | Endpoint | Priority |
|------|----------|----------|
| Layout recommendation | `POST /recommend-layout` | P0 |
| Layout validation | `POST /can-fit` | P0 |

**`POST /recommend-layout` Request**:
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

**`POST /recommend-layout` Response**:
```json
{
  "recommended_layouts": [
    {"layout_id": "C01", "series": "C", "confidence": 0.90, "reason": "3-column content, theme-enabled"},
    {"layout_id": "L25", "series": "L", "confidence": 0.75, "reason": "Standard content layout"}
  ]
}
```

**`POST /can-fit` Request**:
```json
{
  "layout_id": "C01",
  "content_zones_needed": 3,
  "content_type": "text"
}
```

**`POST /can-fit` Response**:
```json
{
  "can_fit": true,
  "layout_id": "C01",
  "content_zones_available": 4,
  "suggested_layout": null
}
```

### Phase 3 Completion Criteria
- [ ] Text Service: `POST /recommend-variant`
- [ ] Analytics Service: `POST /recommend-chart`
- [ ] Illustrator: `POST /recommend-visual`
- [ ] Diagram Service: `POST /recommend-diagram`
- [ ] Layout Service: `POST /recommend-layout` + `POST /can-fit`
- [ ] Strawman integrates all recommendations

---

## Phase 4: Strawman Per-Slide Decision Engine

**Duration**: 3-4 weeks
**Goal**: Strawman makes ALL decisions at generation time using Phases 1-3

### The 4-Step Strawman Process

> **This is the heart of the coordination system:**
>
> 1. **STEP 1**: Determine storyline & messages → Deep thought + playbooks to determine WHAT to say
> 2. **STEP 2**: Select layouts → Layout Service provides layouts with **grid size** (content zone dimensions)
> 3. **STEP 3**: Select content variants → Based on **space available**, services recommend variants
> 4. **STEP 4**: Refine & personalize → Assemble personalized content into each element
>
> **Key Insight**: Message drives layout, not the other way around.
>
> **Critical Constraint**: Layouts, slide types, and variants are **NOT independent**:
> - Layout → constrains → Slide Types (e.g., H01 only supports `hero`, not `matrix`)
> - Layout → constrains → Variants (e.g., C01 supports `matrix_2x2` but not `matrix_3x3`)
> - Steps 2-3 require **bidirectional negotiation** if variant doesn't fit layout

### Director Team (Primary Focus)

| Task | Priority | Description |
|------|----------|-------------|
| **Storyline Analyzer** | **P0** | **Deep thought to determine presentation storyline and slide messages** |
| **Playbook Matcher** | **P0** | **Match user prompt against available playbooks for structure guidance** |
| **Grid Size Handler** | **P0** | **Fetch and cache content zone dimensions from layout** |
| **Constraint Validator** | **P0** | **Validate Layout-SlideType-Variant compatibility; negotiate if mismatch** |
| Content Analyzer | P0 | Extract topics, keywords, numbers, patterns from slide content |
| Service Router | P0 | Query all services with available_space, pick highest confidence |
| Variant Selector | P0 | Call winning service's recommend endpoint with grid size; check layout compatibility |
| Layout Selector | P0 | Call Layout Service's recommend endpoint based on message; return supported slide types |
| **Content Refiner** | **P0** | **Refine and personalize content based on variant and layout elements** |
| Decision Assembler | P0 | Combine all decisions into strawman output |
| Fallback Handler | P1 | Handle cases when services fail/disagree or layout-variant mismatch |
| Logging & Metrics | P1 | Track decision accuracy, service response times |

**Per-Slide Decision Flow (4-Step Process)**:
```
┌─────────────────────────────────────────────────────────────────┐
│                    STRAWMAN SERVICE                             │
│                                                                 │
│  ╔═══════════════════════════════════════════════════════════╗ │
│  ║  STEP 1: DETERMINE STORYLINE & MESSAGES                   ║ │
│  ╚═══════════════════════════════════════════════════════════╝ │
│                                                                 │
│  1a. DEEP THOUGHT ANALYSIS                                     │
│      └── Analyze user prompt for core message/purpose          │
│      └── Identify key themes, arguments, data points           │
│      └── Determine optimal presentation structure              │
│                                                                 │
│  1b. PLAYBOOK MATCHING (if applicable)                         │
│      └── Match prompt against available playbooks              │
│      └── If match (confidence > 0.8): use playbook structure   │
│      └── If no match: use AI to determine structure            │
│                                                                 │
│  1c. SLIDE MESSAGE OUTLINE                                     │
│      └── Generate high-level bullets for each slide            │
│      └── Determine slide purpose (title, problem, metrics...)  │
│      └── Output:                                               │
│          {                                                     │
│            "storyline": "Q4 review showing growth",            │
│            "slides": [                                         │
│              {"purpose": "title", "message": "Q4 Review"},     │
│              {"purpose": "metrics", "message": "3 key KPIs"},  │
│              {"purpose": "challenges", "message": "2 risks"}   │
│            ]                                                   │
│          }                                                     │
│                                                                 │
│  ╔═══════════════════════════════════════════════════════════╗ │
│  ║  STEP 2: SELECT LAYOUTS (work with Layout Service)        ║ │
│  ╚═══════════════════════════════════════════════════════════╝ │
│                                                                 │
│  For each slide message from Step 1:                           │
│                                                                 │
│  2a. SELECT LAYOUT FOR MESSAGE                                 │
│      └── From playbook: use specified layout (H01, C01, etc.)  │
│      └── OR POST /recommend-layout → Layout Service            │
│          Request: {message_type, content_hints}                │
│                                                                 │
│  2b. GET GRID SIZE (Critical Step)                             │
│      └── GET /layouts/{id} → Layout Service                    │
│      └── Response includes content_zones:                      │
│          • title: {width: 1800, height: 80}                    │
│          • subtitle: {width: 1800, height: 50} (optional)      │
│          • main_content: {width: 1800, height: 750}            │
│          • sub_zones: [{col_1: 560×750}, {col_2: 560×750}...]  │
│          • footer: {width: 1800, height: 40}                   │
│                                                                 │
│  ╔═══════════════════════════════════════════════════════════╗ │
│  ║  STEP 3: SELECT CONTENT VARIANTS (based on space)         ║ │
│  ╚═══════════════════════════════════════════════════════════╝ │
│                                                                 │
│  3a. SELECT SERVICE (with available_space)                     │
│      └── POST /can-handle → Text Service                       │
│          Request: {content, hints, available_space: 1800×750}  │
│          Response: {confidence: 0.85, fits_well: true}         │
│      └── POST /can-handle → Analytics Service                  │
│          Response: {confidence: 0.40, fits_well: true}         │
│      └── POST /can-handle → Illustrator                        │
│          Response: {confidence: 0.20, fits_well: false}        │
│      └── Winner: Text Service (highest confidence + fits)      │
│                                                                 │
│  3b. GET VARIANT RECOMMENDATION (with space)                   │
│      └── POST /recommend-variant → Text Service                │
│          Request: {content, available_space: 1800×750}         │
│          Response: {                                           │
│            variant: "metrics_3col",                            │
│            confidence: 0.92,                                   │
│            requires_space: {width: 1680, height: 600}          │
│          }                                                     │
│                                                                 │
│  ╔═══════════════════════════════════════════════════════════╗ │
│  ║  STEP 4: REFINE & PERSONALIZE CONTENT                     ║ │
│  ╚═══════════════════════════════════════════════════════════╝ │
│                                                                 │
│  4a. REFINE CONTENT FOR VARIANT                                │
│      └── Based on selected variant (metrics_3col)              │
│      └── Refine topics to match element structure              │
│      └── Apply user context and personalization                │
│                                                                 │
│  4b. MAP CONTENT TO LAYOUT ELEMENTS                            │
│      └── layout: C01 (from step 2)                             │
│      └── service: text-service (from step 3a)                  │
│      └── variant: metrics_3col (from step 3b)                  │
│      └── Content mapping:                                      │
│          • title → "Key Performance Metrics"                   │
│          • col_1 → "Revenue: $4.2M (+15% YoY)"                 │
│          • col_2 → "Active Users: 50K (+30%)"                  │
│          • col_3 → "NPS Score: 72 (+8 pts)"                    │
│                                                                 │
│  4c. OUTPUT COMPLETE PERSONALIZED STRAWMAN                     │
│      └── {layout, service, variant, content_mapping, reasons}  │
│      └── Each element populated with refined content           │
│      └── Ready for user review and approval                    │
└─────────────────────────────────────────────────────────────────┘
```

**Strawman Output with Per-Slide Decisions**:
```json
{
  "presentation_id": "uuid",
  "title": "Q4 Business Review",
  "decision_method": "per_slide_engine",
  "playbook": null,

  "slides": [
    {
      "slide_number": 1,
      "title": "Q4 2024 Business Review",
      "topics": [],
      "slide_type": "hero",

      "decisions": {
        "method": "per_slide_engine",
        "service": {
          "id": "text-service",
          "endpoint": "/v1.2/hero/title-with-image",
          "confidence": 0.95,
          "reason": "Hero slide best handled by text-service"
        },
        "variant": null,
        "layout": {
          "id": "H01",
          "series": "H",
          "confidence": 0.90,
          "reason": "Hero layout for title slides"
        }
      }
    },
    {
      "slide_number": 2,
      "title": "Key Performance Metrics",
      "topics": ["Revenue: $4.2M (+15%)", "Users: 50K (+30%)", "NPS: 72 (+8)"],
      "slide_type": "content",

      "decisions": {
        "method": "per_slide_engine",
        "service": {
          "id": "text-service",
          "endpoint": "/v1.2/generate",
          "confidence": 0.85,
          "competing_services": [
            {"id": "analytics-service", "confidence": 0.40},
            {"id": "illustrator", "confidence": 0.15}
          ],
          "reason": "Structured KPI content, not chart data"
        },
        "variant": {
          "id": "metrics_3col",
          "confidence": 0.92,
          "alternatives": [
            {"id": "comparison_3col", "confidence": 0.70}
          ],
          "reason": "3 KPIs with numbers - ideal for metrics layout"
        },
        "layout": {
          "id": "C01",
          "series": "C",
          "confidence": 0.90,
          "reason": "3-column themed layout for metrics"
        }
      }
    },
    {
      "slide_number": 3,
      "title": "Revenue Trend Over Time",
      "topics": ["Show quarterly revenue from Q1-Q4 2024"],
      "slide_type": "chart",

      "decisions": {
        "method": "per_slide_engine",
        "service": {
          "id": "analytics-service",
          "endpoint": "/api/v1/analytics/L02/line",
          "confidence": 0.92,
          "reason": "Time series data visualization"
        },
        "variant": {
          "chart_type": "line",
          "confidence": 0.95,
          "reason": "Time series best shown as line chart"
        },
        "layout": {
          "id": "L02",
          "series": "L",
          "confidence": 0.95,
          "reason": "Chart layout for analytics"
        }
      }
    }
  ],

  "decision_log": [
    {"slide": 1, "step": "service_selection", "winner": "text-service", "confidence": 0.95},
    {"slide": 1, "step": "layout_selection", "layout": "H01", "confidence": 0.90},
    {"slide": 2, "step": "service_selection", "winner": "text-service", "confidence": 0.85},
    {"slide": 2, "step": "variant_selection", "variant": "metrics_3col", "confidence": 0.92},
    {"slide": 2, "step": "layout_selection", "layout": "C01", "confidence": 0.90},
    {"slide": 3, "step": "service_selection", "winner": "analytics-service", "confidence": 0.92},
    {"slide": 3, "step": "variant_selection", "chart_type": "line", "confidence": 0.95},
    {"slide": 3, "step": "layout_selection", "layout": "L02", "confidence": 0.95}
  ]
}
```

### All Service Teams (Support)
- [ ] Ensure Phase 1-3 endpoints are stable and performant
- [ ] Add response time monitoring
- [ ] Handle edge cases gracefully

### Phase 4 Completion Criteria
- [ ] Strawman generates complete decisions for ALL slides
- [ ] No hardcoded layout/variant rules remain
- [ ] All decisions logged with confidence and reasons
- [ ] System works end-to-end without playbooks
- [ ] User can approve strawman with real layouts visible

**MILESTONE**: At Phase 4 completion, the system is fully functional without playbooks.

---

## Phase 5: Playbook Layer

**Duration**: 4-6 weeks
**Goal**: Add presentation-level playbooks as optimization layer

### Director Team (Primary Focus)

| Task | Priority | Description |
|------|----------|-------------|
| Playbook Schema | P0 | Define JSON schema for playbooks |
| Playbook Registry | P0 | Storage and loading of playbooks |
| Playbook Matcher | P0 | Match user prompt to playbook triggers |
| Playbook Executor | P0 | Generate strawman from playbook template |
| Fallback Integration | P0 | Use per-slide engine when no playbook matches |
| First 3 Playbooks | P0 | `startup_pitch`, `quarterly_review`, `educational` |

**Flow with Playbooks**:
```
User Prompt
    │
    ▼
Match against Playbooks (keywords, patterns)
    │
    ├── MATCH (confidence > 0.8)
    │   └── Ask user: "This looks like a [Startup Pitch]. Use template? (S/M/L)"
    │   └── If yes: Generate from playbook sequence
    │   └── Validate each position with services
    │
    └── NO MATCH
        └── Use per-slide engine (Phase 4)
        └── Full AI + service collaboration
```

**Strawman Output with Playbook**:
```json
{
  "presentation_id": "uuid",
  "title": "Series A Pitch - Acme Corp",
  "decision_method": "playbook",

  "playbook": {
    "id": "startup_pitch",
    "name": "Startup Pitch Deck",
    "variant": "medium",
    "duration_minutes": 30,
    "match_confidence": 0.92
  },

  "slides": [
    {
      "slide_number": 1,
      "position_in_playbook": 1,
      "purpose": "title",
      "title": "Acme Corp - AI-Powered Manufacturing",

      "decisions": {
        "method": "playbook",
        "from_playbook": true,
        "service": {"id": "text-service", "endpoint": "/v1.2/hero/title-with-image"},
        "layout": {"id": "H01", "series": "H"},
        "validated": true
      }
    }
  ]
}
```

### All Service Teams (Support)
- [ ] Ensure validation endpoints work for playbook decisions
- [ ] Add any service-specific endpoints needed for playbook validation

### Phase 5 Deliverables
- [ ] Playbook JSON schema defined
- [ ] `startup_pitch.json` playbook (S/M/L)
- [ ] `quarterly_review.json` playbook (S/M/L)
- [ ] `educational.json` playbook (S/M/L)
- [ ] Playbook matching in Strawman
- [ ] Fallback to per-slide engine working

---

## Phase 6: Expansion & Optimization

**Duration**: Ongoing
**Goal**: Continuous improvement based on usage data

### Director Team
- [ ] Add playbooks 4-10 (see SERVICE_COORDINATION_REQUIREMENTS.md)
- [ ] Track playbook match rate
- [ ] Identify common user edits (signals for improvement)
- [ ] A/B test layout/variant alternatives
- [ ] Convert successful per-slide patterns into playbooks

### All Service Teams
- [ ] Monitor endpoint performance
- [ ] Improve confidence scoring based on real data
- [ ] Add new variants/chart types based on demand

---

## Timeline Summary

| Phase | Duration | Primary Team | Key Milestone |
|-------|----------|--------------|---------------|
| **Phase 1** | 1-2 weeks | All Services | All `/capabilities` endpoints live |
| **Phase 2** | 2-3 weeks | All Content Services | Service routing by confidence |
| **Phase 3** | 2-3 weeks | All Services | Recommendations working |
| **Phase 4** | 3-4 weeks | Director Team | **Per-slide engine complete** |
| **Phase 5** | 4-6 weeks | Director Team | First 3 playbooks live |
| **Phase 6** | Ongoing | All Teams | Continuous optimization |

**Total to working system (Phase 4)**: ~8-12 weeks
**Total to playbooks (Phase 5)**: ~12-18 weeks

---

## API Endpoint Summary by Service

### Layout Service v7.5

| Phase | Endpoint | Method | Purpose |
|-------|----------|--------|---------|
| 1 | `/capabilities` | GET | Describe layout capabilities |
| 1 | `/layouts` | GET | List all layouts with metadata |
| 3 | `/recommend-layout` | POST | Recommend layout for content |
| 3 | `/can-fit` | POST | Validate content fits layout |

### Text Service v1.2

| Phase | Endpoint | Method | Purpose |
|-------|----------|--------|---------|
| 1 | `/capabilities` | GET | Describe text service capabilities |
| 2 | `/can-handle` | POST | Can this content be handled? |
| 3 | `/recommend-variant` | POST | Recommend best variant |

### Analytics Service v3

| Phase | Endpoint | Method | Purpose |
|-------|----------|--------|---------|
| 1 | `/capabilities` | GET | Describe analytics capabilities |
| 2 | `/can-handle` | POST | Can this content be visualized? |
| 3 | `/recommend-chart` | POST | Recommend chart type |

### Illustrator Service v1.0

| Phase | Endpoint | Method | Purpose |
|-------|----------|--------|---------|
| 1 | `/capabilities` | GET | Describe illustrator capabilities |
| 2 | `/can-handle` | POST | Is this good for infographics? |
| 3 | `/recommend-visual` | POST | Recommend visual type |

### Diagram Service v1.0

| Phase | Endpoint | Method | Purpose |
|-------|----------|--------|---------|
| 1 | `/capabilities` | GET | Describe diagram capabilities |
| 2 | `/can-handle` | POST | Is this good for diagrams? |
| 3 | `/recommend-diagram` | POST | Recommend diagram type |

---

## Dependencies

```
Phase 1 (Capabilities)
    │
    ▼
Phase 2 (Can-Handle) ─── Depends on Phase 1 (need capabilities to query)
    │
    ▼
Phase 3 (Recommendations) ─── Depends on Phase 2 (need service selection first)
    │
    ▼
Phase 4 (Per-Slide Engine) ─── Depends on Phases 1-3 (integrates all)
    │
    ▼
Phase 5 (Playbooks) ─── Depends on Phase 4 (per-slide is fallback)
    │
    ▼
Phase 6 (Optimization) ─── Depends on Phase 5 (iterate on foundation)
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Service endpoints slow | Add timeout + fallback to defaults |
| Low confidence from all services | Use Text Service as default fallback |
| Layout doesn't fit content | Use L25 as universal fallback |
| Playbook match is wrong | Allow user to switch/override |
| Service unavailable | Cache last-known capabilities, proceed with cached data |

---

## Success Metrics

| Metric | Phase 4 Target | Phase 5 Target | Phase 6 Target |
|--------|---------------|----------------|----------------|
| Decisions at strawman time | 100% | 100% | 100% |
| Service routing accuracy | 80%+ | 85%+ | 90%+ |
| Variant selection accuracy | 75%+ | 85%+ | 90%+ |
| Layout selection accuracy | 80%+ | 85%+ | 90%+ |
| Playbook match rate | N/A | 40%+ | 70%+ |
| User edits to structure | 30% | 20% | <15% |

---

## Document References

- [SERVICE_CAPABILITIES_SPEC.md](./SERVICE_CAPABILITIES_SPEC.md) - Detailed endpoint specifications
- [SERVICE_COORDINATION_REQUIREMENTS.md](./SERVICE_COORDINATION_REQUIREMENTS.md) - Architecture and playbook details

---

*Document Version: 4.0*
*Created: December 2024*
*Owner: Director Agent Team*
*Changes in v4.0:*
- *Added Layout-SlideType-Variant constraint to 4-Step process description*
- *Added P0 task: Constraint Validator (validate Layout-SlideType-Variant compatibility)*
- *Updated Variant Selector and Layout Selector to include constraint handling*
- *Updated Fallback Handler to include layout-variant mismatch handling*

*Changes in v3.0:*
- *Updated from 3-Step to 4-Step Strawman Process*
- *Added Step 1: Determine Storyline & Messages (deep thought + playbooks)*
- *Added P0 tasks: Storyline Analyzer, Playbook Matcher, Content Refiner*
- *Updated Per-Slide Decision Flow diagram to show 4 steps*
- *Key insight: Message drives layout, not the other way around*

*Changes in v2.0:*
- *Added Critical Concept: Layout Grid Size section to Phase 1*
- *Added "Cache layout grid dimensions" task for Director Team*
- *Updated Phase 4 with grid size → recommendations → decisions flow*
- *Added Grid Size Handler as P0 task*
