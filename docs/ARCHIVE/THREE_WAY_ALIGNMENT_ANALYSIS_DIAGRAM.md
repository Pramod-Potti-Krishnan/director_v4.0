# Diagram Service v3.0 - Three-Way Alignment Analysis

## Summary

This document analyzes alignment between THREE documents:
1. **DIAGRAM_SERVICE_CAPABILITIES.md** - What Diagram Service offers
2. **SERVICE_REQUIREMENTS_DIAGRAM.md** - What Director expects from Diagram Service
3. **SLIDE_GENERATION_INPUT_SPEC.md** - What Layout Service expects (**SOURCE OF TRUTH**)

**Analysis Date**: December 2024
**Status**: ✅ **FULLY ALIGNED** - Diagram Service now returns `svg_content`, `diagram_html`, and `mermaid_code`

---

## Quick Reference: Alignment Status

| Layout | Diagram Service | Director | Layout Service | Status |
|--------|-----------------|----------|----------------|--------|
| C5-diagram | ✅ `svg_content` + `diagram_html` | ✅ Direct or maps | ✅ `diagram_html` | **FULLY ALIGNED** |
| V3-diagram-text | ✅ `svg_content` + `diagram_html` | ✅ Direct or maps | ✅ `diagram_html`, `body` | **FULLY ALIGNED** |
| Title/Subtitle | ❌ Not generated | ✅ Uses Text Service | ✅ Required | **ALIGNED** (Correct separation) |
| background_color | ❌ Not returned | ✅ Adds default | ✅ Optional (default `#ffffff`) | **ALIGNED** (Director adds) |

---

## Detailed Analysis by Layout Type

### C5-diagram (Single Diagram)

**Layout Service SPEC (lines 785-827)**:
```json
{
  "layout": "C5-diagram",
  "content": {
    "slide_title": "<h2>Process Flow</h2>",              // REQUIRED - HTML
    "subtitle": "<p>Order Fulfillment Pipeline</p>",    // Optional - HTML
    "diagram_html": "<div class='diagram-container' style='width:100%;height:100%'><svg viewBox='0 0 1800 840'>...</svg></div>"  // REQUIRED - HTML from Diagram Service
  },
  "background_color": "#ffffff",                         // Optional - default white
  "background_image": "https://example.com/pattern.png"  // Optional
}
```

**Grid Specifications:**
- Diagram Area: rows 4-18, cols 2-32
- Dimensions: 1800 x 840 px
- Format Owner: `diagram_service`

**Director SERVICE_REQUIREMENTS (lines 53-64)**:
- Submits to `/generate` with `diagram_type` and `content`
- Polls `/status/{job_id}` until complete
- Maps `result.svg_content` → `diagram_html`
- Generates `slide_title`/`subtitle` via Text Service

**Diagram Service DIAGRAM_SERVICE_CAPABILITIES (Part 2.3)**:
- Returns `svg_content`: ✅ Inline SVG content
- Returns `diagram_html`: ⚠️ Documented as alias but NOT IMPLEMENTED in actual code
- Returns `diagram_url`: ✅ URL fallback
- Returns `mermaid_code`: ✅ For debugging

**STATUS**: ⚠️ **MINOR GAP - `diagram_html` alias not yet implemented**
- Documentation shows `diagram_html` as alias (line 386)
- Actual code returns only `svg_content`
- Director currently handles mapping, so no breaking issue

---

### V3-diagram-text (Diagram + Text Insights)

**Layout Service SPEC (lines 830-869)**:
```json
{
  "layout": "V3-diagram-text",
  "content": {
    "slide_title": "<h2>System Architecture</h2>",       // REQUIRED - HTML
    "subtitle": "<p>High-Level Overview</p>",            // Optional - HTML
    "diagram_html": "<div class='diagram-container'>...</div>",  // REQUIRED - 1080x840px
    "body": "<ul><li>Frontend: React</li><li>Backend: FastAPI</li></ul>"  // Optional - 720x840px
  },
  "background_color": "#f8fafc"                          // Optional
}
```

**Grid Specifications:**
- Left (Diagram): rows 4-18, cols 2-20 = 1080 x 840 px
- Right (Text): rows 4-18, cols 20-32 = 720 x 840 px

**Director SERVICE_REQUIREMENTS (lines 66-78)**:
- Diagram: from Diagram Service (`svg_content` → `diagram_html`)
- Body text: from Text Service
- Title/Subtitle: from Text Service

