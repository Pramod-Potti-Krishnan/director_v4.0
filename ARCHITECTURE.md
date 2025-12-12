# Director Agent v4.0 - Architecture Documentation

## Executive Summary

Director Agent v4.0 transforms the presentation assistant from a **rigid 6-stage state machine** (v3.4) into a **flexible, MCP-style decision engine**. The AI now makes context-aware decisions about what action to take, rather than following predetermined state transitions.

---

## How v4.0 Works

### The Core Concept

Instead of:
```
State A → State B → State C → State D → ...
```

v4.0 uses:
```
User Message → AI Analyzes Context → Decides Best Action → Executes
                       ↑                                       |
                       └───────────────────────────────────────┘
```

The AI has **guidance** (best practices) not **gates** (forced transitions).

---

## Architecture Components

### 1. Decision Engine (`src/agents/decision_engine.py`)

The brain of v4.0. A single AI agent that:

1. **Receives** the user's message and session context
2. **Analyzes** what the user wants and what progress has been made
3. **Decides** which action to take (from 7 possible actions)
4. **Validates** the decision against cost control rules
5. **Returns** a structured decision to execute

```python
# Simplified flow
async def decide(context: DecisionContext) -> DecisionOutput:
    # 1. Detect if user is giving approval
    approval_result = detect_approval(user_message)

    # 2. Build prompt with all context
    prompt = build_decision_prompt(context, approval_result)

    # 3. Ask AI to decide
    decision = await agent.run(prompt)

    # 4. Validate against guardrails
    decision = validate_decision(decision, context)

    return decision
```

#### Available Actions (ActionType)

| Action | Description | When Used |
|--------|-------------|-----------|
| `RESPOND` | Conversational reply | General chat, acknowledgments |
| `ASK_QUESTIONS` | Gather information | Topic unclear, missing context |
| `PROPOSE_PLAN` | Suggest structure | Ready to outline presentation |
| `GENERATE_STRAWMAN` | Create slide outline | User approves plan |
| `REFINE_STRAWMAN` | Modify outline | User wants changes |
| `INVOKE_TOOLS` | Call content services | User approves generation |
| `COMPLETE` | Mark finished | Presentation delivered |

### 2. Guidance System (`config/guidance/`)

Like CLAUDE.md for Claude Code - markdown files that shape AI behavior without hard-coding logic.

**`director_guidance.md`** - Best practices for conversation:
- When to ask clarifying questions
- When to propose a plan
- When to generate content
- Communication style guidelines
- Off-topic handling

**`cost_control_rules.md`** - Guardrails for expensive operations:
- Never call HIGH cost tools without approval
- Explicit vs soft approval phrases
- Cost tier definitions
- Prerequisites for each tool

### 3. Tool Registry (`src/tools/`)

Services are wrapped as **registered tools** with:
- **Cost tiers** (LOW, MEDIUM, HIGH)
- **Approval requirements**
- **Prerequisites** (what context is needed)
- **Input schemas** (parameter validation)

```
┌────────────────────────────────────────────────────────────────┐
│                       Tool Registry                             │
├────────────────────────────────────────────────────────────────┤
│  LOW Cost (Always Allowed)                                      │
│  🟢 conversation.respond                                        │
│  🟢 conversation.ask_questions                                  │
│  🟢 conversation.propose_plan                                   │
├────────────────────────────────────────────────────────────────┤
│  MEDIUM Cost (After Strawman)                                   │
│  🟡 illustrator.generate_pyramid                                │
│  🟡 illustrator.generate_funnel                                 │
│  🟡 illustrator.generate_concentric                             │
│  🟡 deck.create_presentation                                    │
│  🟡 deck.get_preview_url                                        │
│  🟡 deck.update_slide                                           │
├────────────────────────────────────────────────────────────────┤
│  HIGH Cost (Requires Explicit Approval)                         │
│  🔴 text.generate_content                                       │
│  🔴 text.generate_hero_title                                    │
│  🔴 text.generate_hero_section                                  │
│  🔴 text.generate_hero_closing                                  │
│  🔴 analytics.generate_chart                                    │
│  🔴 analytics.generate_table                                    │
└────────────────────────────────────────────────────────────────┘
```

