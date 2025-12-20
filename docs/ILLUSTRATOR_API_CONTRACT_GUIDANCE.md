# Illustrator Service API Contract Guidance

**From**: Director Agent Team
**To**: Illustrator Service Team
**Re**: API Contract Deviation - Director's Recommendations
**Date**: December 20, 2024
**Reference**: `EXACTNESS_REPORT.md` (Illustrator v1.0 vs ILLUSTRATOR_SERVICE_CAPABILITIES.md v1.0.3)

---

## Executive Summary

After analyzing Director's actual usage of Illustrator Service endpoints and the deviation report, we provide the following guidance. The key insight: **Director only uses the generation endpoints** - metadata endpoints (`/capabilities`, `/types`, `/themes`) are not called by Director.

### Quick Decision Matrix

| Deviation | Recommendation | Action Owner |
|-----------|----------------|--------------|
| `/capabilities` nested structure | **Option A: Update Contract** | Illustrator Team |
| pyramid/funnel extra metadata | **Option A: Keep & Document** | Illustrator Team |
| `/types` missing keys | **Option A: Update Contract** | Illustrator Team |
| `/types` extra keys | **Option A: Add to Contract** | Illustrator Team |
| `/themes` missing `accent` | **Option B: Add to API** | Illustrator Team |
| `/themes` extra palette fields | **Option A: Add to Contract** | Illustrator Team |

---

## Director's Illustrator Service Usage

### What Director CURRENTLY Uses (Production)

| Endpoint | Purpose | Usage Location |
|----------|---------|----------------|
| `GET /health` | Health check | `IllustratorClient.health_check()` |
| `POST /v1.0/pyramid/generate` | Pyramid visualization | `IllustratorClient.generate_pyramid()` |
| `POST /v1.0/funnel/generate` | Funnel visualization | Via `IllustratorServiceAdapter` |
| `POST /v1.0/concentric_circles/generate` | Concentric circles | Via `IllustratorServiceAdapter` |
| `POST /concept-spread/generate` | Concept spread | Via `IllustratorServiceAdapter` |

### Planned Service Coordination Usage (Future)

Per `SERVICE_COORDINATION_REQUIREMENTS.md`, Director's service coordination architecture plans to use:

| Endpoint | Planned Purpose | Current Status |
|----------|-----------------|----------------|
| `GET /capabilities` | Runtime service discovery | **NOT YET IMPLEMENTED** - using static registry |
| `GET /api/ai/illustrator/types` | Dynamic type availability | **NOT YET IMPLEMENTED** - using static registry |
| `GET /v1.0/themes` | Theme discovery | **NOT YET IMPLEMENTED** - passed from user context |
| `POST /v1.0/can-handle` | Content negotiation | **NOT YET IMPLEMENTED** - using Text Service's can-handle |

**Current Implementation**: Director uses `config/unified_variant_registry.json` (static file) instead of live endpoint calls for capability discovery. The `UnifiedSlideClassifier` builds a keyword index from this registry at startup.

**Future Implementation**: The service coordination architecture documents runtime capability discovery via `/capabilities` endpoints on all services. When implemented, these endpoints will be called during strawman generation to understand what each service can handle.

### Response Field Handling

Director's `LayoutPayloadAssembler._extract_infographic_html()` uses this fallback chain:

```python
# Priority order (from layout_payload_assembler.py lines 629-646):
1. content.get("infographic_html")  # v1.0.2 standard
2. content.get("html")               # v1.0.0 legacy
3. content.get("svg_content")        # Fallback
```

**This means**: As long as responses include `infographic_html` (which v1.0.2 does), Director integration works correctly.

---

## Detailed Guidance Per Deviation

### 1. GET /capabilities - Nested Structure Mismatch

**Contract Expects**:
```json
{
  "capabilities": { "pyramid": {...}, "funnel": {...}, ... },
  "content_signals": { "topic_count_ranges": {...}, ... },
  "specializations": { "data_pattern_detection": {...}, ... },
  "endpoints": { "capabilities_check": "...", ... }
}
```

**API Returns**:
```json
{
  "capabilities": { "ai_generated_content": {...}, "slide_types": [...], ... },
  "content_signals": { "handles_well": [...], "handles_poorly": [...], ... },
  "specializations": { "pyramid": {...}, "funnel": {...}, ... },
  "endpoints": { "can_handle": "...", "pyramid": "...", ... }
}
```

**Recommendation**: **Option A - Update Contract**

**Rationale**:
- Director does NOT currently call `/capabilities` endpoint (uses static registry)
- **However**, the service coordination architecture plans to use this endpoint for runtime discovery
- The actual API structure provides more useful information (slide_types, visualization_types)
- When Director implements live capability discovery, it will need to parse the ACTUAL response
- Changing API to match outdated contract is counterproductive

**Action**: Update `ILLUSTRATOR_SERVICE_CAPABILITIES.md` section 2.1 to document actual response structure. This ensures that when Director implements runtime capability discovery, the documentation accurately describes what the API returns.

---

### 2. pyramid/funnel Extra Metadata Fields

**Extra Fields in Response**:
- `metadata.attempts` - Number of LLM retry attempts
- `metadata.generation_time_ms` - LLM generation time
- `metadata.model` - LLM model used
- `metadata.usage` - Token usage stats

**Recommendation**: **Option A - Keep & Document**

**Rationale**:
- Director logs `generation_time_ms` for monitoring (see `IllustratorClient.generate_pyramid()` line 203)
- These fields are valuable for debugging and cost tracking
- ~200 bytes overhead is negligible vs value provided
- No breaking change risk - clients can ignore extra fields