**Diagram Service DIAGRAM_SERVICE_CAPABILITIES**:
- Returns `svg_content`: ✅
- Does NOT return `body`: ✅ Correct (Text Service responsibility)
- Does NOT return `slide_title`/`subtitle`: ✅ Correct (Text Service responsibility)

**STATUS**: ✅ **ALIGNED** - Correct separation of concerns

---

## Gap Analysis

### Gap 1: `diagram_html` Field Alias - ✅ RESOLVED

| What | Status |
|------|--------|
| **SPEC Requires** | `diagram_html` field in content |
| **Diagram Service Returns** | ✅ `svg_content` + `diagram_html` + `mermaid_code` |
| **Director Handles** | Can use `diagram_html` directly |
| **Documentation Says** | Shows `diagram_html` as alias |
| **Actual Code** | ✅ Now includes `diagram_html` alias |

**Fix Applied**: Added in `agent.py` (December 2024):
```python
# agent.py - Response now includes all fields
return {
    "success": True,
    "diagram_url": diagram_url,
    "svg_content": svg_content,           # Inline SVG content (preferred)
    "diagram_html": svg_content,          # Alias for Layout Service compatibility
    "mermaid_code": mermaid_code,         # Source code for debugging
    "diagram_type": diagram_type,
    "generation_method": generation_method,
    "metadata": {...}
}
```

---

### Gap 2: Background Color Not Returned (EXPECTED)

| What | Status |
|------|--------|
| **SPEC Expects** | `background_color` as slide-level field |
| **Diagram Service Returns** | Diagram content only (no styling) |
| **Director Should** | Add default `background_color: "#ffffff"` |

**Impact**: None - this is correct behavior
**Rationale**: Diagram Service is a content generator, not a slide assembler. Background is a slide-level concern.

**Director Responsibility**:
```python
# In LayoutPayloadAssembler
payload = {
    "layout": "C5-diagram",
    "content": {
        "slide_title": title_from_text_service,
        "subtitle": subtitle_from_text_service,
        "diagram_html": diagram_result["svg_content"]
    },
    "background_color": theme.get("background_color", "#ffffff")
}
```

---

### Gap 3: Title/Subtitle Not Generated (CORRECT)

| What | Status |
|------|--------|
| **SPEC Requires** | `slide_title` (REQUIRED), `subtitle` (Optional) |
| **Diagram Service** | Does NOT generate these |
| **Text Service** | Generates these |
| **Director** | Coordinates between services |

**Impact**: None - this is correct separation of concerns
**Rationale**:
- Diagram Service focuses on visual diagram generation
- Text Service handles all text content generation
- Director orchestrates and assembles final payload

---

## Structural Difference: Response Shape

### Layout Service expects nested structure:
```json
{
  "layout": "C5-diagram",
  "content": {
    "slide_title": "...",
    "subtitle": "...",
    "diagram_html": "<svg>...</svg>"
  },
  "background_color": "#ffffff"
}
```

### Diagram Service returns flat structure:
```json
{
  "status": "completed",
  "result": {
    "success": true,
    "svg_content": "<svg>...</svg>",
    "diagram_url": "https://...",
    "mermaid_code": "flowchart TD..."
  }
}
```

**Resolution**: Director's `LayoutPayloadAssembler` is responsible for:
1. Getting diagram from Diagram Service (`svg_content`)
2. Getting title/subtitle from Text Service
3. Assembling into Layout Service format
4. Adding slide-level fields (`background_color`, etc.)

---

## Content Area Dimensions Alignment

| Layout | SPEC Dimensions | Diagram Service Supports | Status |
|--------|-----------------|--------------------------|--------|
| C5-diagram | 1800 x 840 px | ✅ Full content area | **ALIGNED** |
| V3-diagram-text (left) | 1080 x 840 px | ✅ Via constraints | **ALIGNED** |
| S3-two-visuals | 900 x 600 px each | ✅ Via constraints | **ALIGNED** |

**Grid Coordinates Mapping**:
```
C5-diagram:
  rows 4-18, cols 2-32
  x = (2-1) × 60 = 60px
  y = (4-1) × 60 = 180px
  width = (32-2) × 60 = 1800px
  height = (18-4) × 60 = 840px

V3-diagram-text (left panel):
  rows 4-18, cols 2-20
  width = (20-2) × 60 = 1080px
  height = (18-4) × 60 = 840px
```

---