### 4. Session Model (`src/models/session.py`)

Replaces rigid `current_state` with **progress flags**:

```python
class SessionV4:
    # Progress flags (not states)
    has_topic: bool = False
    has_audience: bool = False
    has_duration: bool = False
    has_purpose: bool = False
    has_plan: bool = False
    has_strawman: bool = False
    has_explicit_approval: bool = False
    has_content: bool = False
    is_complete: bool = False

    # Flexible context storage
    context: Dict[str, Any] = {}
```

### 5. WebSocket Handler (`src/handlers/websocket.py`)

Routes messages through the Decision Engine:

```python
async def _process_message(websocket, session, data):
    # Build context for decision
    context = build_decision_context(session, user_message)

    # Get AI decision
    decision = await decision_engine.decide(context)

    # Execute the decision
    await execute_decision(websocket, session, decision)
```

---

## Decision Flow Diagram

```
                            ┌──────────────────┐
                            │   User Message   │
                            └────────┬─────────┘
                                     │
                                     ▼
                     ┌───────────────────────────────┐
                     │     Approval Detection        │
                     │  "generate" → explicit        │
                     │  "looks good" → soft          │
                     └───────────────┬───────────────┘
                                     │
                                     ▼
         ┌───────────────────────────────────────────────────────┐
         │                   Decision Engine                      │
         │  ┌─────────────────────────────────────────────────┐  │
         │  │              System Prompt                       │  │
         │  │  - Guidance System (best practices)              │  │
         │  │  - Cost Control Rules                            │  │
         │  │  - Tool Definitions                              │  │
         │  └─────────────────────────────────────────────────┘  │
         │                         +                              │
         │  ┌─────────────────────────────────────────────────┐  │
         │  │              Context                             │  │
         │  │  - User message                                  │  │
         │  │  - Session progress flags                        │  │
         │  │  - Conversation history                          │  │
         │  │  - Existing strawman (if any)                    │  │
         │  └─────────────────────────────────────────────────┘  │
         └───────────────────────────┬───────────────────────────┘
                                     │
                                     ▼
                     ┌───────────────────────────────┐
                     │     Decision Validation       │
                     │  - Check cost control         │
                     │  - Check prerequisites        │
                     │  - Block if no approval       │
                     └───────────────┬───────────────┘
                                     │
                                     ▼
    ┌────────────────────────────────┴─────────────────────────────┐
    │                                                               │
    ▼                    ▼                    ▼                     ▼
┌─────────┐      ┌──────────────┐    ┌──────────────┐      ┌──────────────┐
│ RESPOND │      │ASK_QUESTIONS │    │GENERATE_     │      │INVOKE_TOOLS  │
│         │      │              │    │STRAWMAN      │      │              │
│ Send    │      │ Send         │    │              │      │ Call Text    │
│ chat    │      │ questions    │    │ Generate     │      │ Service,     │
│ message │      │ to user      │    │ outline      │      │ Illustrator, │
│         │      │              │    │              │      │ etc.         │
└─────────┘      └──────────────┘    └──────────────┘      └──────────────┘
```

---

## v3.4 vs v4.0 Comparison

### Architecture

| Aspect | v3.4 | v4.0 |
|--------|------|------|
| **Control Flow** | State machine with fixed transitions | AI-driven decisions |
| **States** | 6 rigid states | 9 flexible progress flags |
| **LLM Agents** | 5 separate agents (one per state) | 1 Decision Engine |
| **Intent Router** | Hardcoded 9 intent types | Context-aware analysis |
| **Tool Invocation** | Implicit in state handlers | Explicit via Tool Registry |
| **Guidance** | Hardcoded in prompts | External markdown files |

