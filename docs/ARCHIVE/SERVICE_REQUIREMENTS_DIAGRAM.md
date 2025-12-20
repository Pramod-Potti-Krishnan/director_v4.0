# Diagram Service - Director Integration Requirements

**Version**: 2.0
**Date**: December 2024
**Status**: **FULLY ALIGNED** - Diagram Service returns spec-compliant fields directly

---

## Summary

Diagram Service v3.0 now returns **spec-compliant field names** directly. Director can use `diagram_html` field without any mapping.

| Response Field | Layout Service Needs | Status |
|----------------|---------------------|--------|
| `diagram_html` | `diagram_html` | **ALIGNED** - Direct use |
| `svg_content` | `diagram_html` | Legacy (still supported) |
| `mermaid_code` | (debug only) | Bonus - source code |

---

## Current Response Format (Diagram v3.0)

### Async Job Model

**Step 1: Submit Job**
```json
POST /generate
{
  "diagram_type": "flowchart",
  "content": "Show user registration process",
  "topics": ["Input validation", "Database storage", "Email confirmation"]
}

Response: {"job_id": "abc123-def456"}
```

**Step 2: Poll Status**
```json
GET /status/abc123-def456

Response (completed):
{
  "status": "completed",
  "result": {
    "success": true,
    "diagram_url": "https://storage.example.com/diagrams/abc123.svg",
    "svg_content": "<svg viewBox='0 0 1800 840'>...</svg>",
    "diagram_html": "<svg viewBox='0 0 1800 840'>...</svg>",
    "mermaid_code": "flowchart TD\n    A[Start] --> B[Validate]\n    B --> C[Save]\n    C --> D[Email]\n    D --> E[End]",
    "diagram_type": "flowchart",
    "generation_method": "mermaid"
  }
}
```

### Field Alias Reference (v3.0)

| Alias | Original Field | Purpose |
|-------|---------------|---------|
| `diagram_html` | `svg_content` | Layout Service compatibility |
| `mermaid_code` | (new) | Debugging - source Mermaid code |

---

## Layout Service Requirements

### For C5-diagram Layout

```json
{
  "layout": "C5-diagram",
  "content": {
    "slide_title": "<h2>Process Flow</h2>",
    "subtitle": "<p>User Registration Pipeline</p>",
    "diagram_html": "<svg viewBox='0 0 1800 840'>...</svg>"
  },
  "background_color": "#ffffff"
}
```

### For V3-diagram-text Layout

```json
{
  "layout": "V3-diagram-text",
  "content": {
    "slide_title": "<h2>System Architecture</h2>",
    "subtitle": "<p>High-Level Overview</p>",
    "diagram_html": "<svg>...</svg>",
    "body": "<ul><li>Frontend: React</li><li>Backend: FastAPI</li>...</ul>"
  },
  "background_color": "#f8fafc"
}
```

---

## Alignment Status

| Layout | Diagram Service v3.0 | Layout Service Expects | Status |
|--------|---------------------|----------------------|--------|
| C5-diagram | `diagram_html` | `diagram_html` | **ALIGNED** |
| V3-diagram-text | `diagram_html` + `body` (Text Svc) | `diagram_html` + `body` | **ALIGNED** |

**Note**: Diagram Service does NOT generate `slide_title`, `subtitle`, or `body`. These come from Text Service. Director orchestrates.

---

## Director Integration

### LayoutPayloadAssembler (v4.4)

```python
def _extract_diagram_html(self, content: Dict[str, Any]) -> str:
    """
    v4.4 preference order:
    1. diagram_html - Spec-compliant alias (PREFERRED)
    2. svg_content  - Legacy field
    3. diagram_url  - URL wrapped in img tag
    """
    if content.get("diagram_html"):
        return content["diagram_html"]  # v3.0 returns this!
    if content.get("svg_content"):
        return content["svg_content"]
    if content.get("diagram_url"):
        return f'<img src="{content["diagram_url"]}" ... />'
    return ""
```

### Payload Assembly

```python
# Director assembles from multiple services:
payload = {
    "layout": "C5-diagram",
    "content": {
        "slide_title": title_from_text_service,
        "subtitle": subtitle_from_text_service,
        "diagram_html": diagram_result.get("diagram_html")  # Direct!
    },
    "background_color": "#ffffff"
}
```

---

## Input Fields (Director → Diagram)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `diagram_type` | string | Yes | Type of diagram (flowchart, sequence, etc.) |
| `content` | string | Yes | Description of what to diagram |
| `topics` | array | No | Key elements to include |
| `direction` | string | No | TB, LR, BT, RL (default: TB) |
| `theme` | string | No | default, dark, forest, neutral |

---

## Output Fields (Diagram → Director)

| Field | Type | Description | Status |
|-------|------|-------------|--------|
| `result.diagram_html` | string | Inline SVG (spec-compliant) | **NEW v3.0** |
| `result.svg_content` | string | Inline SVG (legacy) | Supported |
| `result.mermaid_code` | string | Source Mermaid code | **NEW v3.0** |
| `result.diagram_url` | string | Cloud storage URL | Fallback |
| `result.diagram_type` | string | Type of diagram generated | Metadata |
| `result.generation_method` | string | mermaid, svg, python | Metadata |

---

## Supported Diagram Types

Diagram Service v3.0 supports 38 diagram types across 3 renderers:

### Mermaid Renderer (7 types)
- flowchart, erDiagram, journey, gantt
- quadrantChart, timeline, kanban

### SVG Renderer (25 types)
- Process diagrams, organizational charts
- Network diagrams, technical architecture

### Python Renderer (6 types)
- Complex visualizations requiring Python libraries

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Dec 2024 | Initial - Director handles svg_content → diagram_html mapping |
| 2.0 | Dec 2024 | **FULLY ALIGNED** - Diagram returns diagram_html directly |

### v3.0 Response Changes
- Added `diagram_html` field (alias for Layout Service)
- Added `mermaid_code` field (debugging)
- Kept `svg_content` for backward compatibility

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `THREE_WAY_ALIGNMENT_ANALYSIS_DIAGRAM.md` | Detailed alignment analysis |
| `DIAGRAM_SERVICE_CAPABILITIES.md` | Full API reference |
| `SLIDE_GENERATION_INPUT_SPEC.md` | Layout Service INPUT SPEC (SOURCE OF TRUTH) |

---

## Integration Notes

1. **Async Model**: Diagram generation is async - poll `/status/{job_id}` until complete
2. **Title/Subtitle**: Director generates these via Text Service (not Diagram)
3. **Timeout**: Consider 30-60s timeout for complex diagrams
4. **SVG Preferred**: Use `diagram_html` (inline SVG) for best quality
5. **URL Fallback**: Use `diagram_url` wrapped in `<img>` if no inline SVG
6. **Debugging**: `mermaid_code` shows source code for troubleshooting
