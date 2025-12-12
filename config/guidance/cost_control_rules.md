# Cost Control Rules

This document defines strict rules for controlling costs in the Director Agent v4.0.

## Tool Cost Tiers

### LOW Cost (Always Allowed)
These tools are cheap and can be called freely:

| Tool ID | Description | Typical Latency |
|---------|-------------|-----------------|
| `conversation.respond` | Conversational response | ~100ms |
| `conversation.ask_questions` | Generate clarifying questions | ~200ms |
| `conversation.propose_plan` | Generate plan proposal | ~300ms |

**Rule**: No approval required. Use judgment based on context.

### MEDIUM Cost (After Strawman Approved)
These tools have moderate cost and should be used purposefully:

| Tool ID | Description | Typical Latency |
|---------|-------------|-----------------|
| `illustrator.generate_pyramid` | Pyramid visualization | ~2s |
| `illustrator.generate_funnel` | Funnel visualization | ~2s |
| `illustrator.generate_concentric` | Concentric circles | ~2s |
| `deck.create_presentation` | Render final deck | ~3s |
| `deck.get_preview_url` | Generate preview URL | ~1s |

**Rule**: Only invoke after strawman exists and user has approved outline.

### HIGH Cost (Explicit Approval Required)
These tools are expensive and require explicit user approval:

| Tool ID | Description | Typical Latency |
|---------|-------------|-----------------|
| `text.generate_content` | Generate slide HTML | ~3s/slide |
| `text.generate_hero_title` | Generate title slide | ~3s |
| `text.generate_hero_section` | Generate section divider | ~3s |
| `text.generate_hero_closing` | Generate closing slide | ~3s |
| `analytics.generate_chart` | Generate Chart.js chart | ~2s |
| `analytics.generate_d3` | Generate D3.js visualization | ~3s |

**Rule**: NEVER call without explicit user approval.

---

## Approval Detection

### Explicit Approval Phrases
The following indicate user wants to proceed with generation:

- "generate"
- "generate the slides"
- "create it"
- "create the presentation"
- "proceed"
- "go ahead"
- "looks good, generate"
- "yes, make it"
- "build it"
- "let's do it"

### NOT Approval (Requires More Confirmation)
These do NOT constitute approval for HIGH cost tools:

- "looks good" (alone, without "generate")
- "yes" (to a question, not explicit generation request)
- "ok" / "okay"
- "sounds good"
- "that works"

**When uncertain**, ask explicitly:
> "Ready to generate the actual slide content? This will create the presentation."

---

## Guardrails

### Confidence Threshold
- For HIGH cost tools: Confidence must be >= 0.95
- If confidence < 0.95: Ask for confirmation

### Prerequisites
Before calling tools, verify prerequisites are met:

| Tool Category | Prerequisites |
|---------------|---------------|
| `text.generate_*` | `has_strawman = true` AND explicit approval |
| `illustrator.*` | `has_strawman = true` |
| `analytics.*` | `has_strawman = true` AND explicit approval |
| `deck.*` | `has_content = true` OR strawman with rendered slides |

### Rate Limiting
- Maximum 1 generation request per user message
- Batch slide generation when possible
- Don't regenerate unchanged slides on refinement

---

## Regeneration Rules

### Full Regeneration
Only regenerate entire presentation when:
- User explicitly requests "start over"
- User changes topic completely
- User requests fundamental restructure

### Partial Regeneration
For minor changes:
- Only regenerate affected slides
- Preserve unchanged content
- Explain what will be regenerated

### Never Regenerate
- On simple acknowledgments ("ok", "thanks")
- When user is asking a question
- When user is exploring options

---

## Cost Optimization Strategies

### 1. Batch Operations
When generating multiple slides:
```
GOOD: Generate all 10 slides in parallel
BAD: Generate one slide, ask, generate another, ask...
```

### 2. Incremental Refinement
When user requests changes:
```
GOOD: "I'll update slides 3 and 5 with your feedback"
BAD: "I'll regenerate all slides with your feedback"
```

### 3. Preview Before Generate
When strawman is approved:
```
GOOD: Show preview URL first, then offer to generate content
BAD: Immediately generate all content
```

### 4. Smart Defaults
Use sensible defaults to reduce iterations:
- Professional tone unless specified
- 8-12 slides for standard presentations
- Balanced visual variety

---

## Enforcement

The Decision Engine MUST:
1. Check tool cost tier before invocation
2. Verify prerequisites are met
3. Confirm explicit approval for HIGH cost tools
4. Log all tool invocations for monitoring
5. Reject requests that violate guardrails

### Violation Handling
If a tool call would violate rules:
1. Do NOT make the call
2. Respond to user explaining what's needed
3. Ask for explicit approval if that's the blocker

---

## Monitoring Metrics

Track these for cost optimization:
- Tool calls per session
- Tool calls per slide generated
- Regeneration rate
- Approval-to-generation ratio
- Cost per presentation

---

*These rules protect both user experience and system costs. Always err on the side of asking rather than assuming.*