### State Machine (v3.4) → Progress Flags (v4.0)

```
v3.4 States:                      v4.0 Progress Flags:
─────────────                     ────────────────────
PROVIDE_GREETING         →        (handled dynamically)
ASK_CLARIFYING_QUESTIONS →        has_topic, has_audience, has_duration, has_purpose
CREATE_CONFIRMATION_PLAN →        has_plan
GENERATE_STRAWMAN        →        has_strawman
REFINE_STRAWMAN          →        (same as has_strawman, tracked via history)
CONTENT_GENERATION       →        has_content, is_complete
```

### Cost Control

| v3.4 | v4.0 |
|------|------|
| Implicit (generate only in specific states) | Explicit cost tiers with approval requirements |
| No formal approval detection | Phrase-based approval detection (explicit vs soft) |
| State gates prevent premature generation | Decision validation blocks HIGH cost tools without approval |

---

## Capabilities Comparison

### Fully Preserved Capabilities

| Capability | v3.4 | v4.0 | Notes |
|------------|------|------|-------|
| WebSocket communication | ✅ | ✅ | Same protocol preserved |
| Session persistence (Supabase) | ✅ | ✅ | Uses `dr_sessions_v4` table |
| Greeting message | ✅ | ✅ | Handled by handler |
| Clarifying questions | ✅ | ✅ | `ASK_QUESTIONS` action |
| Confirmation plan | ✅ | ✅ | `PROPOSE_PLAN` action |
| Strawman generation | ✅ | ✅ | `GENERATE_STRAWMAN` action |
| Strawman refinement | ✅ | ✅ | `REFINE_STRAWMAN` action |
| Text Service integration | ✅ | ✅ | `text.*` tools |
| Illustrator integration | ✅ | ✅ | `illustrator.*` tools |
| Analytics integration | ✅ | ✅ | `analytics.*` tools |
| Deck Builder integration | ✅ | ✅ | `deck.*` tools |
| Message protocol (chat, status, slide_update) | ✅ | ✅ | Preserved from v3.4 |
| Ping/pong heartbeat | ✅ | ✅ | In WebSocket handler |
| Duplicate connection handling | ✅ | ✅ | In WebSocket handler |

### Enhanced Capabilities in v4.0

| Capability | v3.4 | v4.0 |
|------------|------|------|
| **Flexible conversation flow** | ❌ Rigid state order | ✅ AI decides best action |
| **Skip unnecessary steps** | ❌ Must follow sequence | ✅ Can skip if context sufficient |
| **Mid-flow questions** | ❌ Only in ASK_CLARIFYING state | ✅ Anytime AI deems necessary |
| **Natural conversation** | ❌ Intent classification | ✅ Context-aware decisions |
| **Configurable guidance** | ❌ Hardcoded in prompts | ✅ External markdown files |
| **Cost visibility** | ❌ Implicit | ✅ Explicit cost tiers |
| **Tool introspection** | ❌ No API | ✅ `/tools` endpoint |
| **Approval detection** | ❌ Intent-based | ✅ Phrase-based with confidence |

### Capabilities Not Yet Fully Migrated

| Capability | Status | Notes |
|------------|--------|-------|
| `skip_history` parameter | ⚠️ Removed | v4.0 uses session persistence instead |
| History replay on reconnect | ⚠️ Simplified | Sessions auto-restore from Supabase |
| Button action mapping | ⚠️ Generalized | AI handles all actions, no special mapping |

---

## Service Integration

### External Services (Preserved)

All v3.4 service integrations are preserved via tool wrappers:

