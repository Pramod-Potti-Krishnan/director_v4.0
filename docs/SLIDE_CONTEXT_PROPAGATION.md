# Slide Context Propagation Architecture

**Version**: 1.0
**Date**: December 21, 2024
**Status**: Design Proposal
**Author**: Director Agent Team

---

## 1. Problem & Motivation

### The Parallel Generation Challenge

Director Agent v4.0+ generates all slides **in parallel** using `asyncio.gather()` for performance (~5s vs ~50s sequential). However, this creates a narrative continuity problem:

```
┌─────────────────────────────────────────────────────────────┐
│                    CURRENT STATE                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Slide 1 ──────►  Generated independently                  │
│   Slide 2 ──────►  Generated independently  (parallel)      │
│   Slide 3 ──────►  Generated independently                  │
│   Slide 4 ──────►  Generated independently                  │
│                                                             │
│   Result: Each slide is an island - no narrative awareness  │
└─────────────────────────────────────────────────────────────┘
```

### Symptoms of Missing Context

| Issue | Example |
|-------|---------|
| **Content repetition** | Slide 3 re-explains concepts from Slide 2 |
| **Inconsistent terminology** | "Users" in Slide 2, "Customers" in Slide 4 |
| **No narrative arc** | Each slide reads like a standalone document |
| **Missing transitions** | No "Building on..." or "As we saw..." connections |
| **Illustration disconnect** | Infographic doesn't reference earlier data points |

### Why This Matters

A great presentation tells a **story**. Each slide should:
- Know what came before (avoid repetition)
- Know what comes after (set up transitions)
- Understand its role in the narrative arc

---

## 2. Current Architecture

### Parallel Generation Flow

```python
# websocket.py:2043-2115 (simplified)
async def _generate_slide_content(self, slides, session):
    tasks = [
        self._generate_single_slide(idx, slide, session, total_slides)
        for idx, slide in enumerate(slides)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Existing Infrastructure (UNUSED)

**Critical Finding**: The infrastructure for passing context already exists in all service clients, but is currently unused.

| Service | Parameter | Location | Status |
|---------|-----------|----------|--------|
| Text Service | `previous_slides` | `text_service_client.py:135,153` | Exists, UNUSED |
| Illustrator | `previous_slides` in context | `illustrator_client.py:182` | Exists, UNUSED |
| Analytics | `previous_slides` in context | `analytics_client.py:59,167` | Exists, UNUSED |

### Current Context Passed to Services

Each slide currently receives:
```python
{
    "slide_number": 4,           # Position
    "total_slides": 10,          # Deck size
    "presentation_title": "...",  # Topic
    "tone": "professional",       # Style
    "audience": "executives",     # Target audience
    # NO previous_slides context!
}
```

---

## 3. Proposed Solution: Strawman-Based Narrative Context

### Core Insight

We can't pass *actual generated content* from previous slides (they're generated in parallel), but we CAN pass the **strawman plan** which contains:
- All slide titles and subtitles
- Slide purposes and types
- Key topics to be covered
- Narrative flow structure

This gives each slide **full visibility into the presentation arc** before any content is generated.

### Design Principles

1. **Lightweight** - Use plan metadata, not generated content
2. **Pre-computed** - Build context once before parallel generation
3. **Narrative-aware** - Include before AND after slides
4. **Service-specific** - Different services need different context depths

### Proposed Context Structure

```python
class NarrativeContext:
    """Lightweight context for slide-in-story positioning."""

    # Position
    current_slide_number: int      # 1-based
    total_slides: int

    # Narrative Arc (from strawman)
    previous_slides: List[SlideSummary]  # Slides before this one
    upcoming_slides: List[SlideSummary]  # Slides after this one

    # Role
    narrative_position: str  # "opening", "middle", "climax", "closing"
    section_context: Optional[str]  # "In the Problem section..."

class SlideSummary:
    """Minimal slide summary for context - NOT full content."""

    title: str                 # "Market Opportunity"
    purpose: str              # "establish_scale"
    slide_type: str           # "text", "chart", "diagram"
    key_theme: Optional[str]  # One-line summary