## Director Coordination Endpoints Alignment

| Endpoint | SPEC Required | Diagram Service Implements | Status |
|----------|--------------|---------------------------|--------|
| `GET /capabilities` | ✅ | ✅ Implemented | **ALIGNED** |
| `POST /can-handle` | ✅ | ✅ Implemented | **ALIGNED** |
| `POST /recommend-diagram` | ✅ | ✅ Implemented | **ALIGNED** |

**Content Signals Alignment**:

| Signal Type | SERVICE_CAPABILITIES_SPEC | Diagram Service | Status |
|-------------|---------------------------|-----------------|--------|
| `handles_well` | Required | ✅ 11 categories | **ALIGNED** |
| `handles_poorly` | Required | ✅ 7 categories | **ALIGNED** |
| `keywords` | Required | ✅ 20 keywords | **ALIGNED** |
| `diagram_type_signals` | Recommended | ✅ 7 types with keywords | **ALIGNED** |

---

## Issues Identified

### Issue 1: `diagram_html` Alias Not Implemented - ✅ RESOLVED

**DIAGRAM_SERVICE_CAPABILITIES.md** (line 386) documents:
```json
"diagram_html": "<svg viewBox='0 0 1800 840'>...</svg>",    // Alias for Layout Service
```

**Fix Applied**: `agent.py` now includes `diagram_html` alias in the response (December 2024)

**Status**: ✅ RESOLVED - Documentation matches implementation

---

### Issue 2: Documentation Claims Alias Exists - ✅ RESOLVED

The capabilities document shows `diagram_html` in the response schema.

**Status**: ✅ RESOLVED - Implementation now matches documentation

---

## Summary: What Has Been Done

### Diagram Service - ✅ FIXED

- [x] Added `svg_content` field with inline SVG content
- [x] Added `diagram_html` field as alias for Layout Service compatibility
- [x] Added `mermaid_code` field for debugging

**Change Location**: `agent.py` lines 76-94

```python
# agent.py - Now returns all required fields
svg_content = generation_result.get("content", "")
mermaid_code = metadata.get("mermaid_code", "")

return {
    "success": True,
    "diagram_url": diagram_url,
    "svg_content": svg_content,           # Inline SVG (preferred)
    "diagram_html": svg_content,          # Alias for Layout Service
    "mermaid_code": mermaid_code,         # Source code for debugging
    ...
}
```

### Director - NO CHANGES NEEDED (Current Implementation Works)

The Director's `LayoutPayloadAssembler` can now use:
- [x] `diagram_html` directly (no mapping needed)
- [x] Or fallback to `svg_content`
- [x] URL fallback: wrapping `diagram_url` in `<img>` tag
- [x] Getting title/subtitle from Text Service
- [x] Adding `background_color` default
- [x] Assembling final Layout Service payload

### Layout Service - NO CHANGES NEEDED

- SLIDE_GENERATION_INPUT_SPEC.md is the canonical reference
- All diagram layouts (C5-diagram, V3-diagram-text) are properly specified

---

## Field Mapping Reference

### Diagram Service → Layout Service (via Director)

| Diagram Service Field | Director Mapping | Layout Service Field |
|-----------------------|------------------|---------------------|
| `result.diagram_html` | ✅ Direct (preferred) | `content.diagram_html` |
| `result.svg_content` | Direct or via alias | `content.diagram_html` |
| `result.diagram_url` | Wrap in `<img>` (fallback) | `content.diagram_html` |
| `result.mermaid_code` | Debug only | (not passed) |
| (not returned) | From Text Service | `content.slide_title` |
| (not returned) | From Text Service | `content.subtitle` |
| (not returned) | From Text Service | `content.body` |
| (not returned) | From Theme/Default | `background_color` |

### Director Assembly Example

```python
# Director's LayoutPayloadAssembler
def assemble_diagram_slide(
    self,
    layout: str,
    diagram_result: Dict,
    text_result: Dict,
    theme: Dict
) -> Dict:
    """Assemble C5-diagram or V3-diagram-text payload"""

    # Extract diagram HTML
    diagram_html = self._extract_diagram_html(diagram_result)

    payload = {
        "layout": layout,
        "content": {
            "slide_title": text_result.get("slide_title", ""),
            "subtitle": text_result.get("subtitle"),
            "diagram_html": diagram_html
        },
        "background_color": theme.get("background_color", "#ffffff")
    }

    # V3-diagram-text also needs body
    if layout == "V3-diagram-text":
        payload["content"]["body"] = text_result.get("body", "")

    return payload

def _extract_diagram_html(self, content: Dict) -> str:
    """Extract diagram HTML with fallback logic"""
    if content.get("diagram_html"):
        return content["diagram_html"]
    if content.get("svg_content"):
        return content["svg_content"]
    if content.get("diagram_url"):
        return f'<img src="{content["diagram_url"]}" class="diagram-image" style="max-width:100%;max-height:100%;" />'
    return ""
```

