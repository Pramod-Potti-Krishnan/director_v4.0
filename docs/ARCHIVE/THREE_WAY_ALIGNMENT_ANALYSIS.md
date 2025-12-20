# Text Service v1.2 - Three-Way Alignment Analysis

## Summary

This document analyzes alignment between THREE documents:
1. **TEXT_SERVICE_CAPABILITIES.md** - What Text Service offers
2. **SERVICE_REQUIREMENTS_TEXT.md** - What Director expects from Text Service
3. **SLIDE_GENERATION_INPUT_SPEC.md** - What Layout Service expects (**SOURCE OF TRUTH**)

**Analysis Date**: December 2024
**Status**: ✅ **TEXT SERVICE IS FULLY SPEC-COMPLIANT** - Director documentation needs update

---

## Quick Reference: Alignment Status

| Layout | Text Service | Director | Layout Service | Status |
|--------|-------------|----------|----------------|--------|
| H1-generated | ✅ `hero_content` | ✅ Maps `content` → `hero_content` | ✅ | **ALIGNED** |
| H1-structured | ✅ Structured fields + `background_color` | ⚠️ Uses workaround | ✅ | **Text Service READY, Director needs update** |
| H2-section | ✅ `section_number`, `slide_title`, `background_color` | ⚠️ Uses workaround | ✅ | **Text Service READY, Director needs update** |
| H3-closing | ✅ Fields + `background_color` | ⚠️ Uses workaround | ✅ | **Text Service READY, Director needs update** |
| L29 | ✅ `hero_content` | ✅ Direct | ✅ | **ALIGNED** |
| C1-text | ✅ Combined gen + `background_color` | ⚠️ Separate calls | ✅ | **Text Service READY, Director can simplify** |
| L25 | ✅ `slide_title`, `rich_content`, `background_color` | ✅ Mapping | ✅ | **ALIGNED** |
| I-series | ✅ Slots + aliases + `background_color` | ✅ Mapping | ✅ | **ALIGNED** |

---

## Detailed Analysis by Layout Type

### H1-generated / L29 (Full-Bleed Hero)

**Layout Service SPEC (lines 152-177, 331-363)**:
```json
{
  "layout": "H1-generated",
  "content": {
    "hero_content": "<div style='...'>Full 1920x1080 HTML</div>"
  }
  // NO background_color or background_image needed (embedded in hero_content)
}
```

**Director SERVICE_REQUIREMENTS (lines 60-64, 74)**:
- Maps `response.content` → `hero_content`
- Works correctly ✅

**Text Service TEXT_SERVICE_CAPABILITIES (Part 1.1)**:
- Returns `hero_content`: ✅
- Returns `background_color: null`: ✅ (per SPEC, not needed)
- Returns `background_image`: extracted from HTML

**STATUS**: ✅ **FULLY ALIGNED**

---

### H1-structured (Manual Title Slide)

**Layout Service SPEC (lines 181-234)**:
```json
{
  "layout": "H1-structured",
  "content": {
    "slide_title": "HTML with inline CSS",      // REQUIRED
    "subtitle": "HTML with inline CSS",          // Optional
    "author_info": "HTML with inline CSS"        // Optional
  },
  "background_color": "#1e3a5f",                 // Default
  "background_image": "https://..."              // Optional
}
```

**Director SERVICE_REQUIREMENTS (lines 76-100)**:
- **Current workaround**: Generates title/subtitle separately via `/api/ai/slide/title` and `/api/ai/slide/subtitle`
- OR treats as full HTML (like H1-generated)
- **NOT using new Text Service endpoints**

**Text Service TEXT_SERVICE_CAPABILITIES (Part 1.2)**:
- Returns `slide_title`: ✅ HTML with inline CSS
- Returns `subtitle`: ✅ HTML with inline CSS
- Returns `author_info`: ✅ HTML with inline CSS
- Returns `background_color`: ✅ `#1e3a5f`
- Returns `background_image`: ✅ Optional

**STATUS**: ⚠️ **Text Service READY - Director documentation outdated**
- Text Service now returns exactly what Layout Service expects
- Director's SERVICE_REQUIREMENTS_TEXT.md still describes old workaround

---

### H2-section (Section Divider)

**Layout Service SPEC (lines 237-272)**:
```json
{
  "layout": "H2-section",
  "content": {
    "section_number": "01",                      // Optional (can be HTML)
    "slide_title": "Section Title"               // REQUIRED
  },
  "background_color": "#374151",                 // Default (darker gray)
  "background_image": "https://..."              // Optional
}
```

**Director SERVICE_REQUIREMENTS (lines 199-205)**:
- `section_number`: From strawman or auto-generated
- `slide_title`: From `/api/ai/slide/title` or strawman
- **NOT using new Text Service endpoints**

**Text Service TEXT_SERVICE_CAPABILITIES (Part 1.3)**:
- Returns `section_number`: ✅ HTML with inline CSS
- Returns `slide_title`: ✅ HTML with inline CSS
- Returns `background_color`: ✅ `#374151`

**STATUS**: ⚠️ **Text Service READY - Director documentation outdated**

