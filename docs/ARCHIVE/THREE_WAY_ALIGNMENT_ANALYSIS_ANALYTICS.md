# Analytics Service v3.0 - Three-Way Alignment Analysis

## Summary

This document analyzes alignment between THREE documents:
1. **ANALYTICS_SERVICE_CAPABILITIES.md** - What Analytics Service offers
2. **SERVICE_REQUIREMENTS_ANALYTICS.md** - What Director expects from Analytics Service
3. **SLIDE_GENERATION_INPUT_SPEC.md** - What Layout Service expects (**SOURCE OF TRUTH**)

**Analysis Date**: December 2024
**Last Updated**: December 2024 (v3.0 Aliases Added)
**Status**: ✅ **FULLY ALIGNED** - All layouts now have spec-compliant field aliases

---

## Quick Reference: Alignment Status

| Layout | Analytics Service | Director Mapping | Layout Service | Status |
|--------|------------------|------------------|----------------|--------|
| C3-chart | ✅ `chart_html` (alias) | ✅ Direct use | ✅ | **ALIGNED** |
| V2-chart-text | ✅ `chart_html`, `body` (aliases) | ✅ Direct use | ✅ | **ALIGNED** |
| L02 | ✅ `element_4`, `element_2` (aliases) | ✅ Direct use | ✅ | **ALIGNED** |

### v3.0 Field Aliases (NEW)

Analytics Service v3.0 now provides SPEC-compliant field aliases in all responses:

| Original Field | New Alias | Used By Layouts |
|----------------|-----------|-----------------|
| `element_3` | `chart_html` | C3-chart, V2-chart-text |
| `element_3` | `element_4` | L02 (SPEC requires element_4) |
| `element_2` | `body` | V2-chart-text |

Original fields are preserved for backward compatibility.

---

## Detailed Analysis by Layout Type

### C3-chart (Single Chart)

**Layout Service SPEC (lines 658-704)**:
```json
{
  "layout": "C3-chart",
  "content": {
    "slide_title": "<h2>Revenue Growth</h2>",      // REQUIRED - Director via Text Service
    "subtitle": "<p>FY 2024 Results</p>",          // Optional - Director via Text Service
    "chart_html": "<canvas>...</canvas><script>...</script>"  // REQUIRED - Analytics provides
  },
  "background_color": "#ffffff",                   // Optional - Director provides default
  "background_image": "https://..."                // Optional - Director provides if needed
}
```

**Analytics SERVICE_REQUIREMENTS (lines 43-54)**:
- Returns `element_3` for chart HTML
- Director maps `element_3` → `chart_html`
- Works correctly ✅

**Analytics Service CAPABILITIES (Part 3.1)**:
- Returns `content.element_3`: Complete chart HTML with Canvas/SVG and script
- Returns `content.element_2`: AI-generated insights (not used for C3)
- Does NOT generate: `slide_title`, `subtitle`, `background_color`

**STATUS**: ✅ **FULLY ALIGNED**

**Data Flow**:
```
Director              Analytics Service          Director Mapping         Layout Service
────────              ─────────────────          ────────────────         ──────────────
1. Calls Analytics    2. Returns element_3       3. Maps to chart_html    4. Renders chart
   with narrative     (canvas + script)          Adds title/subtitle
                                                 from Text Service
```

---

### V2-chart-text (Chart + Insights)

**Layout Service SPEC (lines 706-747)**:
```json
{
  "layout": "V2-chart-text",
  "content": {
    "slide_title": "<h2>Performance Analysis</h2>",   // REQUIRED - Director via Text Service
    "subtitle": "<p>Q4 Metrics</p>",                  // Optional - Director via Text Service
    "chart_html": "<canvas>...</canvas>",             // REQUIRED - Left panel (1080x840px)
    "body": "<ul><li>+25% revenue</li>...</ul>"       // Optional - Right panel (720x840px)
  },
  "background_color": "#ffffff"
}
```