---

## Service Responsibility Matrix

| Responsibility | Diagram Service | Text Service | Director | Layout Service |
|----------------|-----------------|--------------|----------|----------------|
| Generate diagram SVG | ✅ Primary | - | - | - |
| Generate slide_title | - | ✅ Primary | Orchestrates | Renders |
| Generate subtitle | - | ✅ Primary | Orchestrates | Renders |
| Generate body (V3) | - | ✅ Primary | Orchestrates | Renders |
| Field name mapping | Optional alias | - | ✅ Handles | Expects specific names |
| Add background_color | - | - | ✅ Adds | Renders |
| Assemble payload | - | - | ✅ Primary | Receives |
| Validate input | - | - | - | ✅ Primary |
| Render slide | - | - | - | ✅ Primary |

---

## Recommendation for Director Team

### Current State: WORKING

The Director's current implementation correctly:
1. Gets diagrams from Diagram Service via `/generate` + `/status/{job_id}`
2. Maps `svg_content` → `diagram_html`
3. Gets title/subtitle/body from Text Service
4. Assembles complete payload for Layout Service

### Optional Enhancement

If Diagram Service adds the `diagram_html` alias:
```python
# Simplified Director code (no mapping needed)
def _extract_diagram_html(self, content: Dict) -> str:
    return content.get("diagram_html") or content.get("svg_content") or ""
```

---

## SPEC Compliance Checklist

| Layout | `diagram_html` | `slide_title` | `subtitle` | `body` | `background_color` |
|--------|---------------|---------------|------------|--------|-------------------|
| C5-diagram | ✅ Via mapping | ✅ Text Service | ✅ Optional | N/A | ✅ Director adds |
| V3-diagram-text | ✅ Via mapping | ✅ Text Service | ✅ Optional | ✅ Text Service | ✅ Director adds |

---

## Comparison with Text Service Analysis

| Aspect | Text Service | Diagram Service |
|--------|--------------|-----------------|
| Field alignment | Had gaps, now fixed | ✅ Fixed - includes `diagram_html` |
| Background fields | Returns `background_color` | Not returned (correct) |
| Title/Subtitle | Returns directly | Not generated (correct) |
| Director mapping needed | Minimal after fixes | ✅ None - can use `diagram_html` directly |
| Efficiency savings | 67% LLM call reduction | N/A (diagram generation is separate) |
| Documentation status | Updated | ✅ Updated - matches implementation |

---

## Action Items - ✅ ALL COMPLETE

### Priority 1: Fix Documentation/Implementation Mismatch - ✅ DONE

**Implemented Option A**: Added `diagram_html` alias to response
- [x] File: `agent.py` - Added `svg_content`, `diagram_html`, `mermaid_code`
- [x] Benefit: Documentation now matches implementation
- [x] Director can use `diagram_html` directly

### Priority 2: None Required

- [x] Director handles mapping correctly (can now use direct field)
- [x] Layout Service receives correct format
- [x] No breaking changes needed

---

## Related Documents

| Document | Location | Purpose |
|----------|----------|---------|
| DIAGRAM_SERVICE_CAPABILITIES.md | `/director_agent/v4.0/docs/` | Diagram Service API Reference |
| SERVICE_REQUIREMENTS_DIAGRAM.md | `/director_agent/v4.0/docs/` | Director → Diagram Service Contract |
| SLIDE_GENERATION_INPUT_SPEC.md | `/director_agent/v4.0/docs/` | Layout Service Input Spec (SOURCE OF TRUTH) |
| THREE_WAY_ALIGNMENT_ANALYSIS.md | `/director_agent/v4.0/docs/` | Text Service Alignment (reference) |
| SERVICE_CAPABILITIES_SPEC.md | `/director_agent/v4.0/docs/` | Coordination Endpoint Specification |

---

*This analysis was generated December 2024 as part of Diagram Service v3.0 Director coordination integration work.*
