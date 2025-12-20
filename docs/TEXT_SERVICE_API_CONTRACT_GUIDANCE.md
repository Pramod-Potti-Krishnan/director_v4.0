# Text Service API Contract Guidance

**From**: Director Agent Team
**To**: Text Service Team
**Re**: API Contract Discrepancies - Director's Guidance
**Date**: December 20, 2024
**Reference**: `CONTRACT_EXACTNESS_REPORT.md` and `NOTE_TO_DIRECTOR_TEAM.md`

---

## Executive Summary

After analyzing Director's actual usage of Text Service response fields, we provide clear answers to your questions and recommend a **hybrid approach** that minimizes changes while ensuring contract accuracy.

### Quick Decision Matrix

| Deviation | Recommendation | Breaking? |
|-----------|----------------|-----------|
| `background_color` in iseries/generate | **Document it** | YES - Director uses it |
| `metadata.validation` | **Keep & Document** | NO - safe to keep |
| `metadata.visual_style` | **Normalize across endpoints** | NO |
| Timing fields (3 → 1) | **Simplify docs** | NO - Director doesn't use |
| Other extra metadata | **Document (optional)** | NO |

---

## Answers to Your Questions

### Q1: Are any discrepancies breaking for Director?

**YES - One field is breaking if removed:**

| Field | Endpoint | Breaking? | Evidence |
|-------|----------|-----------|----------|
| `background_color` | `/v1.2/iseries/generate` | **YES** | Used at `websocket.py:1507,1642,2120` |

**NO - These fields are NOT consumed by Director:**

| Field | Used? | Notes |
|-------|-------|-------|
| `metadata.validation` | Passed through only | `text_tools.py` passes generic `metadata` object |
| `metadata.visual_style` | NO | Not consumed anywhere |
| `metadata.generation_time_ms` | NO | Not consumed |
| `metadata.fallback_to_gradient` | NO | Not consumed |
| `metadata.generation_mode` | NO | Not consumed |
| `metadata.layout_type` | NO | Not consumed |
| `metadata.image_generation_time_ms` | NO | Not consumed |
| `metadata.content_generation_time_ms` | NO | Not consumed |
| `metadata.total_generation_time_ms` | NO | Not consumed |

### Q2: Preference for Resolution?

**Recommendation: Hybrid Approach (Modified Option A)**

We recommend **documenting** the extra fields rather than removing them, with one normalization fix.

---

## Detailed Recommendations Per Discrepancy

### 1. `background_color` in `/v1.2/iseries/generate` (EXTRA)

**Status**: UNDOCUMENTED but Director uses it

**Recommendation**: **Document it (HIGH PRIORITY)**

**Evidence**:
```python
# websocket.py lines 1507, 1642, 2120
'background_color': result.get('background_color'),
```

**Action**: Add `background_color` to Part 5.1 of TEXT_SERVICE_CAPABILITIES.md

---

### 2. `metadata.validation` (EXTRA in H1-generated, I1, iseries/generate)

**Recommendation**: **Keep & Document**

**Rationale**:
- Useful for debugging generation issues
- Director passes through generic `metadata` object to tools
- No harm in keeping it - adds observability
- ~100 bytes overhead is negligible

**Action**: Add `metadata.validation` as an optional diagnostic field in documentation.

**Example documentation**:
```markdown
#### Diagnostic Fields (Optional)

| Field | Type | Description |
|-------|------|-------------|
| `metadata.validation` | object | Content validation results |
| `metadata.validation.valid` | boolean | Whether content passed validation |
| `metadata.validation.violations` | array | List of validation issues (if any) |
```

---

### 3. `metadata.visual_style` (Inconsistent)

**Current State**:
- H1-generated: **DOCUMENTED** but **NOT RETURNED**
- C1-text: **NOT DOCUMENTED** but **RETURNED**

**Recommendation**: **Normalize - Add to all endpoints**

**Rationale**:
- Consistency helps debugging
- Shows which visual style was applied
- Useful for future style-aware features

**Action**:
1. Add `metadata.visual_style` to H1-generated responses (fix missing)
2. Document `metadata.visual_style` for C1-text and all other endpoints

---

### 4. Timing Fields in `/v1.2/iseries/generate`