**Analytics SERVICE_REQUIREMENTS (lines 56-68, 93)**:
- Returns `element_3` for chart HTML
- Returns `element_2` for insights text
- Director maps:
  - `element_3` → `chart_html`
  - `element_2` → `body`
- Works correctly ✅

**Analytics Service CAPABILITIES (Part 3.1)**:
- Returns `content.element_3`: Chart HTML (1080×840px)
- Returns `content.element_2`: AI-generated insights HTML
- Does NOT generate: `slide_title`, `subtitle`

**STATUS**: ✅ **FULLY ALIGNED**

**Data Flow**:
```
Analytics Response          Director Mapping              Layout Service
──────────────────          ────────────────              ──────────────
element_3 (chart)       →   chart_html                →   Left panel (1080×840)
element_2 (insights)    →   body                      →   Right panel (720×840)
                            + slide_title (Text Service)
                            + subtitle (Text Service)
```

---

### L02 (Left Diagram with Text Right)

**Layout Service SPEC (lines 749-778)**:
```json
{
  "layout": "L02",
  "content": {
    "slide_title": "System Architecture",         // Optional
    "element_1": "Architecture Overview",         // Optional - subtitle equivalent
    "element_4": "<div class='diagram-container'>...</div>",  // Diagram/chart slot
    "element_2": "<ul><li>Component A</li>...</ul>"           // Text slot
  },
  "background_color": "#ffffff"
}
```

**Analytics v3.0 Response (With Aliases)**:
```json
{
  "content": {
    "element_3": "...",   // Legacy - still available
    "element_4": "...",   // ✅ NEW v3.0 Alias - SPEC compliant
    "element_2": "..."    // Observations - matches SPEC
  }
}
```

**STATUS**: ✅ **FULLY ALIGNED** (v3.0 aliases resolve previous mismatch)

**Field Alignment**:
```
Analytics v3.0 Returns      Layout Service Expects        Status
──────────────────────      ──────────────────────        ──────
element_4 (alias)           element_4 (diagram)           ✅ ALIGNED
element_2 (insights)        element_2 (text)              ✅ ALIGNED
(not generated)             element_1 (subtitle)          ℹ️ Optional
(not generated)             slide_title                   ℹ️ Director provides
```

**Resolution**: Analytics v3.0 now returns `element_4` as an alias for `element_3`, matching SPEC exactly.

---

## Fields NOT Generated by Analytics Service

Analytics Service is responsible for chart content only. Director must generate or provide:

| Field | Source | Default |
|-------|--------|---------|
| `slide_title` | Text Service `/api/ai/slide/title` | Required |
| `subtitle` | Text Service `/api/ai/slide/subtitle` | Optional |
| `background_color` | Director provides | `#ffffff` |
| `background_image` | Director provides | None |
| `element_1` (L02) | Director or Text Service | Optional |

**This is confirmed correct** per SERVICE_REQUIREMENTS_ANALYTICS.md (line 96):
> "Analytics does NOT generate `slide_title` or `subtitle`. Director generates these via Text Service."

---

## Grid System Alignment

### Layout Dimensions (from SLIDE_GENERATION_INPUT_SPEC)

| Layout | Chart Area Grid | Chart Area Pixels | Text Area |
|--------|-----------------|-------------------|-----------|
| **C3-chart** | rows 4-18, cols 2-32 | 1800 × 840 px | - |
| **V2-chart-text** | rows 4-18, cols 2-20 | 1080 × 840 px | 720 × 840 px |
| **L02** | rows 5-17, cols 2-23 | 1260 × 720 px | 540 × 720 px |

### Core Constants

| Property | Value |
|----------|-------|
| Slide Resolution | 1920 × 1080 px |
| Grid Columns | 32 |
| Grid Rows | 18 |
| Cell Size | 60 × 60 px |

**Analytics Service ALIGNMENT**: ✅ Grid dimensions documented in ANALYTICS_SERVICE_CAPABILITIES.md Appendix D match SPEC.

---

## Response Structure Comparison