| Service | Endpoint | v4.0 Tool |
|---------|----------|-----------|
| Text Service v1.2 | `/v1.2/generate` | `text.generate_content` |
| Text Service (Hero) | `/v1.2/hero/*` | `text.generate_hero_*` |
| Illustrator v1.0 | `/v1.0/{type}/generate` | `illustrator.generate_*` |
| Analytics v3 | `/analytics/v3/{engine}/generate` | `analytics.generate_*` |
| Deck Builder | `/api/presentations` | `deck.*` |

### Client Dependencies

The tool wrappers use existing clients from v3.4:
- `src/utils/text_service_client.py`
- `src/clients/illustrator_client.py`
- `src/clients/analytics_client.py`
- `src/utils/deck_builder_client.py`

---

## Configuration Files

### Tool Schemas (`config/tools/tool_schemas.json`)

Defines input/output schemas for each tool:
```json
{
  "tools": {
    "text.generate_content": {
      "name": "Generate Slide Content",
      "description": "Generate content for a slide using Text Service",
      "input_schema": {
        "type": "object",
        "properties": {
          "slide_id": {"type": "string"},
          "layout": {"type": "string"},
          "topics": {"type": "array"}
        }
      }
    }
  }
}
```

### Tool Costs (`config/tools/tool_costs.json`)

Defines cost tiers and approval rules:
```json
{
  "cost_tiers": {
    "low": {"requires_approval": false},
    "medium": {"requires_approval": false},
    "high": {"requires_approval": true}
  },
  "approval_phrases": {
    "explicit_approval": ["generate", "create it", "proceed", "make it"],
    "not_approval": ["looks good", "yes", "ok", "sure"]
  }
}
```

---

## Running v4.0

### Prerequisites

```bash
# Same as v3.4
pip install -r requirements.txt
```

### Environment Variables

Same as v3.4:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `GCP_PROJECT_ID`
- `GCP_SERVICE_ACCOUNT_JSON` (for production)

### Start Server

```bash
cd director_agent/v4.0
python main.py
```

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | API info with v4.0 architecture details |
| `GET /health` | Health check with tool count |
| `GET /version` | Version info |
| `GET /tools` | List all registered tools |
| `GET /test-handler` | Test handler initialization |
| `WS /ws` | WebSocket endpoint |

---

## Database Changes

v4.0 uses a new Supabase table: **`dr_sessions_v4`**

### Schema Changes

| v3.4 Column | v4.0 Column | Change |
|-------------|-------------|--------|
| `current_state` | (removed) | Replaced by progress flags |
| (none) | `has_topic` | New progress flag |
| (none) | `has_audience` | New progress flag |
| (none) | `has_duration` | New progress flag |
| (none) | `has_purpose` | New progress flag |
| (none) | `has_plan` | New progress flag |
| (none) | `has_strawman` | New progress flag |
| (none) | `has_explicit_approval` | New progress flag |
| (none) | `has_content` | New progress flag |
| (none) | `is_complete` | New progress flag |
| `state_data` | `context` | Renamed, generic storage |

---

## Summary

### What's Better in v4.0

1. **Flexibility**: AI can adapt conversation flow to user needs
2. **Natural Conversation**: No forced state transitions
3. **Configurable**: Behavior defined in markdown, not code
4. **Explicit Cost Control**: Clear tiers and approval requirements
5. **Tool Introspection**: API to list available tools
6. **Simpler Codebase**: 1 decision engine vs 5 separate agents

### What's Preserved

1. **All Service Integrations**: Text, Illustrator, Analytics, Deck Builder
2. **WebSocket Protocol**: Same message types
3. **Session Persistence**: Same Supabase pattern
4. **Strawman Generation**: Same AI-powered outline creation
5. **Frontend Compatibility**: Same API contract

### Recommendation

For new deployments, use v4.0. For existing v3.4 deployments, migration requires:
1. Create `dr_sessions_v4` table in Supabase
2. Deploy v4.0 code
3. Existing sessions will create new v4.0 records (no automatic migration)

---

*Document Version: 1.0*
*Last Updated: December 2024*
