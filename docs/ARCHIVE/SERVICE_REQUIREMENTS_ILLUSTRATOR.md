# Illustrator Service - Director Integration Requirements

**Version**: 2.0
**Date**: December 2024
**Priority**: LOW
**Status**: ✅ **FULLY ALIGNED** - Illustrator returns infographic_html directly

## Summary

Director Agent v4.4 coordinates with Illustrator Service v1.0.2 for infographic generation (pyramids, funnels, concentric circles, concept spreads).

**v2.0 Update**: Illustrator Service now provides `infographic_html` field directly in all responses. Director's `LayoutPayloadAssembler` no longer needs field mapping - responses can be used directly.

---

## Illustrator v1.0.2 Response Format (With Alias)

### Endpoint: `POST /v1.0/{visual_type}/generate`

**Example**: `POST /v1.0/pyramid/generate`

```json
{
  // NEW v1.0.2 Alias (SPEC-compliant)
  "infographic_html": "<div class='pyramid-container' style='width:100%;height:100%'>...</div>",

  // Original field (kept for backward compatibility)
  "html": "<div class='pyramid-container' style='width:100%;height:100%'>...</div>",

  "generated_content": {
    "title": "Organizational Hierarchy",
    "levels": [
      {"label": "CEO", "description": "Chief Executive Officer"},
      {"label": "VPs", "description": "Vice Presidents"},
      {"label": "Directors", "description": "Department Directors"},
      {"label": "Managers", "description": "Team Managers"}
    ]
  },
  "metadata": {
    "service": "illustrator_v1",
    "visual_type": "pyramid",
    "num_levels": 4,
    "generation_time_ms": 850,
    "model_used": "gemini-2.0-flash"
  },
  "validation": {
    "valid": true,
    "violations": []
  }
}
```

### Field Alias Reference

| New Alias | Value | Use For | SPEC Compliance |
|-----------|-------|---------|-----------------|
| `infographic_html` | Same as `html` | C4-infographic, V4-infographic-text | ✅ Direct use |

---

## Layout Service Requirements (All ALIGNED)

### For C4-infographic Layout

```json
{
  "layout": "C4-infographic",
  "content": {
    "slide_title": "<h2>Organizational Structure</h2>",
    "subtitle": "<p>Company Hierarchy Overview</p>",
    "infographic_html": "..."  // ✅ Illustrator provides directly
  }
}
```

### For V4-infographic-text Layout

```json
{
  "layout": "V4-infographic-text",
  "content": {
    "slide_title": "<h2>Key Metrics</h2>",
    "subtitle": "<p>2024 Performance Summary</p>",
    "infographic_html": "...",  // ✅ Illustrator provides directly (left, 1080x840px)
    "body": "..."               // Director provides via Text Service (right, 720x840px)
  }
}
```

---

## Alignment Status

| Layout | Infographic Field | Status |
|--------|-------------------|--------|
| C4-infographic | `infographic_html` ✅ | **ALIGNED** |
| V4-infographic-text | `infographic_html` ✅ | **ALIGNED** |

**Note**: Illustrator does NOT generate `slide_title`, `subtitle`, or `body`. Director generates these via Text Service.

---

## Director Integration (v4.4)

### LayoutPayloadAssembler

The assembler prioritizes spec-compliant field and falls back to legacy for compatibility:

```python
# C4-infographic / V4-infographic-text
infographic_html = content.get("infographic_html") or content.get("html", "")
```

### Backward Compatibility

Original `html` field is preserved, ensuring existing integrations continue to work.

---

## Field Reference

### Input Fields (Director → Illustrator)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `num_levels` | int | Yes | Number of levels (3-6 for pyramid) |
| `topic` | string | Yes | Main topic/theme |
| `target_points` | array | No | Optional specific level labels |
| `context` | object | No | Presentation context for LLM |
| `tone` | string | No | Content tone (default: professional) |
| `audience` | string | No | Target audience |

### Output Fields (Illustrator → Director)

| Field | Type | Description |
|-------|------|-------------|
| `infographic_html` | string | ✅ **NEW v1.0.2** SPEC-compliant visualization HTML |
| `html` | string | Original HTML (legacy, still available) |
| `generated_content.title` | string | AI-generated title (plain text) |
| `generated_content.levels` | array | Level data (labels, descriptions) |
| `metadata.visual_type` | string | pyramid, funnel, concentric_circles, concept_spread |
| `validation.valid` | boolean | Whether constraints are met |

---

## Supported Visual Types

Illustrator v1.0.2 supports 4 visual types:

| Visual Type | Endpoint | Levels/Items | `infographic_html` |
|-------------|----------|--------------|-------------------|
| Pyramid | `/v1.0/pyramid/generate` | 3-6 levels | ✅ Included |
| Funnel | `/v1.0/funnel/generate` | 3-5 stages | ✅ Included |
| Concentric Circles | `/v1.0/concentric_circles/generate` | 3-5 rings | ✅ Included |
| Concept Spread | `/concept-spread/generate` | 6 hexagons | ✅ Included |

---

## Integration Notes

1. **Title/Subtitle Generation**: Director generates these via Text Service, not Illustrator
2. **HTML Size**: Typically 5-15KB per visualization
3. **Character Constraints**: Illustrator applies character limits and may retry generation
4. **Validation**: Check `validation.valid` for constraint compliance
5. **Field Priority**: Director uses spec-compliant `infographic_html` first, `html` as fallback

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | Dec 2024 | Illustrator v1.0.2 alias - FULLY ALIGNED |
| 1.0 | Dec 2024 | Initial - Director handles field mapping |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `THREE_WAY_ALIGNMENT_ANALYSIS_ILLUSTRATOR.md` | Detailed alignment analysis |
| `ILLUSTRATOR_SERVICE_CAPABILITIES.md` | Illustrator Service API Reference (v1.0.2) |
| `SLIDE_GENERATION_INPUT_SPEC.md` | Layout Service Input Spec (SOURCE OF TRUTH) |