### Analytics Service v3.0 Returns (With Aliases):
```json
{
  "content": {
    // Original fields (kept for backward compatibility)
    "element_3": "<canvas id='chart_abc'>...</canvas><script>...</script>",
    "element_2": "<div class='insights'>...</div>",

    // NEW v3.0 Aliases (SPEC-compliant)
    "chart_html": "<canvas id='chart_abc'>...</canvas><script>...</script>",
    "element_4": "<canvas id='chart_abc'>...</canvas><script>...</script>",
    "body": "<div class='insights'>...</div>"
  },
  "metadata": {
    "service": "analytics_v3",
    "chart_type": "line",
    "data_source": "director",
    "synthetic_data_used": false,
    "generation_time_ms": 1250
  }
}
```

### Layout Service Expects (Nested with slide-level fields):
```json
{
  "layout": "C3-chart",
  "content": {
    "slide_title": "...",
    "subtitle": "...",
    "chart_html": "..."
  },
  "background_color": "#ffffff"
}
```

**Resolution**: With v3.0 aliases, Director responsibilities are simplified:
1. ~~Mapping field names~~ ✅ Analytics now provides spec-compliant aliases
2. Adding title/subtitle from Text Service (unchanged)
3. Adding slide-level fields (`background_color`) (unchanged)
4. Restructuring into Layout Service format (unchanged)

Director's `LayoutPayloadAssembler` prioritizes aliases but falls back to original fields for compatibility.

---

## Issues Identified (RESOLVED)

### Issue 1: L02 Element Slot Naming ✅ RESOLVED

**Previous Issue**: SPEC required `element_4` for L02 diagram slot, but Analytics returned `element_3`.

**Resolution**: Analytics v3.0 now includes `element_4` as an alias for `element_3`.

```json
// Analytics v3.0 Response
{
  "content": {
    "element_3": "...",  // Legacy - still available
    "element_4": "...",  // ✅ NEW - SPEC compliant
    "element_2": "..."
  }
}
```

---

### Issue 2: Supported Layouts Discrepancy ✅ CLARIFIED

**Analytics CAPABILITIES** claims support for: `L01, L02, L03`

**SLIDE_GENERATION_INPUT_SPEC** assigns to Analytics: `C3-chart, V2-chart-text, L02`

**Clarification**: L01, L02, L03 are internal Analytics layout codes. C3-chart and V2-chart-text are Director-facing layout names that map to internal codes:

```
Analytics Internal    Director/Layout Service
──────────────────    ──────────────────────
L01                   (internal use)
L02                   L02 (shared name)
L03                   (internal use)
(generated)           C3-chart
(generated)           V2-chart-text
```

This is working as designed.

---

## Summary: What Needs to Happen

### Analytics Service - ✅ COMPLETE

- [x] Returns `element_3` for chart HTML
- [x] Returns `element_2` for insights HTML
- [x] Returns metadata with chart_type, data_source
- [x] Documentation complete in ANALYTICS_SERVICE_CAPABILITIES.md
- [x] ✅ **DONE**: `chart_html`, `element_4`, `body` aliases added in v3.0

### Director Agent - ✅ COMPLETE

- [x] ✅ L02 mapping handles `element_4` directly (v4.4 LayoutPayloadAssembler)
- [x] ✅ Title/subtitle generated via Text Service for all chart layouts
- [x] ✅ SERVICE_REQUIREMENTS_ANALYTICS.md updated to v2.0 (FULLY ALIGNED)

### Layout Service - NO CHANGES NEEDED

- SLIDE_GENERATION_INPUT_SPEC.md is the canonical reference
- Analytics + Director responses comply with this spec

---

## Implementation Status

### L02 Layout - ✅ VERIFIED

Director's LayoutPayloadAssembler (v4.4) handles L02 correctly:
```python
# LayoutPayloadAssembler._assemble_l02()
def _assemble_l02(self, slide_title, content):
    return {
        "content": {
            "slide_title": slide_title or "",
            "element_1": content.get("element_1", ""),
            "element_2": content.get("element_2", ""),
            # v4.4: Analytics v3.0 returns element_4 directly (SPEC-compliant)
            "element_4": content.get("element_4") or content.get("element_3", "")
        }
    }
```

