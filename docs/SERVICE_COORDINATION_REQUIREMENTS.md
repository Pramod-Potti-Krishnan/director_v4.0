# Service Coordination Architecture: Strategic Requirements

## Executive Summary

This document outlines the architecture for evolving the **Strawman Service** (part of Director ecosystem) to become the central coordinator between Layout Service and Content Services. The goal is to make **all layout, service, and variant decisions at strawman generation time** through intelligent per-slide decision-making, enhanced by presentation-level playbooks.

**Key Principle**: Build a working **per-slide decision engine** first (using service capabilities and recommendations), then layer **playbooks** on top as an optimization for common presentation types.

**Related Documents**:
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - **Phased rollout plan with team assignments**
- [SERVICE_CAPABILITIES_SPEC.md](./SERVICE_CAPABILITIES_SPEC.md) - Detailed endpoint specifications

---

## 1. The 4-Step Strawman Process

> **This is the heart of the coordination equation.**
>
> **Key Insight**: Start with WHAT to say (storyline), then figure out HOW to present it (layout → variant → content).

```
┌─────────────────────────────────────────────────────────────────┐
│                   4-STEP STRAWMAN PROCESS                       │
│                                                                 │
│  STEP 1: DETERMINE STORYLINE & MESSAGES                        │
│  ──────────────────────────────────────                        │
│  Deep thought + playbooks to determine:                        │
│  • Overall presentation storyline                              │
│  • High-level bullets for each slide                           │
│  • Slide purposes (title, problem, solution, metrics, etc.)    │
│  • If playbook matches, use its structure as guidance          │
│                                                                 │
│  Output:                                                        │
│  {                                                              │
│    "storyline": "Q4 business review showing growth",           │
│    "slides": [                                                  │
│      {"purpose": "title", "message": "Q4 2024 Review"},        │
│      {"purpose": "highlights", "message": "3 key wins"},       │
│      {"purpose": "metrics", "message": "KPI dashboard"},       │
│      {"purpose": "next_steps", "message": "Q1 priorities"}     │
│    ]                                                            │
│  }                                                              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  STEP 2: SELECT LAYOUTS (work with Layout Service)             │
│  ─────────────────────────────────────────────────             │
│  For each slide's message, determine best layout:              │
│  • Use playbook defaults based on degree of fit                │
│  • OR call Layout Service /recommend-layout                    │
│  • Get grid size (content zone dimensions) for each layout     │
│                                                                 │
│  Every layout comes with content_zones:                        │
│  • Title zone: {width: 1800, height: 80} - required            │
│  • Subtitle zone: {width: 1800, height: 50} - optional         │
│  • Main content: {width: 1800, height: 750} - for content      │
│  • Footer zone: {width: 1800, height: 40} - required           │
│  • Logo zone: {width: 180, height: 60} - optional              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  STEP 3: SELECT CONTENT VARIANTS (work with Content Services)  │
│  ──────────────────────────────────────────────────────────────│
│  Based on selected layout's grid size:                         │
│  • Content services recommend variants that fit                │
│  • Consider message complexity + available space               │
│  • "Can I handle this in 1800×750?" → confidence score         │
│  • "metrics_3col needs 1680×600 - fits!" → recommendation      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  STEP 4: REFINE & PERSONALIZE CONTENT                          │
│  ────────────────────────────────────                          │
│  Make the strawman more personalized:                          │
│  • Refine content based on variant selected                    │
│  • Map content to specific layout elements                     │
│  • Personalize based on user context                           │
│  • Assemble final decision with all details                    │
│                                                                 │
│  Output:                                                        │
│  • Layout: C01 (from Step 2)                                   │
│  • Service: text-service (from Step 3)                         │
│  • Variant: metrics_3col (from Step 3)                         │
│  • Content mapping: title → "Key Metrics", col_1 → "Revenue"   │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Order Matters

**Message drives layout, not the other way around.**

1. **Step 1 first**: You can't pick a layout until you know what you're trying to say
2. **Then Step 2**: Layout depends on the message (metrics → C01, hero → H01)
3. **Then Step 3**: Variant depends on space available from layout
4. **Finally Step 4**: Personalization happens after all decisions are made

### Why Grid Size is Critical (Steps 2-4)

**The grid size is a foundational parameter.** Without knowing the exact dimensions of content zones, content services cannot:
1. Recommend variants that fit the available space
2. Generate content sized correctly for the zone
3. Avoid overflow or underutilization

**Example**: A 3-column layout (C01) has `main_content: 1800×750` split into three `560×750` columns. Text Service knows `metrics_3col` needs `560px` per column and recommends it. Without this knowledge, we'd be guessing.

### Layout-SlideType-Variant Constraint (Steps 2-3)

**⚠️ CRITICAL**: Layouts, slide types, and variants are **NOT independent**. They form a hierarchical constraint system:

```
Layout Template
    └── supports → Slide Types
                      └── have → Variants