```

### Example Context for Slide 4 of 10

```json
{
  "current_slide_number": 4,
  "total_slides": 10,
  "narrative_position": "middle",
  "section_context": "We're in the 'Problem & Opportunity' section",

  "previous_slides": [
    {"title": "Welcome", "purpose": "title_slide", "type": "hero"},
    {"title": "The Problem", "purpose": "problem_statement", "type": "text"},
    {"title": "Market Size", "purpose": "establish_scale", "type": "chart"}
  ],

  "upcoming_slides": [
    {"title": "Our Solution", "purpose": "solution_intro", "type": "text"},
    {"title": "How It Works", "purpose": "technical_overview", "type": "diagram"},
    {"title": "Traction", "purpose": "proof_points", "type": "chart"},
    {"title": "Team", "purpose": "credibility", "type": "text"},
    {"title": "Financials", "purpose": "business_case", "type": "chart"},
    {"title": "The Ask", "purpose": "call_to_action", "type": "hero"}
  ],

  "context_hint": "This slide follows 'Market Size' and leads into 'Our Solution'. Focus on quantifying the opportunity without repeating market size data."
}
```

---

## 4. Director Responsibilities

### 4.1 Build Narrative Context Before Generation

```python
# In _generate_slide_content(), BEFORE asyncio.gather()
def _build_narrative_context(self, strawman: Dict, slide_idx: int) -> NarrativeContext:
    """Build lightweight context from strawman for a specific slide."""

    slides = strawman.get('slides', [])
    total = len(slides)

    # Extract summaries from strawman (no generation needed)
    all_summaries = [
        SlideSummary(
            title=s.get('title', f'Slide {i+1}'),
            purpose=s.get('purpose', s.get('slide_type_hint', 'content')),
            slide_type=s.get('service', 'text'),
            key_theme=s.get('notes', '')[:50] if s.get('notes') else None
        )
        for i, s in enumerate(slides)
    ]

    return NarrativeContext(
        current_slide_number=slide_idx + 1,
        total_slides=total,
        previous_slides=all_summaries[:slide_idx],
        upcoming_slides=all_summaries[slide_idx + 1:],
        narrative_position=self._determine_position(slide_idx, total),
        section_context=self._get_section_context(slides, slide_idx)
    )
```

### 4.2 Pass Context to Services

```python
# In _generate_single_slide()
narrative_ctx = self._build_narrative_context(strawman, idx)

# For Text Service
response = await text_service.generate_c1_text(
    variant_id=variant_id,
    slide_spec=slide_spec,
    presentation_spec=presentation_spec,
    context={
        "narrative": narrative_ctx.to_dict(),  # NEW
        "previous_slides": [s.to_dict() for s in narrative_ctx.previous_slides]
    }
)
```

### 4.3 Determine Narrative Position

```python
def _determine_position(self, idx: int, total: int) -> str:
    """Determine where this slide sits in the narrative arc."""
    ratio = idx / total

    if idx == 0:
        return "opening"
    elif idx == total - 1:
        return "closing"
    elif ratio < 0.3:
        return "setup"
    elif ratio < 0.7:
        return "development"
    else:
        return "resolution"
```

---

## 5. Text Service Responsibilities

### 5.1 Accept Narrative Context

The Text Service should accept and use narrative context in its generation prompts.

**Endpoint Changes**: None required - `context` parameter already exists.

**Prompt Enhancement**:

```
## NARRATIVE CONTEXT

You are generating Slide {current} of {total}.

**What came before:**
{for slide in previous_slides}
- Slide {slide.number}: "{slide.title}" ({slide.purpose})
{endfor}

**What comes next:**
{for slide in upcoming_slides[:3]}  # Limit to next 3
- Slide {slide.number}: "{slide.title}" ({slide.purpose})
{endfor}

**Your role:** {narrative_position}

**IMPORTANT:**
- Do NOT repeat information from previous slides
- Set up concepts that will be expanded in upcoming slides
- Use transitional language that connects to the narrative
- Maintain consistent terminology with previous slides
```

### 5.2 Use Context in Generation

The Text Service LLM prompt should:

1. **Avoid repetition**: "Previous slide covered [X], so focus on [Y]"
2. **Create transitions**: "Building on the market data, we now introduce..."
3. **Maintain consistency**: Use same terms/names as earlier slides
4. **Foreshadow**: "As we'll see in the next section..."

### 5.3 Example Enhanced Prompt

```
Generate content for Slide 4: "Our Solution"