### Analytics v3.0 Aliases - ✅ IMPLEMENTED

Analytics now provides all spec-compliant aliases:
```python
# Analytics v3.0 response builder
response = {
    "content": {
        # Original fields (keep for compatibility)
        "element_3": chart_html,
        "element_2": insights_html,

        # NEW v3.0 aliases (SPEC-compliant)
        "chart_html": chart_html,   # For C3-chart, V2-chart-text
        "element_4": chart_html,    # For L02 diagram slot
        "body": insights_html       # For V2-chart-text
    },
    "metadata": {...}
}
```

**Benefit**: Director can use fields directly without mapping

---

## SPEC Compliance Checklist

| Layout | Chart Field | Text Field | Title/Subtitle | Background |
|--------|-------------|------------|----------------|------------|
| C3-chart | ✅ `chart_html` (direct) | N/A | ✅ Text Service | ✅ Director provides |
| V2-chart-text | ✅ `chart_html` (direct) | ✅ `body` (direct) | ✅ Text Service | ✅ Director provides |
| L02 | ✅ `element_4` (direct) | ✅ `element_2` (direct) | ✅ Text Service | ✅ Director provides |

**All layouts now use spec-compliant field names directly from Analytics v3.0 responses.**

---

## Data Flow Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                          DIRECTOR AGENT                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Receives storyline with chart content                        │
│     ↓                                                            │
│  2. Calls /api/v1/analytics/can-handle (confidence check)        │
│     ↓                                                            │
│  3. Calls /api/v1/analytics/recommend-chart (get chart type)     │
│     ↓                                                            │
│  4. Calls Analytics: POST /api/v1/analytics/{layout}/{type}      │
│     ↓                                                            │
│  5. Calls Text Service: /api/ai/slide/title, /api/ai/slide/subtitle│
│     ↓                                                            │
│  6. LayoutPayloadAssembler maps fields:                          │
│     - element_3 → chart_html (C3/V2) or element_4 (L02)          │
│     - element_2 → body (V2) or element_2 (L02)                   │
│     - Adds slide_title, subtitle                                 │
│     - Adds background_color                                      │
│     ↓                                                            │
│  7. Sends to Layout Service                                       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ Analytics       │         │ Text Service    │         │ Layout Service  │
│ Service         │         │                 │         │                 │
├─────────────────┤         ├─────────────────┤         ├─────────────────┤
│ Returns:        │         │ Returns:        │         │ Expects:        │
│ - element_3     │    +    │ - slide_title   │    =    │ - chart_html    │
│ - element_2     │         │ - subtitle      │         │ - body          │
│ - metadata      │         │                 │         │ - slide_title   │
│                 │         │                 │         │ - subtitle      │
│                 │         │                 │         │ - background_*  │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

---

## Related Documents

| Document | Location | Purpose |
|----------|----------|---------|
| ANALYTICS_SERVICE_CAPABILITIES.md | `/director_agent/v4.0/docs/` | Analytics Service API Reference |
| SERVICE_REQUIREMENTS_ANALYTICS.md | `/director_agent/v4.0/docs/` | Director → Analytics Contract |
| SLIDE_GENERATION_INPUT_SPEC.md | `/director_agent/v4.0/docs/` | Layout Service Input Spec (SOURCE OF TRUTH) |
| THREE_WAY_ALIGNMENT_ANALYSIS.md | `/director_agent/v4.0/docs/` | Text Service Alignment Analysis |

---

---

## Version History

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| 1.1 | Dec 2024 | ✅ FULLY ALIGNED | Analytics v3.0 aliases added |
| 1.0 | Dec 2024 | ⚠️ Partial | Initial analysis, L02 needed verification |

*This analysis was generated December 2024 as part of Analytics Service v3.0 Director integration work.*
*Updated December 2024 to reflect Analytics v3.0 field aliases.*