```

**What This Means**:

| Constraint | Rule | Example |
|------------|------|---------|
| **Layout → Slide Types** | Not all slide types work with all layouts | H01 (Hero) only supports `hero`, not `matrix` |
| **Layout → Variants** | Even if slide type is supported, not all variants fit | C01 supports `matrix`, but not `matrix_3x3` |
| **Slide Type → Variants** | Variants belong to specific slide types | `matrix_2x3` is a variant of `matrix`, not `grid` |

**Bidirectional Negotiation in Steps 2-3**:

```
Step 2: Select Layout (e.g., C01)
    │
    └── C01 supports: matrix, comparison, metrics (NOT grid, sequential)
           │
           ▼
Step 3: Select Variant (constrained by layout)
    │
    ├── For matrix on C01: matrix_2x2, matrix_2x3 ✓
    ├── For matrix on C01: matrix_3x3 ✗ (doesn't fit 3-column grid)
    │
    └── If needed variant doesn't fit → go back to Step 2, pick different layout
```

**Layout-SlideType Compatibility**:

| Layout | Supported Slide Types | Service |
|--------|----------------------|---------|
| **L25** | matrix, grid, comparison, sequential, metrics, table | text-service |
| **C01** | matrix, comparison, metrics | text-service |
| **C02** | grid, comparison | text-service |
| **H01, H02, H03** | hero (title, section, closing) | text-service |
| **L02** | chart | analytics-service |

See [SERVICE_CAPABILITIES_SPEC.md](./SERVICE_CAPABILITIES_SPEC.md) for detailed Layout-SlideType-Variant compatibility matrix.

---

## 2. Current State Analysis

### 2.1 Current Flow (Problems)

```
┌─────────────────────────────────────────────────────────────────┐
│                      DIRECTOR AGENT v4.0                        │
│                                                                 │
│  User Prompt → Strawman Gen → [STRAWMAN OUTPUT] →              │
│               (no structure, every presentation from scratch)   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Key Problems

| Problem | What Happens | Impact |
|---------|--------------|--------|
| **No presentation templates** | Every presentation structured from scratch | Inconsistent, AI guesses structure |
| **No proven sequences** | Slide order determined ad-hoc | Poor narrative flow |
| **Late decisions** | Layout/variant decided after strawman | User can't see real layout in preview |
| **Hardcoded layouts** | `L25` for content, `L29` for hero | No C-series/H-series usage |
| **No time awareness** | Same output for 15min vs 1hr presentation | Wrong depth/breadth |
| **No grid size awareness** | Services don't know available space | Variants may not fit layout |

---

## 3. Playbooks: Presentation-Level Templates

### 3.1 What is a Playbook?

A **Playbook** is a pre-defined **presentation template** that specifies:
- **Complete slide sequence** (what slides, in what order)
- **Slide types at each position** (hero, content, chart, visual, etc.)
- **Layout + Service + Variant** for each position
- **Size variants** based on presentation duration:
  - **Small**: 15 minutes (~5-7 slides)
  - **Medium**: 30 minutes (~10-12 slides)
  - **Large**: 1 hour (~18-25 slides)

### 3.2 Playbook Examples

#### Startup Pitch Deck

| Position | Slide Purpose | Small (15m) | Medium (30m) | Large (1hr) |
|----------|--------------|-------------|--------------|-------------|
| 1 | Title | ✓ | ✓ | ✓ |
| 2 | Problem | ✓ | ✓ | ✓ |
| 3 | Solution | ✓ | ✓ | ✓ |
| 4 | Market Size | - | ✓ (TAM/SAM) | ✓ (detailed) |
| 5 | Product | ✓ | ✓ | ✓ (multiple) |
| 6 | Business Model | - | ✓ | ✓ |
| 7 | Traction | ✓ | ✓ | ✓ (detailed) |
| 8 | Competition | - | - | ✓ |
| 9 | Go-to-Market | - | - | ✓ |
| 10 | Team | - | ✓ | ✓ |
| 11 | Financials | - | ✓ | ✓ (detailed) |
| 12 | The Ask | ✓ | ✓ | ✓ |

#### Educational / Teaching

| Position | Slide Purpose | Small (15m) | Medium (30m) | Large (1hr) |
|----------|--------------|-------------|--------------|-------------|
| 1 | Title | ✓ | ✓ | ✓ |
| 2 | Learning Objectives | ✓ | ✓ | ✓ |
| 3 | Concept Introduction | ✓ | ✓ | ✓ |
| 4 | Core Concept 1 | ✓ | ✓ | ✓ |
| 5 | Core Concept 2 | - | ✓ | ✓ |
| 6 | Core Concept 3 | - | - | ✓ |
| 7 | Deep Dive / Examples | - | ✓ | ✓ (multiple) |
| 8 | Case Study | - | - | ✓ |
| 9 | Common Mistakes | - | - | ✓ |
| 10 | Practice Exercise | - | ✓ | ✓ |
| 11 | Summary / Key Takeaways | ✓ | ✓ | ✓ |
| 12 | Q&A / Resources | - | ✓ | ✓ |

#### RFP Response

| Position | Slide Purpose | Small (15m) | Medium (30m) | Large (1hr) |
|----------|--------------|-------------|--------------|-------------|
| 1 | Title | ✓ | ✓ | ✓ |
| 2 | Executive Summary | ✓ | ✓ | ✓ |
| 3 | Understanding Requirements | ✓ | ✓ | ✓ (detailed) |
| 4 | Our Approach | ✓ | ✓ | ✓ |
| 5 | Methodology | - | ✓ | ✓ (detailed) |
| 6 | Technical Solution | - | ✓ | ✓ (multiple) |
| 7 | Team & Expertise | - | ✓ | ✓ |
| 8 | Past Performance | - | - | ✓ |
| 9 | Timeline | ✓ | ✓ | ✓ (detailed) |
| 10 | Pricing Overview | - | ✓ | ✓ |
| 11 | Risk Mitigation | - | - | ✓ |
| 12 | Why Choose Us | ✓ | ✓ | ✓ |
| 13 | Next Steps | ✓ | ✓ | ✓ |

### 3.3 Playbook Structure (JSON Schema)

```json
{
  "playbook_id": "startup_pitch",
  "name": "Startup Pitch Deck",
  "version": "1.0",
  "description": "Classic investor pitch deck structure",

  "use_cases": [
    "Fundraising pitch to VCs/Angels",
    "Demo day presentation",
    "Investor update"
  ],

  "variants": {
    "small": {
      "duration_minutes": 15,
      "slide_count_range": [5, 7],
      "sequence": [
        {
          "position": 1,
          "purpose": "title",
          "slide_type": "hero",
          "layout": {"preferred": "H01", "fallback": "L29"},
          "service": "text-service",
          "endpoint": "/v1.2/hero/title-with-image",
          "content_guidance": "Company name, tagline, logo"
        },
        {
          "position": 2,
          "purpose": "problem",
          "slide_type": "content",
          "layout": {"preferred": "C01", "fallback": "L25"},
          "service": "text-service",
          "variant": "comparison_3col",
          "content_guidance": "Pain points the market faces"
        },
        {
          "position": 3,
          "purpose": "solution",
          "slide_type": "content",
          "layout": {"preferred": "C01", "fallback": "L25"},
          "service": "text-service",
          "variant": "features_3col",
          "content_guidance": "How your product solves the problem"
        },
        {
          "position": 4,
          "purpose": "product",
          "slide_type": "content",
          "layout": {"preferred": "L25", "fallback": "L25"},
          "service": "text-service",
          "variant": "features_benefits",
          "content_guidance": "Key product features and benefits"
        },
        {
          "position": 5,
          "purpose": "traction",
          "slide_type": "chart",
          "layout": {"preferred": "L02", "fallback": "L02"},
          "service": "analytics-service",
          "chart_type": "line",
          "content_guidance": "Growth metrics, user adoption, revenue"
        },
        {
          "position": 6,
          "purpose": "ask",
          "slide_type": "hero",
          "layout": {"preferred": "H03", "fallback": "L29"},
          "service": "text-service",
          "endpoint": "/v1.2/hero/closing-with-image",
          "content_guidance": "Funding ask, contact info, next steps"
        }
      ]
    },

    "medium": {
      "duration_minutes": 30,
      "slide_count_range": [10, 12],
      "sequence": [
        {"position": 1, "purpose": "title", "...": "..."},
        {"position": 2, "purpose": "problem", "...": "..."},
        {"position": 3, "purpose": "solution", "...": "..."},
        {"position": 4, "purpose": "market_size", "slide_type": "chart", "chart_type": "pie"},
        {"position": 5, "purpose": "product", "...": "..."},
        {"position": 6, "purpose": "business_model", "slide_type": "content", "variant": "metrics_4col"},
        {"position": 7, "purpose": "traction", "...": "..."},
        {"position": 8, "purpose": "team", "slide_type": "content", "variant": "grid_2x3"},
        {"position": 9, "purpose": "financials", "slide_type": "chart", "chart_type": "bar_grouped"},
        {"position": 10, "purpose": "ask", "...": "..."}
      ]
    },

    "large": {
      "duration_minutes": 60,
      "slide_count_range": [18, 25],
      "sequence": ["...expanded sequence with all sections..."]
    }
  },

  "triggers": {
    "keywords": ["pitch", "investor", "funding", "startup", "raise", "seed", "series A"],
    "patterns": ["pitch deck", "investor presentation", "fundraising"]
  }
}
```

---

## 4. Top 10 Playbooks (Initial Set)

| # | Playbook ID | Use Case | Typical Audience |
|---|-------------|----------|------------------|
| 1 | `startup_pitch` | Fundraising, demo day | Investors, VCs |
| 2 | `educational` | Teaching a topic/concept | Students, learners |
| 3 | `rfp_response` | Responding to RFP/RFI | Procurement, buyers |
| 4 | `quarterly_review` | QBR, business update | Leadership, stakeholders |
| 5 | `product_launch` | New product announcement | Customers, market |
| 6 | `sales_pitch` | Selling product/service | Prospects, customers |
| 7 | `project_proposal` | Proposing a new initiative | Decision makers |
| 8 | `training_workshop` | Hands-on training | Employees, users |
| 9 | `company_overview` | Company introduction | Partners, recruits |
| 10 | `status_update` | Project/initiative update | Stakeholders |

### 4.1 Playbook Selection Flow

```
1. Strawman analyzes user prompt
2. Match against playbook triggers (keywords, patterns)
3. If match found:
   a. Ask user to confirm playbook OR auto-select if high confidence
   b. Ask user for duration preference (15min / 30min / 1hr)
   c. Generate slide sequence from playbook template
   d. Fill in user's content into the template positions
4. If no match:
   a. Fall back to AI-generated structure
   b. Use per-slide service negotiation
```

---

## 5. Proposed Architecture: Strawman-Coordinated Decisions

### 5.1 Target State

```
┌─────────────────────────────────────────────────────────────────┐
│                      DIRECTOR AGENT v5.0                        │
│                                                                 │
│  User Prompt → STRAWMAN SERVICE (Enhanced) → [STRAWMAN OUTPUT] │
│                      │                                          │
│                      │ ← Coordinates DURING generation         │
│                      ▼                                          │
│       ┌──────────────────────────────────┐                     │
│       │     PRESENTATION PLAYBOOKS       │                     │
│       │                                  │                     │
│       │  startup_pitch (S/M/L)           │                     │
│       │  educational (S/M/L)             │                     │
│       │  rfp_response (S/M/L)            │                     │
│       │  quarterly_review (S/M/L)        │                     │
│       │  ...                             │                     │
│       └──────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Layout    │ │    Text     │ │  Analytics  │
│   Service   │ │   Service   │ │   Service   │
│             │ │             │ │             │
│ /layouts    │ │/capabilities│ │/capabilities│
│ /can-fit    │ │/can-handle  │ │/can-handle  │
└─────────────┘ └─────────────┘ └─────────────┘
```

### 5.2 Strawman Generation Flow (4-Step Process)

```
┌─────────────────────────────────────────────────────────────────┐
│                    STRAWMAN SERVICE (Enhanced)                  │
│                                                                 │
│  ╔══════════════════════════════════════════════════════════╗  │
│  ║  STEP 1: DETERMINE STORYLINE & MESSAGES                  ║  │
│  ╠══════════════════════════════════════════════════════════╣  │
│  ║  Deep thought + playbook matching:                       ║  │
│  ║  • Parse user prompt, extract presentation intent        ║  │
│  ║  • Determine overall storyline and narrative flow        ║  │
│  ║  • Generate high-level bullets for each slide            ║  │
│  ║  • Match against playbooks (if available)                ║  │
│  ║  • Output: slide_messages[] with purpose + message       ║  │
│  ║                                                          ║  │
│  ║  Example output:                                         ║  │
│  ║  {                                                       ║  │
│  ║    "storyline": "Q4 review showing growth and next steps"║  │
│  ║    "slides": [                                           ║  │
│  ║      {"purpose": "title", "message": "Q4 2024 Review"},  ║  │
│  ║      {"purpose": "metrics", "message": "3 key KPIs"},    ║  │
│  ║      {"purpose": "highlights", "message": "Top wins"}    ║  │
│  ║    ]                                                     ║  │
│  ║  }                                                       ║  │
│  ╚══════════════════════════════════════════════════════════╝  │
│                                                                 │
│  FOR EACH SLIDE (using messages from Step 1):                  │
│  ─────────────────────────────────────────────                 │
│                                                                 │
│  ╔══════════════════════════════════════════════════════════╗  │
│  ║  STEP 2: SELECT LAYOUT (work with Layout Service)        ║  │
│  ╠══════════════════════════════════════════════════════════╣  │
│  ║  Based on slide's purpose and message:                   ║  │
│  ║  • From playbook: use default layout based on fit        ║  │
│  ║  • OR call POST /recommend-layout → Layout Service       ║  │
│  ║  • GET /layouts/{id} → get content_zones with dimensions:║  │
│  ║    - title: {width: 1800, height: 80}                    ║  │
│  ║    - main_content: {width: 1800, height: 750}            ║  │
│  ║    - sub_zones: [{col_1: 560×750}, {col_2: 560×750}...]  ║  │
│  ╚══════════════════════════════════════════════════════════╝  │
│                                                                 │
│  ╔══════════════════════════════════════════════════════════╗  │
│  ║  STEP 3: SELECT CONTENT VARIANT (work with Content Svc)  ║  │
│  ╠══════════════════════════════════════════════════════════╣  │
│  ║  Based on layout's grid size:                            ║  │
│  ║  • POST /can-handle with available_space: 1800×750       ║  │
│  ║  • Services return: confidence + fits_well               ║  │
│  ║  • Winner = highest confidence that fits                 ║  │
│  ║  • POST /recommend-variant with available_space          ║  │
│  ║  • Service returns: variant + requires_space             ║  │
│  ╚══════════════════════════════════════════════════════════╝  │
│                                                                 │
│  ╔══════════════════════════════════════════════════════════╗  │
│  ║  STEP 4: REFINE & PERSONALIZE CONTENT                    ║  │
│  ╠══════════════════════════════════════════════════════════╣  │
│  ║  Based on variant selected and layout elements:          ║  │
│  ║  • Refine content to fit the variant                     ║  │
│  ║  • Map content to zones:                                 ║  │
│  ║    - title → slide title                                 ║  │
│  ║    - col_1, col_2, col_3 → topics[0], topics[1], ...     ║  │
│  ║  • Personalize based on user context                     ║  │
│  ║  • Output complete decision with reasons                 ║  │
│  ╚══════════════════════════════════════════════════════════╝  │
│                                                                 │
│  Output Complete Strawman                                      │
│  - Storyline summary from Step 1                               │
│  - Full slide sequence with all decisions made                 │
│  - Playbook ID (if used) or "per_slide_engine"                 │
│  - Personalized content mapping                                │
│  - Ready for user approval                                     │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Enhanced Strawman Output

```json
{
  "presentation_id": "uuid",
  "title": "Series A Pitch - Acme Corp",

  "playbook": {
    "id": "startup_pitch",
    "name": "Startup Pitch Deck",
    "variant": "medium",
    "duration_minutes": 30,
    "matched_confidence": 0.92,
    "matched_keywords": ["pitch", "series A", "investor"]
  },

  "slides": [
    {
      "slide_number": 1,
      "position_in_playbook": 1,
      "purpose": "title",
      "title": "Acme Corp - Revolutionizing Widget Manufacturing",
      "topics": [],

      "decisions": {
        "from_playbook": true,
        "layout": {
          "id": "H01",
          "series": "H",
          "validated_by": "layout-service"
        },
        "content": {
          "service": "text-service",
          "endpoint": "/v1.2/hero/title-with-image",
          "variant": null,
          "validated_by": "text-service"
        }
      }
    },
    {
      "slide_number": 2,
      "position_in_playbook": 2,
      "purpose": "problem",
      "title": "The Problem: Widget Manufacturing is Broken",
      "topics": [
        "Legacy systems waste 40% of materials",
        "Quality control is manual and error-prone",
        "Lead times are 3x longer than necessary"
      ],

      "decisions": {
        "from_playbook": true,
        "layout": {
          "id": "C01",
          "series": "C",
          "validated_by": "layout-service"
        },
        "content": {
          "service": "text-service",
          "endpoint": "/v1.2/generate",
          "variant": "comparison_3col",
          "validated_by": "text-service"
        }
      }
    },
    {
      "slide_number": 3,
      "position_in_playbook": 3,
      "purpose": "solution",
      "title": "Our Solution: AI-Powered Manufacturing",
      "topics": [
        "Real-time optimization reduces waste by 60%",
        "Automated QC catches 99.9% of defects",
        "Smart scheduling cuts lead time in half"
      ],

      "decisions": {
        "from_playbook": true,
        "layout": {
          "id": "C01",
          "series": "C",
          "validated_by": "layout-service"
        },
        "content": {
          "service": "text-service",
          "endpoint": "/v1.2/generate",
          "variant": "features_3col",
          "validated_by": "text-service"
        }
      }
    },
    {
      "slide_number": 4,
      "position_in_playbook": 4,
      "purpose": "market_size",
      "title": "Market Opportunity: $50B TAM",
      "topics": [
        "TAM: $50B global widget market",
        "SAM: $15B addressable in manufacturing",
        "SOM: $2B initial target segment"
      ],

      "decisions": {
        "from_playbook": true,
        "layout": {
          "id": "L02",
          "series": "L",
          "validated_by": "layout-service"
        },
        "content": {
          "service": "analytics-service",
          "endpoint": "/api/v1/analytics/L02/pie",
          "chart_type": "pie",
          "validated_by": "analytics-service"
        }
      }
    },
    {
      "slide_number": 7,
      "position_in_playbook": 7,
      "purpose": "traction",
      "title": "Traction: 10x Growth in 12 Months",
      "topics": [
        "Show MRR growth from $10K to $100K over 12 months"
      ],

      "decisions": {
        "from_playbook": true,
        "layout": {
          "id": "L02",
          "series": "L",
          "validated_by": "layout-service"
        },
        "content": {
          "service": "analytics-service",
          "endpoint": "/api/v1/analytics/L02/line",
          "chart_type": "line",
          "validated_by": "analytics-service"
        }
      }
    },
    {
      "slide_number": 10,
      "position_in_playbook": 10,
      "purpose": "ask",
      "title": "The Ask: $5M Series A",
      "topics": [
        "Raising $5M at $25M pre-money",
        "Use of funds: Engineering (60%), Sales (30%), Ops (10%)",
        "Contact: founder@acme.com"
      ],

      "decisions": {
        "from_playbook": true,
        "layout": {
          "id": "H03",
          "series": "H",
          "validated_by": "layout-service"
        },
        "content": {
          "service": "text-service",
          "endpoint": "/v1.2/hero/closing-with-image",
          "variant": null,
          "validated_by": "text-service"
        }
      }
    }
  ],

  "coordination_log": [
    {"action": "playbook_match", "playbook": "startup_pitch", "confidence": 0.92},
    {"action": "variant_selected", "variant": "medium", "duration": 30},
    {"action": "sequence_generated", "slide_count": 10},
    {"action": "layout_validation", "all_passed": true},
    {"action": "service_validation", "all_passed": true}
  ]
}
```

---

## 6. Service Capabilities (Supporting Infrastructure)

### 6.1 Why Services Still Need /capabilities

Even with playbooks, services expose capabilities so:
1. **Strawman validates** playbook decisions against current service state
2. **Fallback scenarios** when no playbook matches
3. **Services can proactively recommend** better alternatives
4. **New services** can be integrated without playbook changes

### 6.2 Validation Endpoints (with Grid Size)

**Layout Service: `POST /can-fit`**
```json
// Validate playbook's layout choice
{
  "layout_id": "C01",
  "content_zones_needed": 3,
  "content_type": "text"
}

// Response
{
  "can_fit": true,
  "suggested_layout": null
}
```

**Content Services: `POST /can-handle`**
```json
// Validate playbook's variant choice
{
  "topics": ["Point 1", "Point 2", "Point 3"],
  "variant_id": "comparison_3col",
  "layout_id": "C01"
}

// Response
{
  "can_handle": true,
  "confidence": 0.92,
  "suggested_variant": null
}
```

### 6.3 Proactive Recommendations

Content services can suggest better options:

```json
{
  "can_handle": true,
  "confidence": 0.65,
  "variant_id": "comparison_3col",
  "suggested_variant": "metrics_3col",
  "suggestion_confidence": 0.92,
  "reason": "Content has KPI metrics - metrics_3col would be better"
}
```

Strawman can accept or stick with playbook.

---

## 7. Implementation Phases

> **See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for detailed team assignments and timeline.**

### Phase 1: Service Capabilities (Foundation)

**Goal**: All services expose `/capabilities` endpoint

**Owner**: All Service Teams

**Tasks**:
- Layout Service: `GET /capabilities`, `GET /api/layouts`
- Text Service: `GET /capabilities`
- Analytics Service: `GET /capabilities`
- Illustrator: `GET /capabilities`
- Diagram Service: `GET /capabilities`

**Outcome**: Strawman knows what each service can do

---

### Phase 2: Content Negotiation (Service Routing)

**Goal**: Services answer "can you handle this content?"

**Owner**: All Content Service Teams

**Tasks**:
- All content services implement `POST /can-handle`
- Return confidence scores (0-1)
- Strawman queries all services, picks highest confidence

**Outcome**: Intelligent service routing based on content

---

### Phase 3: Variant & Layout Recommendation

**Goal**: Services recommend specific variants/layouts

**Owner**: All Service Teams

**Tasks**:
- Text Service: `POST /recommend-variant`
- Analytics Service: `POST /recommend-chart`
- Illustrator: `POST /recommend-visual`
- Diagram Service: `POST /recommend-diagram`
- Layout Service: `POST /recommend-layout`, `POST /can-fit`

**Outcome**: Services recommend decisions, not Strawman guessing

---

### Phase 4: Per-Slide Decision Engine (MILESTONE)

**Goal**: Strawman makes ALL decisions at generation time

**Owner**: Director Team

**Tasks**:
- Build content analyzer (extract topics, keywords, patterns)
- Integrate service routing (Phase 2)
- Integrate recommendations (Phase 3)
- Assemble complete strawman with all decisions

**Outcome**: **Working system without playbooks**

---

### Phase 5: Playbook Layer (Enhancement)

**Goal**: Add presentation-level playbooks as optimization

**Owner**: Director Team

**Tasks**:
1. Define playbook JSON schema
2. Create first 3 playbooks:
   - `startup_pitch` (most requested)
   - `quarterly_review` (common internal use)
   - `educational` (training use case)
3. Build playbook matching logic in Strawman
4. Implement S/M/L variant selection
5. Per-slide engine becomes fallback

**Outcome**: ~40% of presentations match a playbook

---

### Phase 6: Expansion & Optimization

**Goal**: Continuous improvement

**Tasks**:
1. Add playbooks 4-10 (see section 3)
2. Track match rate and user satisfaction
3. Theme integration (C-series/H-series preference)
4. Iterate based on usage data

**Outcome**: 70%+ playbook match, 90%+ user satisfaction

---

## 8. Playbook Registry

### 8.1 Storage Location

```
director_agent/v5.0/
├── playbooks/
│   ├── registry.json           # Index of all playbooks
│   ├── startup_pitch.json
│   ├── educational.json
│   ├── rfp_response.json
│   ├── quarterly_review.json
│   ├── product_launch.json
│   ├── sales_pitch.json
│   ├── project_proposal.json
│   ├── training_workshop.json
│   ├── company_overview.json
│   └── status_update.json
```

### 8.2 Registry Index

```json
{
  "version": "1.0",
  "playbooks": [
    {
      "id": "startup_pitch",
      "file": "startup_pitch.json",
      "priority": 1,
      "enabled": true,
      "match_rate": 0.15
    },
    {
      "id": "quarterly_review",
      "file": "quarterly_review.json",
      "priority": 2,
      "enabled": true,
      "match_rate": 0.20
    }
  ],
  "fallback_behavior": "ai_generated_structure"
}
```

---

## 9. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Playbook match rate | 0% | 70%+ |
| User accepts playbook structure | N/A | 85%+ |
| Decisions at strawman time | 0% | 100% |
| Time to first slide | ~30s | ~20s |
| User edits to structure | ~40% | <15% |
| Presentation quality score | ~7/10 | 9/10 |

---

## 10. Questions for Review

1. **First Playbooks**: Which 3 playbooks should we build first?
   - Suggested: `startup_pitch`, `quarterly_review`, `educational`

2. **Duration Selection**: Should Strawman auto-detect duration from prompt, or always ask user?

3. **Playbook Override**: If user doesn't like playbook structure, can they:
   - Switch to different playbook?
   - Fall back to AI-generated?
   - Edit individual positions?

4. **Hybrid Approach**: For presentations that partially match a playbook, should we use partial playbook + AI for rest?

5. **Playbook Evolution**: How do we version playbooks when we improve them?

---

## 11. Appendix: Full Playbook Example

### startup_pitch.json

```json
{
  "playbook_id": "startup_pitch",
  "name": "Startup Pitch Deck",
  "version": "1.0",
  "description": "Classic investor pitch deck structure for fundraising",

  "use_cases": [
    "Seed round pitch to angels",
    "Series A/B pitch to VCs",
    "Demo day presentation",
    "Investor update meeting"
  ],

  "triggers": {
    "keywords": [
      "pitch", "investor", "funding", "fundraise", "startup",
      "seed", "series A", "series B", "VC", "angel",
      "demo day", "raise", "investment"
    ],
    "patterns": [
      "pitch deck",
      "investor presentation",
      "fundraising deck",
      "raise.*round"
    ],
    "exclude_keywords": ["status update", "quarterly", "training"]
  },

  "variants": {
    "small": {
      "name": "Quick Pitch",
      "duration_minutes": 15,
      "use_for": "Demo day, elevator pitch, initial meeting",
      "slide_count_range": [5, 7],

      "sequence": [
        {
          "position": 1,
          "purpose": "title",
          "purpose_description": "Company name, tagline, visual hook",
          "slide_type": "hero",
          "required": true,
          "layout": {
            "preferred": "H01",
            "fallback": "L29",
            "series_preference": ["H", "L"]
          },
          "content": {
            "service": "text-service",
            "endpoint": "/v1.2/hero/title-with-image"
          },
          "content_guidance": "Company name prominently displayed, compelling tagline, relevant background image"
        },
        {
          "position": 2,
          "purpose": "problem",
          "purpose_description": "Pain points the market faces",
          "slide_type": "content",
          "required": true,
          "layout": {
            "preferred": "C01",
            "fallback": "L25",
            "series_preference": ["C", "L"]
          },
          "content": {
            "service": "text-service",
            "endpoint": "/v1.2/generate",
            "variant": "comparison_3col"
          },
          "content_guidance": "3 major pain points, quantify impact where possible",
          "topic_count_range": [3, 3]
        },
        {
          "position": 3,
          "purpose": "solution",
          "purpose_description": "How your product solves the problem",
          "slide_type": "content",
          "required": true,
          "layout": {
            "preferred": "C01",
            "fallback": "L25",
            "series_preference": ["C", "L"]
          },
          "content": {
            "service": "text-service",
            "endpoint": "/v1.2/generate",
            "variant": "features_3col"
          },
          "content_guidance": "3 key solution aspects mapped to problem points",
          "topic_count_range": [3, 3]
        },
        {
          "position": 4,
          "purpose": "product",
          "purpose_description": "Key features and benefits",
          "slide_type": "content",
          "required": true,
          "layout": {
            "preferred": "L25",
            "fallback": "L25",
            "series_preference": ["L"]
          },
          "content": {
            "service": "text-service",
            "endpoint": "/v1.2/generate",
            "variant": "features_benefits"
          },
          "content_guidance": "Product screenshots or feature highlights",
          "topic_count_range": [3, 4]
        },
        {
          "position": 5,
          "purpose": "traction",
          "purpose_description": "Growth metrics and validation",
          "slide_type": "chart",
          "required": true,
          "layout": {
            "preferred": "L02",
            "fallback": "L02",
            "series_preference": ["L"]
          },
          "content": {
            "service": "analytics-service",
            "endpoint": "/api/v1/analytics/L02/line",
            "chart_type": "line"
          },
          "content_guidance": "Hockey stick growth, MRR, users, or key metric over time"
        },
        {
          "position": 6,
          "purpose": "ask",
          "purpose_description": "Funding ask and next steps",
          "slide_type": "hero",
          "required": true,
          "layout": {
            "preferred": "H03",
            "fallback": "L29",
            "series_preference": ["H", "L"]
          },
          "content": {
            "service": "text-service",
            "endpoint": "/v1.2/hero/closing-with-image"
          },
          "content_guidance": "Clear ask amount, contact info, call to action"
        }
      ]
    },

    "medium": {
      "name": "Standard Pitch",
      "duration_minutes": 30,
      "use_for": "VC meeting, partner pitch, detailed presentation",
      "slide_count_range": [10, 12],

      "sequence": [
        {
          "position": 1,
          "purpose": "title",
          "slide_type": "hero",
          "required": true,
          "layout": {"preferred": "H01", "fallback": "L29"},
          "content": {"service": "text-service", "endpoint": "/v1.2/hero/title-with-image"}
        },
        {
          "position": 2,
          "purpose": "problem",
          "slide_type": "content",
          "required": true,
          "layout": {"preferred": "C01", "fallback": "L25"},
          "content": {"service": "text-service", "variant": "comparison_3col"}
        },
        {
          "position": 3,
          "purpose": "solution",
          "slide_type": "content",
          "required": true,
          "layout": {"preferred": "C01", "fallback": "L25"},
          "content": {"service": "text-service", "variant": "features_3col"}
        },
        {
          "position": 4,
          "purpose": "market_size",
          "purpose_description": "TAM/SAM/SOM breakdown",
          "slide_type": "chart",
          "required": true,
          "layout": {"preferred": "L02", "fallback": "L02"},
          "content": {"service": "analytics-service", "chart_type": "pie"},
          "content_guidance": "TAM, SAM, SOM with dollar amounts"
        },
        {
          "position": 5,
          "purpose": "product",
          "slide_type": "content",
          "required": true,
          "layout": {"preferred": "L25", "fallback": "L25"},
          "content": {"service": "text-service", "variant": "features_benefits"}
        },
        {
          "position": 6,
          "purpose": "business_model",
          "purpose_description": "How you make money",
          "slide_type": "content",
          "required": true,
          "layout": {"preferred": "C03", "fallback": "L25"},
          "content": {"service": "text-service", "variant": "metrics_4col"},
          "content_guidance": "Revenue streams, pricing, unit economics"
        },
        {
          "position": 7,
          "purpose": "traction",
          "slide_type": "chart",
          "required": true,
          "layout": {"preferred": "L02", "fallback": "L02"},
          "content": {"service": "analytics-service", "chart_type": "line"}
        },
        {
          "position": 8,
          "purpose": "team",
          "purpose_description": "Founding team and key hires",
          "slide_type": "content",
          "required": true,
          "layout": {"preferred": "L25", "fallback": "L25"},
          "content": {"service": "text-service", "variant": "grid_2x3"},
          "content_guidance": "Founder photos, titles, relevant experience"
        },
        {
          "position": 9,
          "purpose": "financials",
          "purpose_description": "Financial projections",
          "slide_type": "chart",
          "required": false,
          "layout": {"preferred": "L02", "fallback": "L02"},
          "content": {"service": "analytics-service", "chart_type": "bar_grouped"},
          "content_guidance": "3-year revenue projection"
        },
        {
          "position": 10,
          "purpose": "ask",
          "slide_type": "hero",
          "required": true,
          "layout": {"preferred": "H03", "fallback": "L29"},
          "content": {"service": "text-service", "endpoint": "/v1.2/hero/closing-with-image"}
        }
      ]
    },

    "large": {
      "name": "Deep Dive Pitch",
      "duration_minutes": 60,
      "use_for": "Board meeting, due diligence, comprehensive pitch",
      "slide_count_range": [18, 25],

      "sequence": [
        {"position": 1, "purpose": "title"},
        {"position": 2, "purpose": "agenda"},
        {"position": 3, "purpose": "problem"},
        {"position": 4, "purpose": "problem_deep_dive"},
        {"position": 5, "purpose": "solution"},
        {"position": 6, "purpose": "solution_details"},
        {"position": 7, "purpose": "market_size"},
        {"position": 8, "purpose": "market_dynamics"},
        {"position": 9, "purpose": "product"},
        {"position": 10, "purpose": "product_roadmap"},
        {"position": 11, "purpose": "technology"},
        {"position": 12, "purpose": "business_model"},
        {"position": 13, "purpose": "go_to_market"},
        {"position": 14, "purpose": "competition"},
        {"position": 15, "purpose": "traction"},
        {"position": 16, "purpose": "case_studies"},
        {"position": 17, "purpose": "team"},
        {"position": 18, "purpose": "advisors"},
        {"position": 19, "purpose": "financials"},
        {"position": 20, "purpose": "use_of_funds"},
        {"position": 21, "purpose": "risks"},
        {"position": 22, "purpose": "milestones"},
        {"position": 23, "purpose": "ask"},
        {"position": 24, "purpose": "appendix_section"},
        {"position": 25, "purpose": "contact"}
      ]
    }
  },

  "validation": {
    "require_layout_validation": true,
    "require_service_validation": true,
    "accept_service_suggestions": true
  }
}
```

---

*Document Version: 7.0*
*Author: Director Agent Architecture*
*Date: December 2024*
*Updates:*
- *v7.0: Added Layout-SlideType-Variant constraint hierarchy (layouts constrain available slide types and variants)*
- *v6.0: Changed to 4-Step Process - added Step 1 (Storyline & Messages) before layout selection*
- *v5.0: Added 3-Step Strawman Process with grid size as foundational parameter*
- *v4.0: Aligned phases with IMPLEMENTATION_PLAN.md, emphasized per-slide engine first*
- *v3.0: Presentation-level playbooks with S/M/L time-based variants*
- *v2.0: Strawman-coordinated architecture*

*Related: [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md), [SERVICE_CAPABILITIES_SPEC.md](./SERVICE_CAPABILITIES_SPEC.md)*