NARRATIVE CONTEXT:
- You are in the "development" phase of this 10-slide pitch deck
- Previous slides established the PROBLEM (Slide 2) and MARKET SIZE (Slide 3)
- The audience has seen: "$50B market opportunity" and "Current solutions fail at scale"
- Next slide will cover "How It Works" (technical details)

YOUR TASK:
- Introduce the solution concept (DO NOT re-explain the problem)
- Connect to the market opportunity established earlier
- Set up the technical deep-dive coming next
- Avoid: Repeating market size figures, restating the problem

SLIDE SPEC:
- Title: "Our Solution"
- Topics: [AI-powered automation, Real-time processing, Enterprise-ready]
- Tone: confident, forward-looking
```

---

## 6. Illustrator Service Responsibilities

### 6.1 Narrative Continuity for Visuals

Illustrations and infographics benefit from narrative context to:
- **Reference earlier concepts**: Pyramid showing "Problem → Solution → Impact"
- **Maintain visual consistency**: Same color coding for recurring concepts
- **Position in story**: "This visualization synthesizes what we've covered"

### 6.2 Context Usage

```json
{
  "visualization_type": "pyramid",
  "narrative_context": {
    "position": "climax",
    "previous_themes": ["Problem identified", "Market validated", "Solution introduced"],
    "purpose": "synthesize_story"
  },
  "hint": "This pyramid should visually summarize the journey from problem to solution"
}
```

### 6.3 Service Adjustments

1. Accept `narrative_context` in request payload
2. Use context to inform:
   - Visual hierarchy (what to emphasize)
   - Labeling (reference earlier terminology)
   - Layout (synthesis vs introduction)

---

## 7. Analytics/Diagram Services

### 7.1 Minimal Impact

Charts and diagrams are more **data-driven** than **narrative-driven**. They're typically:
- "Double-clicking" on specific data points
- Self-contained visualizations
- Less dependent on narrative flow

### 7.2 When Context Helps

| Scenario | Context Value |
|----------|---------------|
| Sequential metrics | "This chart follows Q1 data, show Q2-Q4" |
| Comparative charts | "Earlier slide showed competitor X, now show us vs them" |
| Process diagrams | "Workflow should start where previous diagram ended" |

### 7.3 Recommendation

**Optional Context**: Analytics and Diagram services SHOULD accept narrative context but it's lower priority than Text and Illustrator services.

```python
# Optional - service can ignore if not relevant
context = {
    "narrative_hint": "This follows a chart showing market size",
    "data_continuity": "Use same axis scale as Slide 3 chart if applicable"
}
```

---

## 8. Implementation Approach

### Phase 1: Director Context Builder (Week 1)

**Goal**: Build narrative context from strawman, pass to services

| Task | Effort | Impact |
|------|--------|--------|
| Create `NarrativeContext` model | 2h | Foundation |
| Add `_build_narrative_context()` to websocket handler | 4h | Core logic |
| Pass context to Text Service calls | 2h | Integration |
| Add logging for context debugging | 1h | Observability |

### Phase 2: Text Service Enhancement (Week 2)

**Goal**: Text Service uses narrative context in prompts

| Task | Effort | Impact |
|------|--------|--------|
| Update prompt templates with context sections | 4h | Core value |
| Add context validation/parsing | 2h | Robustness |
| Test narrative awareness in outputs | 4h | Verification |
| Document context contract | 2h | Maintainability |

### Phase 3: Illustrator Integration (Week 3)

**Goal**: Illustrations reference narrative position

| Task | Effort | Impact |
|------|--------|--------|
| Accept narrative context in Illustrator API | 2h | Interface |
| Use context for visual synthesis prompts | 4h | Core value |
| Test visual consistency across deck | 4h | Quality |

### Phase 4: Optimization & Refinement (Week 4)

**Goal**: Tune context size, measure impact

| Task | Effort | Impact |
|------|--------|--------|
| Measure prompt size impact | 2h | Performance |
| A/B test with/without context | 8h | Validation |
| Tune context verbosity per service | 4h | Optimization |

---

## 9. Context Size Considerations

### Keep It Lightweight

**Goal**: Add narrative awareness without bloating prompts.

| Context Element | Recommended Size | Example |
|-----------------|------------------|---------|
| Previous slide summary | 1 line each | "Slide 2: 'The Problem' - established pain points" |
| Upcoming slides | Title + purpose only | "Coming: Our Solution, How It Works, Traction" |
| Section context | 1 sentence | "We're in the Problem & Opportunity section" |
| Narrative hint | 1-2 sentences | "This slide bridges problem to solution. Avoid repetition." |

**Total added context**: ~200-400 tokens per slide (acceptable overhead)

### Token Budget

```
┌─────────────────────────────────────────────────┐
│          PROMPT TOKEN ALLOCATION                │
├─────────────────────────────────────────────────┤
│  Existing content:        ~2000 tokens          │
│  + Narrative context:     ~300 tokens  (NEW)    │
│  = Total:                 ~2300 tokens          │
│                                                 │
│  Impact: +15% prompt size for narrative gain    │
└─────────────────────────────────────────────────┘
```

---

## 10. Success Metrics

### Qualitative

- [ ] Generated slides reference previous content appropriately
- [ ] Consistent terminology across deck
- [ ] Natural transitions ("Building on...", "As we discussed...")
- [ ] Illustrations that synthesize rather than isolate

### Quantitative

| Metric | Baseline | Target |
|--------|----------|--------|
| Content repetition rate | Unknown | Measure |
| Terminology consistency | Unknown | Measure |
| User satisfaction (narrative flow) | Unknown | +20% |
| Generation latency impact | 5s | <5.5s |

---

## 11. Summary

### What Changes

| Component | Change |
|-----------|--------|
| **Director** | Builds `NarrativeContext` from strawman, passes to services |
| **Text Service** | Uses context to avoid repetition, create transitions |
| **Illustrator** | Uses context for visual synthesis and consistency |
| **Analytics/Diagram** | Optional context for data continuity |

### What Stays Same

- Parallel generation architecture (performance preserved)
- Service APIs (additive context parameter)
- Strawman structure (already has needed data)

### Key Insight

The strawman IS the narrative plan. We just need to expose it to each slide generation call in a lightweight, structured format.

---

## Appendix: Sample Code

### A. NarrativeContext Model

```python
from pydantic import BaseModel
from typing import List, Optional

