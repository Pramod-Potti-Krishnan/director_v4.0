# Analytics Service API Contract Guidance

**From**: Director Agent Team
**To**: Analytics Service Team
**Re**: API Contract Exactness Report - Director's Guidance
**Date**: December 20, 2024
**Reference**: Exactness Report showing 6/7 endpoints FAIL (85.7%)

---

## Executive Summary

After analyzing Director's actual usage of Analytics Service responses, we identify **one CRITICAL issue** and provide guidance on all discrepancies.

### Critical Finding

**FIELD ALIASES ARE NOT DEPLOYED** - This is the most important issue.

Director's `layout_payload_assembler.py` (v4.4) expects these aliases per the v3.0 contract:
- `chart_html` → alias for `element_3`
- `element_4` → alias for `element_3` (for L02 SPEC compliance)
- `body` → alias for `element_2`

**The exactness report confirms these aliases are NOT present in responses.** Director currently works because it falls back to `element_3`/`element_2`, but the documented aliases should be deployed.

### Priority Matrix

| Issue | Priority | Impact |
|-------|----------|--------|
| Missing field aliases (chart_html, element_4, body) | **CRITICAL** | Director expects these per v3.0 contract |
| num_points ignored in synthetic/generate | **HIGH** | Logic bug - returns 4 instead of requested 8 |
| Health/stats field name mismatches | MEDIUM | Monitoring only - not breaking |
| Extra metadata fields | LOW | Director ignores - safe to keep |
| chart-types key renames | LOW | Director doesn't parse this endpoint |

---

## Detailed Analysis

### What Director ACTUALLY Uses

**Content Fields** (from `layout_payload_assembler.py` lines 400-485):

| Field | Used For | Fallback | Status |
|-------|----------|----------|--------|
| `chart_html` | C3-chart, V2-chart-text | `element_3` | **MISSING** - add alias |
| `element_4` | L02 (SPEC compliance) | `element_3` | **MISSING** - add alias |
| `body` | V2-chart-text insights | `element_2` | **MISSING** - add alias |
| `element_3` | All chart layouts (legacy) | - | Present ✅ |
| `element_2` | L02 observations | - | Present ✅ |

**Metadata Fields** - Director passes through generically, doesn't consume individually:
- All extra metadata fields are safe to keep or remove
- `metadata.service` is documented but Director doesn't require it

---

## Recommendations Per Endpoint

### 1. POST /api/v1/analytics/L02/{type} - **CRITICAL FIX NEEDED**

**Current Response**:
```json
{
  "content": {
    "element_3": "<canvas>...",
    "element_2": "<p>Observations..."
  }
}
```

**Required Response** (add aliases):
```json
{
  "content": {
    "element_3": "<canvas>...",
    "element_2": "<p>Observations...",
    "chart_html": "<canvas>...",      // ADD: alias for element_3
    "element_4": "<canvas>...",       // ADD: alias for element_3 (L02 SPEC)
    "body": "<p>Observations..."      // ADD: alias for element_2
  }
}
```

**Action**: Add 3 field aliases to response. This is documented in contract v3.1.5 but not deployed.

---

### 2. POST /api/v1/preview/{chart_type} - **CRITICAL FIX NEEDED**

Same as above - add `chart_html`, `element_4`, `body` aliases to `content` object.

---

### 3. POST /api/v1/synthetic/generate - **HIGH PRIORITY BUG**

**Issue**: `num_points` parameter is ignored

**Contract says**: Return 8 data points when `num_points: 8`
**Actual**: Returns 4 data points regardless

**Action**: Fix the synthetic data generator to respect `num_points` parameter.

---

### 4. GET /health - **MEDIUM: Documentation Update**

**Current Response**:
```json
{
  "jobs": {
    "total_jobs": 0,
    "queued": 0,
    "processing": 0,
    "completed": 0,
    "failed": 0
  }
}
```

**Contract Says**:
```json
{
  "jobs": {
    "active": 2,
    "completed": 145,
    "failed": 3
  }
}
```

**Recommendation**: **Update documentation** to match actual response.

**Rationale**:
- Director uses this for health checks (status code 200)
- Doesn't parse individual job count fields
- `queued + processing` is more informative than single `active`
- No code change needed - documentation update only

---

### 5. GET /stats - **MEDIUM: Documentation Update**

Same as /health - update documentation to match actual field names:
- `total_jobs` instead of implied structure
- `queued`, `processing` instead of `active`
- Add `average_time_ms` to API response OR remove from docs

**Recommendation**: Add `average_time_ms` to API (useful metric) and update other field names in docs.

---

### 6. GET /api/v1/chart-types - **LOW: Documentation Update**

**Key Renames**:
- `total` → `total_chart_types`
- `chartjs_count` → `chartjs_types`
- `layouts` → `supported_layouts`

