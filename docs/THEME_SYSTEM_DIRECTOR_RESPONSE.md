# Director's Response: Theme System Architecture

**Document**: Response to `THEME_SYSTEM_DESIGN.md` v2.1
**From**: Director Service Team
**To**: Text Service Team (cc: Layout Service, Frontend)
**Date**: December 20, 2024
**Status**: Action Plan & Clarification Request

---

## Executive Summary

We've reviewed the Theme System Design document and **confirm alignment with Director's orchestration capabilities**. The four-dimension approach (Theme, Audience, Purpose, Time) maps naturally to context we already extract during strawman generation.

**Director commits to implementing the required responsibilities in three phases**, with Phase 1 starting immediately. However, we need clarity from Text Service on parameter readiness before proceeding to integration phases.

---

## Context: Where Director Fits

```
┌─────────────────────────────────────────────────────────────────┐
│                    THEME SYSTEM DATA FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Frontend                                                         │
│     │ theme_id, audience_type, purpose_type, duration            │
│     ▼                                                             │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │                      DIRECTOR                            │     │
│  │                                                          │     │
│  │  STRAWMAN STAGE:                                         │     │
│  │  • Extract audience, purpose, duration (ALREADY DONE)    │     │
│  │  • NEW: Capture theme_id                                 │     │
│  │  • NEW: Build ContentContext from extracted values       │     │
│  │  • NEW: Expand theme_id → full theme_config              │     │
│  │                                                          │     │
│  │  CONTENT GENERATION:                                     │     │
│  │  • NEW: Pass theme_config to Text Service                │     │
│  │  • NEW: Pass content_context to Text Service             │     │
│  │  • NEW: Pass styling_mode to Text Service                │     │
│  │  • NEW: Pass available_space to Text Service             │     │
│  └─────────────────────────────────────────────────────────┘     │
│     │                                                             │
│     │ theme_config, content_context, styling_mode, available_space│
│     ▼                                                             │
│  Text Service → generates themed, audience-aware content          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Key Insight**: Director already extracts `audience`, `duration`, `purpose`, and `tone` during decision engine processing. Adding `theme_id` and building structured `ContentContext` is a natural extension of existing workflow.

---

## Director's Phased Implementation Plan

### Phase 1: Foundation (No External Dependencies)

**Timeline**: Ready within 1 week of approval
**Dependencies**: None (Director-only changes)

| Deliverable | File | Description |
|-------------|------|-------------|
| ThemeConfig model | `src/models/theme_config.py` | TypographyLevel, ColorPalette, ThemeConfig |
| ContentContext model | `src/models/content_context.py` | AudienceConfig, PurposeConfig, TimeConfig |
| Theme Registry | `config/theme_registry.json` | Embedded presets (professional, executive, educational, children) |
| Session enhancement | `src/models/session.py` | Add `theme_id`, `content_context` fields |
| Strawman integration | `src/agents/decision_engine.py` | Build ContentContext at strawman stage |

**Phase 1 Output**: Director is READY to pass theme parameters. No breaking changes to existing flow.

---

### Phase 2: Text Service Integration

**Timeline**: 3-5 days after Text Service confirms parameter support
**Dependencies**: Text Service must support new parameters

| Deliverable | File | Description |
|-------------|------|-------------|
| Client updates | `src/utils/text_service_client_v1_2.py` | Add theme_config, content_context, styling_mode params |
| WebSocket updates | `src/handlers/websocket.py` | Pass new params in all Text Service calls |
| Fallback handling | All clients | Graceful degradation if Text Service returns errors |

**Phase 2 Output**: Full theme_config and content_context passed to Text Service. Initial `styling_mode: "inline_styles"` (safe default).

---

### Phase 3: Layout Service Integration

**Timeline**: 3-5 days after Layout Service provides endpoints
**Dependencies**: Layout Service must provide THEME_REGISTRY sync + available_space

| Deliverable | File | Description |
|-------------|------|-------------|
| Registry sync | `src/core/theme_registry.py` | Sync from Layout Service on startup |
| Space fetching | `src/clients/layout_service_client.py` | Get available_space per layout type |
| CSS mode enable | `src/handlers/websocket.py` | Switch to `styling_mode: "css_classes"` |
| Health check | `src/api/health.py` | Theme registry sync validation |

**Phase 3 Output**: Theme switching without regeneration. Full system integration.

---

## Director's SLA Commitments

| Commitment | SLA | Notes |
|------------|-----|-------|
| Phase 1 completion | **1 week** from approval | No blockers - internal only |
| Phase 2 completion | **3-5 days** from Text Service readiness confirmation | Depends on Q1 answer below |
| Phase 3 completion | **3-5 days** from Layout Service endpoint availability | Depends on Q3, Q4 answers below |
| Backward compatibility | **100%** | Existing presentations continue working |
| Fallback behavior | **Graceful degradation** | If Text Service doesn't support params, Director omits them |
| Default theme | `"professional"` | When user doesn't specify theme_id |
| Default styling_mode | `"inline_styles"` | Until Layout Service CSS is ready |

---

## Questions for Text Service Team

### Q1: Parameter Support Status (CRITICAL)

Does Text Service v1.2.2 currently support these parameters in `/v1.2/slides/*` endpoints?

| Parameter | Expected Type | Supported Today? |
|-----------|--------------|------------------|
| `theme_config` | Object (typography + colors) | ❓ |
| `content_context` | Object (audience + purpose + time) | ❓ |
| `styling_mode` | `"css_classes"` \| `"inline_styles"` | ❓ |
| `available_space` | `{width, height, unit}` | ❓ |

**If NOT supported today**: What is the implementation timeline? Director will hold Phase 2 until ready.

---

### Q2: Parameter Handling Behavior

If Director passes parameters that Text Service doesn't yet support:

- **Option A**: Text Service ignores unknown parameters (backward compatible)
- **Option B**: Text Service returns error for unknown parameters

**Which behavior should Director expect?** This determines our rollout strategy.

---

### Q3: Content Context Usage

How will Text Service use `content_context` to adapt content generation?

| Field | Expected Text Service Behavior |
|-------|-------------------------------|
| `audience.complexity_level` | Adjust vocabulary complexity? |
| `audience.max_sentence_words` | Enforce sentence length limits? |
| `audience.avoid_jargon` | Filter technical terms? |
| `purpose.include_cta` | Add call-to-action on closing slides? |
| `purpose.emotional_tone` | Adjust language tone? |
| `time.duration_minutes` | Adjust content depth/bullets? |

---

### Q4: CSS Classes Output Format

When `styling_mode: "css_classes"`, what CSS class names will Text Service output?

**Expected per document**:
```html
<h3 class="deckster-t1">Heading</h3>
<p class="deckster-t4">Body text</p>
<span class="deckster-emphasis">Highlighted</span>
```

**Confirm**: Is this the exact class naming convention Text Service will use?

---

### Q5: Theme Config Structure

Director will expand `theme_id` → `theme_config` with this structure:

```json
{
  "theme_id": "executive",
  "typography": {
    "hero_title": {"size": 84, "weight": 700, "color": "#ffffff", "family": "Inter"},
    "slide_title": {"size": 48, "weight": 700, "color": "#111827", "family": "Inter"},
    "slide_subtitle": {"size": 32, "weight": 400, "color": "#374151", "family": "Inter"},
    "t1": {"size": 32, "weight": 600, "color": "#111827", "family": "Inter"},
    "t2": {"size": 26, "weight": 600, "color": "#374151", "family": "Inter"},
    "t3": {"size": 22, "weight": 500, "color": "#4b5563", "family": "Inter"},
    "t4": {"size": 20, "weight": 400, "color": "#4b5563", "family": "Inter"}
  },
  "colors": {
    "primary": "#111827",
    "primary_light": "#f3f4f6",
    "accent": "#dc2626",
    "surface": "#f9fafb",
    "border": "#e5e7eb",
    "text_primary": "#111827",
    "text_secondary": "#374151"
  }
}
```

**Confirm**: Does this structure match what Text Service expects?

---

## Questions for Layout Service Team

### Q6: THEME_REGISTRY Sync Endpoint

Will Layout Service provide an endpoint for Director to sync theme presets?

```
GET /api/themes
→ Returns all theme presets (professional, executive, etc.)
```

**If yes**: What's the endpoint URL and response format?
**If no**: Should Director maintain embedded presets indefinitely?

---

### Q7: Available Space Endpoint

Will Layout Service provide content area dimensions per layout type?

```
GET /api/layouts/{layout_id}/content-area
→ Returns {width: 30, height: 14, unit: "grids"}
```

**If yes**: What's the endpoint URL and response format?
**If no**: Should Director hardcode content areas per layout?

---

## Proposed Request Format

Once all parties are ready, Director will send this to Text Service:

```json
{
  "slide_number": 3,
  "narrative": "Key benefits of our platform",
  "topics": ["Speed", "Reliability", "Cost"],
  "variant_id": "bullets",

  "styling_mode": "css_classes",

  "theme_config": {
    "theme_id": "executive",
    "typography": {
      "t1": {"size": 32, "weight": 600, "color": "#111827", "family": "Inter"},
      "t2": {"size": 26, "weight": 600, "color": "#374151", "family": "Inter"},
      "t3": {"size": 22, "weight": 500, "color": "#4b5563", "family": "Inter"},
      "t4": {"size": 20, "weight": 400, "color": "#4b5563", "family": "Inter"}
    },
    "colors": {
      "primary": "#111827",
      "accent": "#dc2626",
      "text_primary": "#111827",
      "text_secondary": "#374151"
    }
  },

  "content_context": {
    "audience": {
      "audience_type": "executive",
      "complexity_level": "moderate",
      "max_sentence_words": 15,
      "avoid_jargon": false
    },
    "purpose": {
      "purpose_type": "persuade",
      "include_cta": true,
      "emotional_tone": "enthusiastic"
    },
    "time": {
      "duration_minutes": 15
    }
  },

  "available_space": {
    "width": 30,
    "height": 14,
    "unit": "grids"
  }
}
```

---

## Next Steps

| Step | Owner | Action | Timeline |
|------|-------|--------|----------|
| 1 | Text Service | Answer Q1-Q5 above | ASAP |
| 2 | Layout Service | Answer Q6-Q7 above | ASAP |
| 3 | Director | Begin Phase 1 implementation | Immediately |
| 4 | All Teams | Sync call to align on timeline | After Q&A |

---

## Contact

**Director Team Lead**: Available in #director-service channel
**Document Location**: `agents/director_agent/v4.0/docs/THEME_SYSTEM_DIRECTOR_RESPONSE.md`

---

*This document is part of the cross-service Theme System implementation. Related documents:*
- *THEME_SYSTEM_DESIGN.md (Text Service)*
- *SLIDE_GENERATION_INPUT_SPEC.md (Layout Service)*
- *SERVICE_REQUIREMENTS_TEXT.md (Director)*
