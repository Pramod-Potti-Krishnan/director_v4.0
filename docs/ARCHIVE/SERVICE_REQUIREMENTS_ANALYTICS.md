# Analytics Service - Director Integration Requirements

**Version**: 2.0
**Date**: December 2024
**Priority**: LOW (was MEDIUM)
**Status**: ✅ **FULLY ALIGNED** - Analytics provides spec-compliant field names directly

## Summary

Director Agent v4.4 coordinates with Analytics Service v3.0 for chart generation.

**v2.0 Update**: Analytics Service now provides field aliases that match Layout Service SPEC exactly. Director's `LayoutPayloadAssembler` no longer needs to perform field mapping - responses can be used directly.

---

## Analytics v3.0 Response Format (With Aliases)

### Endpoint: `POST /api/v1/analytics/{layout}/{analytics_type}`

```json
{
  "content": {
    // Original fields (kept for backward compatibility)
    "element_3": "<canvas id='chart_abc'>...</canvas><script>new Chart(...)</script>",
    "element_2": "<div class='insights'><ul><li>Revenue grew 25%</li>...</ul></div>",

    // NEW v3.0 Aliases (SPEC-compliant)
    "chart_html": "<canvas id='chart_abc'>...</canvas><script>new Chart(...)</script>",
    "element_4": "<canvas id='chart_abc'>...</canvas><script>new Chart(...)</script>",
    "body": "<div class='insights'><ul><li>Revenue grew 25%</li>...</ul></div>"
  },
  "metadata": {
    "service": "analytics_v3",
    "chart_type": "bar_vertical",
    "data_source": "director" | "synthetic",
    "synthetic_data_used": true | false,
    "generation_time_ms": 1250
  }
}
```

### Field Alias Reference

| New Alias | Value | Use For | SPEC Compliance |
|-----------|-------|---------|-----------------|
| `chart_html` | Same as `element_3` | C3-chart, V2-chart-text | ✅ Direct use |
| `element_4` | Same as `element_3` | L02 layout | ✅ Direct use |
| `body` | Same as `element_2` | V2-chart-text | ✅ Direct use |

---

## Layout Service Requirements (All ALIGNED)

### For C3-chart Layout

```json
{
  "layout": "C3-chart",
  "content": {
    "slide_title": "<h2>Revenue Growth</h2>",
    "subtitle": "<p>FY 2024 Results</p>",
    "chart_html": "..."  // ✅ Analytics provides directly
  }
}
```

### For V2-chart-text Layout

```json
{
  "layout": "V2-chart-text",
  "content": {
    "slide_title": "<h2>Performance Analysis</h2>",
    "subtitle": "<p>Q4 Metrics</p>",
    "chart_html": "...",  // ✅ Analytics provides directly
    "body": "..."         // ✅ Analytics provides directly
  }
}
```

### For L02 Layout

```json
{
  "layout": "L02",
  "content": {
    "slide_title": "System Architecture",
    "element_1": "Architecture Overview",
    "element_4": "...",   // ✅ Analytics provides directly (was element_3)
    "element_2": "..."    // ✅ Analytics provides directly
  }
}
```

---

## Alignment Status

| Layout | Chart Field | Text Field | Status |
|--------|-------------|------------|--------|
| C3-chart | `chart_html` ✅ | N/A | **ALIGNED** |
| V2-chart-text | `chart_html` ✅ | `body` ✅ | **ALIGNED** |
| L02 | `element_4` ✅ | `element_2` ✅ | **ALIGNED** |

**Note**: Analytics does NOT generate `slide_title` or `subtitle`. Director generates these via Text Service.

---

## Director Integration (v4.4)

### LayoutPayloadAssembler

The assembler prioritizes spec-compliant fields and falls back to legacy for compatibility:

```python
# C3-chart / V2-chart-text
chart_html = content.get("chart_html") or content.get("element_3", "")

# V2-chart-text body
body = content.get("body") or content.get("element_2", "")

# L02 diagram slot
element_4 = content.get("element_4") or content.get("element_3", "")
```

### Backward Compatibility

Original `element_3` and `element_2` fields are preserved, ensuring existing integrations continue to work.

---

## Field Reference

### Input Fields (Director → Analytics)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `narrative` | string | Yes | User's narrative about what to visualize |
| `chart_type` | string | Yes | One of 18 supported chart types |
| `layout` | string | Yes | L01, L02, or L03 |
| `data` | array | No | Data points (auto-generates if missing) |
| `context` | object | No | Presentation context for LLM |

### Output Fields (Analytics → Director)

| Field | Type | Description |
|-------|------|-------------|
| `content.chart_html` | HTML | ✅ **NEW** Chart HTML (alias for element_3) |
| `content.body` | HTML | ✅ **NEW** Observations/insights (alias for element_2) |
| `content.element_4` | HTML | ✅ **NEW** L02 diagram slot (alias for element_3) |
| `content.element_3` | HTML | Chart HTML (legacy, still available) |
| `content.element_2` | HTML | Insights HTML (legacy, still available) |
| `metadata.chart_type` | string | Actual chart type used |
| `metadata.synthetic_data_used` | boolean | Whether synthetic data was generated |

---

## Supported Chart Types

Analytics v3.0 supports 18 chart types:

**Chart.js (14 types)**:
- line, bar_vertical, bar_horizontal, pie, doughnut
- scatter, bubble, radar, polar_area, area
- bar_grouped, bar_stacked, area_stacked, mixed

**D3.js (4 types)**:
- d3_treemap, d3_sunburst, d3_choropleth_usa, d3_sankey

---

## Integration Notes

1. **Title/Subtitle Generation**: Director generates these via Text Service, not Analytics
2. **Data Strategy**: Analytics auto-generates synthetic data if none provided
3. **Field Priority**: Director uses spec-compliant aliases first, legacy fields as fallback
4. **No Mapping Required**: Analytics v3.0 aliases eliminate Director field mapping

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | Dec 2024 | Analytics v3.0 aliases - FULLY ALIGNED |
| 1.0 | Dec 2024 | Initial - Director handles field mapping |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `THREE_WAY_ALIGNMENT_ANALYSIS_ANALYTICS.md` | Detailed alignment analysis |
| `ANALYTICS_SERVICE_CAPABILITIES.md` | Analytics Service API Reference |
| `SLIDE_GENERATION_INPUT_SPEC.md` | Layout Service Input Spec (SOURCE OF TRUTH) |