**Missing**: `d3_count`
**Extra**: `l02_compatible`, `chart_libraries`

**Recommendation**: **Update documentation** to match actual response.

**Rationale**:
- Director doesn't parse this endpoint (uses static registry)
- Actual field names are more descriptive
- Extra fields (`l02_compatible`, `chart_libraries`) are useful

---

### 7. Extra Metadata Fields - **LOW: Keep and Document**

**Extra fields in L02 and preview responses**:
- `metadata.analytics_type`
- `metadata.chart_library`
- `metadata.model_used`
- `metadata.theme`
- `metadata.generated_at`
- `metadata.interactive_editor`

**Recommendation**: **Keep and document** these fields.

**Rationale**:
- Director doesn't consume them specifically (passes through generically)
- Useful for debugging and monitoring
- No breaking change risk
- Add to documentation as "Diagnostic Metadata"

---

## Summary of Required Actions

### Analytics Team - Code Changes

| Priority | Action | Endpoint |
|----------|--------|----------|
| **CRITICAL** | Add `chart_html` alias (copy of `element_3`) | L02, preview |
| **CRITICAL** | Add `element_4` alias (copy of `element_3`) | L02, preview |
| **CRITICAL** | Add `body` alias (copy of `element_2`) | L02, preview |
| **HIGH** | Fix `num_points` parameter handling | synthetic/generate |
| MEDIUM | Add `average_time_ms` to stats response | /stats |

### Analytics Team - Documentation Updates

| Priority | Action | File |
|----------|--------|------|
| MEDIUM | Update /health field names | ANALYTICS_SERVICE_CAPABILITIES.md |
| MEDIUM | Update /stats field names | ANALYTICS_SERVICE_CAPABILITIES.md |
| LOW | Update /chart-types field names | ANALYTICS_SERVICE_CAPABILITIES.md |
| LOW | Document extra metadata fields | ANALYTICS_SERVICE_CAPABILITIES.md |

### No Director Changes Needed

Director's fallback chains already handle the current responses:
- `chart_html` falls back to `element_3` ✅
- `element_4` falls back to `element_3` ✅
- `body` falls back to `element_2` ✅

However, the aliases SHOULD be added for contract compliance and future-proofing.

---

## Director's Field Usage Reference

### Fields Director ACTIVELY Uses

| Field | Layout | Purpose | Fallback |
|-------|--------|---------|----------|
| `chart_html` | C3-chart, V2-chart-text | Chart HTML | `element_3` |
| `element_4` | L02 | SPEC-compliant chart slot | `element_3` |
| `body` | V2-chart-text | Text insights | `element_2` |
| `element_3` | All (legacy) | Chart HTML | - |
| `element_2` | L02, V2 | Observations | - |

### Fields Director Does NOT Use (Safe to Modify)

| Field | Status |
|-------|--------|
| `metadata.analytics_type` | Passed through, not consumed |
| `metadata.chart_library` | Passed through, not consumed |
| `metadata.model_used` | Passed through, not consumed |
| `metadata.theme` | Passed through, not consumed |
| `metadata.generated_at` | Passed through, not consumed |
| `metadata.interactive_editor` | Passed through, not consumed |
| `metadata.service` | Documented but not used |

---

## Contract Accuracy After Fixes

| Endpoint | Current | After Fix |
|----------|---------|-----------|
| GET /health | FAIL | PASS (doc update) |
| GET /stats | FAIL | PASS (add field + doc) |
| GET /api/v1/chart-types | FAIL | PASS (doc update) |
| POST /api/v1/synthetic/generate | FAIL | PASS (fix num_points) |
| GET /api/charts/get-data/{id} | PASS | PASS ✅ |
| POST /api/v1/analytics/L02/{type} | FAIL | PASS (add aliases) |
| POST /api/v1/preview/{chart_type} | FAIL | PASS (add aliases) |

**After fixes: 7/7 PASS (100%)**

---

## Path Forward

1. **CRITICAL** (Day 1): Add field aliases (`chart_html`, `element_4`, `body`) to L02 and preview endpoints
2. **HIGH** (Day 1): Fix `num_points` bug in synthetic generator
3. **MEDIUM** (Week 1): Update documentation for health, stats, chart-types endpoints
4. **LOW** (Week 1): Document extra metadata fields

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-20 | 1.0 | Initial guidance document |

---

**Contact**: Director Agent Team
**Related Docs**:
- `docs/ANALYTICS_SERVICE_CAPABILITIES.md` (v3.1.5)
- `docs/SERVICE_REQUIREMENTS_ANALYTICS.md` (v2.0)
- `docs/THREE_WAY_ALIGNMENT_ANALYSIS_ANALYTICS.md`
- `src/utils/layout_payload_assembler.py` (v4.4)