---

### H3-closing (Closing Slide)

**Layout Service SPEC (lines 274-327)**:
```json
{
  "layout": "H3-closing",
  "content": {
    "slide_title": "Thank You",                  // REQUIRED (HTML OK)
    "subtitle": "Questions?",                    // Optional (HTML OK)
    "contact_info": "<a href='mailto:...'>...</a>"  // Optional (HTML OK)
  },
  "background_color": "#1e3a5f",                 // Default
  "background_image": "https://..."              // Optional
}
```

**Director SERVICE_REQUIREMENTS (lines 207-214)**:
- `slide_title`: From `/api/ai/slide/title` or default "Thank You"
- `contact_info`: From branding or strawman
- **NOT using new Text Service endpoints**

**Text Service TEXT_SERVICE_CAPABILITIES (Part 1.4)**:
- Returns `slide_title`: ✅ HTML with inline CSS
- Returns `subtitle`: ✅ HTML with inline CSS
- Returns `contact_info`: ✅ HTML with inline CSS
- Returns `closing_message`: ⚠️ Extra field (not in SPEC, but harmless)
- Returns `background_color`: ✅ `#1e3a5f`

**STATUS**: ⚠️ **Text Service READY - Director documentation outdated**
- `closing_message` field is extra but Layout Service will ignore it

---

### C1-text (Content Slide)

**Layout Service SPEC (lines 368-413)**:
```json
{
  "layout": "C1-text",
  "content": {
    "slide_title": "HTML",                       // REQUIRED
    "subtitle": "HTML",                          // Optional
    "body": "<ul><li>...</li></ul>",             // REQUIRED (HTML)
    "footer_text": "Confidential",               // Optional (NOT generated by Text Service)
    "company_logo": "https://..."                // Optional (NOT generated by Text Service)
  },
  "background_color": "#ffffff",                 // Default white
  "background_image": "https://..."              // Optional
}
```

**Director SERVICE_REQUIREMENTS (lines 224-230)**:
- `slide_title`: from `/api/ai/slide/title`
- `subtitle`: from `/api/ai/slide/subtitle`
- `body`: from `/v1.2/generate` → `response.html`
- **3 separate calls** per slide

**Text Service TEXT_SERVICE_CAPABILITIES (Part 1.5)**:
- Returns `slide_title`: ✅ HTML with inline CSS
- Returns `subtitle`: ✅ HTML with inline CSS
- Returns `body`: ✅ HTML content
- Returns `rich_content`: ✅ Alias for body
- Returns `background_color`: ✅ `#ffffff`
- **1 LLM call** (combined generation)

**STATUS**: ⚠️ **Text Service READY with 67% efficiency improvement**
- Director can simplify: use single `/v1.2/slides/C1-text` instead of 3 separate calls
- `footer_text` and `company_logo` are NOT content - Director passes through from strawman

---

### L25 (Main Content Shell)

**Layout Service SPEC (lines 416-461)**:
```json
{
  "layout": "L25",
  "content": {
    "slide_title": "HTML",                       // REQUIRED
    "subtitle": "HTML",                          // Optional
    "rich_content": "<div>...</div>",            // REQUIRED (HTML from Text Service)
    "presentation_name": "Quarterly Review",     // Optional (NOT generated)
    "company_logo": "https://..."                // Optional (NOT generated)
  },
  "background_color": "#ffffff",                 // Default white
  "background_image": "https://..."              // Optional
}
```

**Director SERVICE_REQUIREMENTS (lines 216-222)**:
- `slide_title`: from `/api/ai/slide/title`
- `subtitle`: from `/api/ai/slide/subtitle`
- `rich_content`: from `/v1.2/generate`

**Text Service C1-text Response**:
- `body` AND `rich_content` (alias): ✅ Both returned

**STATUS**: ✅ **ALIGNED** - `/v1.2/slides/L25` is alias for C1-text

---

### I-Series (Image + Content)

**Layout Service SPEC (lines 469-607)**:
```json
{
  "layout": "I1-image-left",
  "content": {
    "slide_title": "HTML",                       // REQUIRED
    "subtitle": "HTML",                          // Optional
    "image_url": "https://...",                  // Optional
    "body": "HTML"                               // Optional
  },
  "background_color": "#ffffff"                  // Optional (background_image NOT recommended)
}
```

**Director SERVICE_REQUIREMENTS (lines 102-129, 232-239)**:
- `title_html` → `slide_title` (mapping needed)
- `content_html` → `body` (mapping needed)
- `image_url`: direct
- Director handles field name mapping

**Text Service TEXT_SERVICE_CAPABILITIES (Part 1.6)**:
- Returns `title_html`, `content_html`, `image_url`: ✅ Original fields
- Returns `slide_title`, `body`: ✅ **Aliases now included**
- Returns `background_color`: ✅ `#ffffff`

**STATUS**: ✅ **ALIGNED** - Director can now use aliases directly (no mapping needed)

---

## Structural Difference: Response Shape