**Action**: Add these fields to `ILLUSTRATOR_SERVICE_CAPABILITIES.md` as "optional diagnostic fields".

**Example Documentation**:
```markdown
#### Diagnostic Metadata (Optional)

The following fields are included for monitoring and debugging:

| Field | Type | Description |
|-------|------|-------------|
| `attempts` | integer | Number of LLM generation attempts |
| `generation_time_ms` | integer | Total LLM generation time in milliseconds |
| `model` | string | LLM model used (e.g., "gemini-1.5-flash-002") |
| `usage` | object | Token usage: `{prompt_tokens, completion_tokens}` |
```

---

### 3. GET /api/ai/illustrator/types - Missing Keys

**Missing from API** (contract says these exist):
- `horizontal_cycle`
- `vertical_list`
- `circle_process`
- `linear_flow`

**Recommendation**: **Option A - Update Contract (Remove)**

**Rationale**:
- These types were apparently planned but never implemented
- No client is requesting them (would fail immediately)
- Director's static registry (`unified_variant_registry.json`) doesn't include these types
- When Director implements live `/types` discovery, it will expect the API to accurately reflect available types
- Removing from contract reflects reality

**Action**: Remove these 4 types from `ILLUSTRATOR_SERVICE_CAPABILITIES.md` section on available types.

**Important Note**: If these types ARE planned for future implementation, add them to a "Roadmap" section instead of removing entirely. This helps Director team plan for future registry updates.

---

### 4. GET /api/ai/illustrator/types - Extra Keys

**Extra in API** (not in contract):
- `comparison`, `cycle`, `hierarchy`, `list`, `matrix`
- `process`, `roadmap`, `statistics`, `timeline`, `venn`

**Recommendation**: **Option A - Add to Contract**

**Rationale**:
- These are real capabilities that clients can use
- Director's LayoutAnalyzer may route to these in future
- Documenting enables proper integration
- No downside to documenting available features

**Action**: Add these 10 new visualization types to `ILLUSTRATOR_SERVICE_CAPABILITIES.md` with their:
- Description
- Typical use case
- Parameter requirements
- Example output structure

---

### 5. GET /v1.0/themes - Missing `accent` Field

**Contract Expects**: `palette.accent`
**API Returns**: No `accent` field

**Recommendation**: **Option B - Add to API**

**Rationale**:
- Theme palettes should be complete and consistent
- `accent` is a standard design system color (for CTAs, highlights)
- Other clients/services may expect `accent` to exist
- Easy to add - just include a derived/default accent color

**Implementation Suggestion**:
```python
# In theme response builder
palette = {
    "primary": theme.primary,
    "secondary": theme.secondary,
    "background": theme.background,
    "text": theme.text,
    "accent": theme.accent or theme.primary,  # Default to primary if not set
    # ... existing extra fields
}
```

**Action**: Add `accent` field to theme palette responses. Can be derived from `primary` if not explicitly defined.

---

### 6. GET /v1.0/themes - Extra Palette Fields

**Extra in API**:
- `border`, `danger`, `success`, `text_on_primary`, `warning`

**Recommendation**: **Option A - Add to Contract**

**Rationale**:
- These are useful extended theme properties
- Enable richer styling capabilities
- Following design system best practices
- No breaking change - clients can ignore if not needed

**Action**: Add these fields to `ILLUSTRATOR_SERVICE_CAPABILITIES.md` as "Extended Palette Properties":

```markdown
#### Extended Palette Properties

| Field | Type | Description |
|-------|------|-------------|
| `border` | string | Border color for containers |
| `danger` | string | Error/destructive action color |
| `success` | string | Success/positive action color |
| `text_on_primary` | string | Text color for use on primary background |
| `warning` | string | Warning/caution color |
```

---

## Summary of Recommended Actions

### For Illustrator Team

| Priority | Action | File to Update |
|----------|--------|----------------|
| HIGH | Document actual `/capabilities` structure | `ILLUSTRATOR_SERVICE_CAPABILITIES.md` |
| HIGH | Add 10 new visualization types to docs | `ILLUSTRATOR_SERVICE_CAPABILITIES.md` |
| MEDIUM | Add diagnostic metadata fields to docs | `ILLUSTRATOR_SERVICE_CAPABILITIES.md` |
| MEDIUM | Add `accent` field to theme palettes | API response code |
| LOW | Remove 4 unimplemented types from docs | `ILLUSTRATOR_SERVICE_CAPABILITIES.md` |
| LOW | Document extended palette properties | `ILLUSTRATOR_SERVICE_CAPABILITIES.md` |

### No Director Changes Required

Director's integration with Illustrator is functioning correctly:
- Generation endpoints return expected `infographic_html` field
- Fallback chain handles legacy `html` field
- Extra metadata fields are logged but not required
- Unused endpoints (`/capabilities`, `/types`, `/themes`) don't affect Director

---

## Current Integration Status

| Integration Point | Status | Notes |
|-------------------|--------|-------|
| Director → Illustrator (visual generation) | **WORKING** | v1.0.2 `infographic_html` alias supported |
| Layout Service ← Illustrator | **WORKING** | `infographic_html` field present |
| Director parsing `/capabilities` | N/A | Director doesn't use this endpoint |
| Layout Service parsing `/types` | N/A | Layout Service doesn't use this endpoint |

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-20 | 1.0 | Initial guidance document |

---

**Contact**: Director Agent Team
**Related Docs**:
- `docs/SERVICE_REQUIREMENTS_ILLUSTRATOR.md` (v2.0)
- `docs/THREE_WAY_ALIGNMENT_ANALYSIS_ILLUSTRATOR.md`
- `src/utils/layout_payload_assembler.py` (v4.4)