class SlideSummary(BaseModel):
    """Minimal slide info for narrative context."""
    slide_number: int
    title: str
    purpose: str
    slide_type: str  # text, chart, diagram, infographic, hero
    key_theme: Optional[str] = None

class NarrativeContext(BaseModel):
    """Lightweight narrative positioning for a slide."""
    current_slide_number: int
    total_slides: int
    narrative_position: str  # opening, setup, development, resolution, closing
    section_context: Optional[str] = None
    previous_slides: List[SlideSummary] = []
    upcoming_slides: List[SlideSummary] = []

    def to_prompt_text(self) -> str:
        """Convert to human-readable prompt section."""
        lines = [
            f"Slide {self.current_slide_number} of {self.total_slides}",
            f"Position: {self.narrative_position}",
        ]

        if self.previous_slides:
            lines.append("\nPrevious slides covered:")
            for s in self.previous_slides[-3:]:  # Last 3 only
                lines.append(f"  - {s.title} ({s.purpose})")

        if self.upcoming_slides:
            lines.append("\nComing next:")
            for s in self.upcoming_slides[:2]:  # Next 2 only
                lines.append(f"  - {s.title} ({s.purpose})")

        return "\n".join(lines)
```

### B. Context Builder

```python
def build_narrative_context(
    strawman: Dict,
    slide_idx: int
) -> NarrativeContext:
    """Build narrative context from strawman for a specific slide."""

    slides = strawman.get('slides', [])
    total = len(slides)

    summaries = [
        SlideSummary(
            slide_number=i + 1,
            title=s.get('title', f'Slide {i+1}'),
            purpose=s.get('purpose', s.get('slide_type_hint', 'content')),
            slide_type=s.get('service', 'text'),
            key_theme=s.get('notes', '')[:50] if s.get('notes') else None
        )
        for i, s in enumerate(slides)
    ]

    # Determine position in arc
    if slide_idx == 0:
        position = "opening"
    elif slide_idx == total - 1:
        position = "closing"
    elif slide_idx / total < 0.3:
        position = "setup"
    elif slide_idx / total < 0.7:
        position = "development"
    else:
        position = "resolution"

    return NarrativeContext(
        current_slide_number=slide_idx + 1,
        total_slides=total,
        narrative_position=position,
        previous_slides=summaries[:slide_idx],
        upcoming_slides=summaries[slide_idx + 1:]
    )
```