**Contract Says**:
- `metadata.image_generation_time_ms`
- `metadata.content_generation_time_ms`
- `metadata.total_generation_time_ms`

**API Returns**:
- `metadata.generation_time_ms` (single field)

**Recommendation**: **Simplify documentation**

**Rationale**:
- Director doesn't consume timing fields
- Single `generation_time_ms` is cleaner
- 3-field spec was over-engineered

**Action**: Update Part 5.1 to document single `metadata.generation_time_ms` instead of 3 separate fields.

---

### 5. Other Extra Metadata (H1-generated)

**Extra fields**:
- `metadata.background_image`
- `metadata.image_generation_time_ms`
- `metadata.fallback_to_gradient`
- `metadata.generation_mode`
- `metadata.layout_type`

**Recommendation**: **Document as optional diagnostics**

**Rationale**:
- Useful for debugging image generation issues
- `fallback_to_gradient` shows when image gen failed
- No harm in keeping - adds observability

**Action**: Add these to documentation as "Diagnostic Fields (H1-generated specific)".

---

## Summary of Actions

### For Text Service Team

| Priority | Action | File to Update |
|----------|--------|----------------|
| **HIGH** | Document `background_color` in iseries/generate | `TEXT_SERVICE_CAPABILITIES.md` Part 5.1 |
| **HIGH** | Add `metadata.visual_style` to H1-generated response | API code |
| MEDIUM | Document `metadata.validation` as optional | `TEXT_SERVICE_CAPABILITIES.md` |
| MEDIUM | Simplify timing fields (3→1) in docs | `TEXT_SERVICE_CAPABILITIES.md` Part 5.1 |
| LOW | Document other extra metadata fields | `TEXT_SERVICE_CAPABILITIES.md` |

### No Code Removal Needed

All extra fields can remain in responses. Director ignores what it doesn't need.

---

## Director's Field Usage Reference

### Fields Director ACTIVELY Uses

| Field | Location | Purpose |
|-------|----------|---------|
| `slide_title` | websocket.py:1502,1638 | Slide title HTML |
| `subtitle` | websocket.py:1503,1639 | Slide subtitle HTML |
| `body` | websocket.py:1637,1640 | Main content HTML |
| `rich_content` | websocket.py:1641 | Alternative content field |
| `hero_content` | websocket.py:1501 | Full-bleed hero HTML |
| `background_color` | websocket.py:1507,1642,2120 | Slide background |
| `background_image` | websocket.py:1508 | Hero image URL |
| `section_number` | websocket.py:1504 | H2-section numbering |
| `contact_info` | websocket.py:1505 | H3-closing contact |
| `author_info` | websocket.py:1506 | H1-structured author |

### Fields Director Passes Through (Not Consumed)

| Field | Location | Notes |
|-------|----------|-------|
| `metadata` (generic) | text_tools.py:299,425,551 | Whole object passed to tools |

---

## Contract Accuracy Summary

After implementing recommended changes:

| Endpoint | Input | Output | Status |
|----------|-------|--------|--------|
| GET /v1.2/slides/health | EXACT | EXACT | ✅ |
| GET /v1.2/capabilities | EXACT | EXACT | ✅ |
| POST /v1.2/can-handle | EXACT | EXACT | ✅ |
| POST /v1.2/slides/H1-generated | EXACT | EXACT (after fix) | ✅ |
| POST /v1.2/slides/C1-text | EXACT | EXACT (after doc) | ✅ |
| POST /v1.2/slides/I1 | EXACT | EXACT (after doc) | ✅ |
| POST /v1.2/iseries/generate | EXACT | EXACT (after doc) | ✅ |

---

## Path Forward

1. **Text Service fixes H1-generated** - Add `metadata.visual_style` to response
2. **Text Service updates documentation** - All changes listed above
3. **Director confirms** - No code changes needed on Director side
4. **Both teams sign off** - Contract is now exact

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-20 | 1.0 | Initial guidance document |

---

**Contact**: Director Agent Team
**Related Docs**:
- `docs/TEXT_SERVICE_CAPABILITIES.md`
- `docs/SERVICE_REQUIREMENTS_TEXT.md` (v2.0)
- `docs/THREE_WAY_ALIGNMENT_ANALYSIS.md`