### Layout Service expects nested structure:
```json
{
  "layout": "H1-structured",
  "content": {
    "slide_title": "...",
    "subtitle": "..."
  },
  "background_color": "#1e3a5f"
}
```

### Text Service returns flat structure:
```json
{
  "slide_title": "...",
  "subtitle": "...",
  "background_color": "#1e3a5f",
  "metadata": {}
}
```

**Resolution**: Director is responsible for restructuring Text Service response into Layout Service format. This is expected and documented in SERVICE_REQUIREMENTS_TEXT.md as "Director handles mapping".

---

## Issues Identified

### Issue 1: Director Documentation is Outdated

**SERVICE_REQUIREMENTS_TEXT.md** (last updated December 2024) describes:
- Workarounds for H1-structured, H2-section, H3-closing (separate title/subtitle calls)
- 3 LLM calls per content slide
- Field mapping for I-series

**Current Reality** (Text Service v1.2 with unified slides router):
- `/v1.2/slides/*` endpoints return structured fields directly
- 1 LLM call for C1-text (combined generation)
- I-series includes aliases (no mapping needed)

**Recommendation**: Update SERVICE_REQUIREMENTS_TEXT.md to reflect new capabilities

### Issue 2: Extra `closing_message` Field in H3-closing

**Text Service returns**: `closing_message` field
**Layout Service SPEC**: Does NOT include `closing_message`

**Impact**: None - Layout Service will ignore unknown fields
**Recommendation**: Could remove from response for cleaner contract, but not breaking

### Issue 3: I-Series Layout Names

**Layout Service uses**: `I1-image-left`, `I2-image-right`, etc.
**Text Service uses**: `I1`, `I2`, `I3`, `I4`

**Impact**: None - short names are acceptable aliases
**Recommendation**: Document both forms as valid

---

## Summary: What Needs to Happen

### Text Service - ✅ COMPLETE
- [x] All H-series return `background_color` with correct defaults
- [x] All text fields are HTML with inline CSS
- [x] H1-generated uses `hero_content` (no separate background fields)
- [x] C1-text uses combined generation (1 LLM call)
- [x] I-series includes Layout Service aliases
- [x] TEXT_SERVICE_CAPABILITIES.md updated with SPEC-compliant examples

### Director - NEEDS UPDATE
- [ ] Update SERVICE_REQUIREMENTS_TEXT.md to document new `/v1.2/slides/*` endpoints
- [ ] Simplify code to use combined generation for C1-text
- [ ] Use I-series aliases instead of manual mapping
- [ ] Use new H1-structured, H2-section, H3-closing endpoints instead of workarounds

### Layout Service - NO CHANGES NEEDED
- SLIDE_GENERATION_INPUT_SPEC.md is the canonical reference
- Text Service responses now comply with this spec

---

## Recommendation for Director Team

Create a migration document for Director v4.3+ that:
1. Deprecates separate title/subtitle calls for H-series
2. Uses `/v1.2/slides/C1-text` for 67% LLM savings
3. Uses new `/v1.2/slides/H1-structured` etc. for structured hero fields
4. Removes I-series field mapping code (use aliases)

---

## SPEC Compliance Checklist

| Layout | `background_color` | `background_image` | Text Fields as HTML |
|--------|-------------------|-------------------|---------------------|
| H1-generated/L29 | ❌ Not needed (in hero_content) | ❌ Not needed | N/A (hero_content is full HTML) |
| H1-structured | ✅ Required (default `#1e3a5f`) | ✅ Optional | ✅ All fields with inline CSS |
| H2-section | ✅ Required (default `#374151`) | ✅ Optional | ✅ All fields with inline CSS |
| H3-closing | ✅ Required (default `#1e3a5f`) | ✅ Optional | ✅ All fields with inline CSS |
| C1-text | ✅ Required (default `#ffffff`) | ✅ Optional | ✅ All fields with inline CSS |
| I-series | ✅ Required (default `#ffffff`) | ❌ Not recommended | ✅ HTML slots |

---

## LLM Call Efficiency

| Slide Type | Old (Separate) | New (Combined) | Savings |
|-----------|---------------|----------------|---------|
| C1-text | 3 calls (title + subtitle + body) | 1 call | **-67%** |
| H-series | 1 call | 1 call | Same |
| I-series | 2 calls (image + content) | 2 calls | Same |

For a 10-slide deck with 6 content slides:
- Old: 6 × 3 = 18 LLM calls for content
- New: 6 × 1 = 6 LLM calls for content
- **Savings: 12 LLM calls per deck**

---

## Related Documents

| Document | Location | Purpose |
|----------|----------|---------|
| TEXT_SERVICE_CAPABILITIES.md | `/director_agent/v4.0/docs/` | Text Service API Reference |
| SERVICE_REQUIREMENTS_TEXT.md | `/director_agent/v4.0/docs/` | Director → Text Service Contract |
| SLIDE_GENERATION_INPUT_SPEC.md | `/director_agent/v4.0/docs/` | Layout Service Input Spec (SOURCE OF TRUTH) |

---

*This analysis was generated December 2024 as part of Text Service v1.2 SPEC compliance work.*
