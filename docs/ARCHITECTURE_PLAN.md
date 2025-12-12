# Director Agent v4.0 - MCP-Style Architecture Transformation

## Executive Summary

Transform the Director Agent from a **rigid 6-stage state machine** into a **flexible, MCP-inspired conversational agent** that makes context-aware decisions about when to ask questions, when to generate content, and which tools (services) to invoke.

## Current State (v3.4)

```
PROVIDE_GREETING → ASK_CLARIFYING_QUESTIONS → CREATE_CONFIRMATION_PLAN
    → GENERATE_STRAWMAN → REFINE_STRAWMAN → CONTENT_GENERATION
```

**Problem**: User MUST follow this exact path. No flexibility for:
- Asking questions mid-flow
- Skipping stages when unnecessary
- Handling tangential requests
- Natural conversation flow

## Target State (v4.0)

```
User Message → AI Analyzes Context → Decides Action → Executes (may invoke tools)
                    ↑                                        |
                    └────────────────────────────────────────┘
```

**Key Principles**:
1. AI has **guidance** (like CLAUDE.md) not **gates**
2. Services become **registered tools** with schemas
3. Conversation context drives decisions
4. Natural flow with best-practice guardrails

---

## Phase 1: Exploration Findings ✅

### 1.1 State Machine Analysis (RIGID - Must Replace)

**Location**: `src/agents/director.py` (2225 lines)

**Current Problems**:
- Monolithic `process()` method with 1000+ line if-elif chain (lines 347-1213)
- 5 separate Pydantic-AI agents created at init, one per state
- Hardcoded state routing: `if state == "PROVIDE_GREETING": ... elif state == "ASK_CLARIFYING_QUESTIONS": ...`
- Fixed output types per state (can't return alternative formats)
- State transitions in `src/workflows/state_machine.py` (hardcoded `TRANSITIONS` dict)

**Intent Router** (`src/agents/intent_router.py`):
- 9 hardcoded intent types as Pydantic Literal
- Ultra-low temperature (0.1) makes classification deterministic
- Adding new intent requires changes in 3 places

### 1.2 Service Integrations (PRESERVE - Become Tools)

| Service | Current Pattern | Endpoint | Purpose |
|---------|----------------|----------|---------|
| Text Service v1.2 | Single endpoint | `/v1.2/generate` | 87 content variants |
| Illustrator v1.0 | Per-variant endpoints | `/v1.0/{pyramid\|funnel\|circles}/generate` | Visualizations |
| Analytics v3 | Typed endpoints | `/analytics/v3/{chartjs\|d3}/generate` | Charts |
| Deck Builder | Direct client | `/api/presentations` | Render final deck |

**Adapter Pattern Already Exists**:
- `UnifiedServiceRouter` → dispatches to adapters
- `TextServiceAdapter`, `IllustratorServiceAdapter`, `AnalyticsServiceAdapter`
- `unified_variant_registry.json` - 87 variants with schemas

### 1.3 WebSocket & Session (PRESERVE)

**Must Preserve** (Generic Infrastructure):
- Connection management (duplicate detection, cleanup)
- Message protocol (chat_message, action_request, slide_update, status_update, presentation_url, sync_response)
- Session CRUD (cache + Supabase)
- History restoration with skip_history protocol
- Ping/pong heartbeat

**Must Refactor** (Coupled to State Machine):
- `_determine_next_state()` - hardcoded intent-to-state mapping
- Button-to-intent direct mapping for specific states
- Session fields tied to states (`clarifying_answers`, `confirmation_plan`, etc.)
- Pre-generation status logic checking specific state names

### 1.4 Key Files to Modify/Replace

| File | Action | Reason |
|------|--------|--------|
| `src/agents/director.py` | **REPLACE** | Monolithic state machine |
| `src/agents/intent_router.py` | **REPLACE** | Rigid intent classification |
| `src/handlers/websocket.py` | **MODIFY** | Remove state-machine coupling |
| `src/models/session.py` | **MODIFY** | Generify session fields |
| `src/utils/session_manager.py` | **MODIFY** | Generic context clearing |
| `src/workflows/state_machine.py` | **DELETE** | No longer needed |

### 1.5 Key Files to Preserve (Copy to v4.0)

| File | Reason |
|------|--------|
| `src/models/websocket_messages.py` | Generic message protocol |
| `src/services/unified_service_router.py` | Adapter pattern for tools |
| `src/services/adapters/*.py` | Service adapters (become tool handlers) |
| `src/storage/supabase.py` | Database layer |
| `src/utils/deck_builder_client.py` | Deck rendering |
| `src/utils/text_service_client.py` | Text generation |
| `src/clients/*.py` | Service clients |
| `config/unified_variant_registry.json` | Tool configurations |
| `main.py` | WebSocket endpoint (modify handler init) |

---

## Phase 2: Architecture Design ✅

### 2.1 Core Philosophy Change

| v3.4 (State Machine) | v4.0 (MCP-Style) |
|---------------------|------------------|
| Fixed state transitions | AI-driven decision making |
| Intent → State mapping | Context-aware tool selection |
| Hardcoded 6 stages | Flexible conversation flow |
| 5 separate LLM agents | Single decision engine + tools |
| State determines output | Context determines action |

### 2.2 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        WebSocket Handler                         │
│              (PRESERVED - connection mgmt, protocol)             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Decision Engine (NEW)                       │
│  ┌─────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │  Guidance   │    │  Context         │    │  Tool         │  │
│  │  System     │───▶│  Analyzer        │───▶│  Selector     │  │
│  │  (MD files) │    │  (Single LLM)    │    │  (Schemas)    │  │
│  └─────────────┘    └──────────────────┘    └───────────────┘  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┬───────────────┐
          ▼               ▼               ▼               ▼
   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
   │ Text       │  │ Illustrator│  │ Analytics  │  │ Deck       │
   │ Service    │  │ Service    │  │ Service    │  │ Builder    │
   │ (87 vars)  │  │ (3 viz)    │  │ (18 charts)│  │ (render)   │
   └────────────┘  └────────────┘  └────────────┘  └────────────┘
```

### 2.3 New Components

#### A. Decision Engine (`src/agents/decision_engine.py`)

Single LLM agent that analyzes context and decides what action to take.

**Decision Output Schema:**
```python
class DecisionOutput(BaseModel):
    action_type: Literal[
        "respond",           # Conversational response
        "ask_questions",     # Need more information
        "propose_plan",      # Propose presentation structure
        "generate_strawman", # Generate slide outline
        "refine_strawman",   # Modify existing strawman
        "invoke_tools",      # Call content generation tools
        "complete"           # Presentation finished
    ]
    response_text: Optional[str]       # Text to send to user
    tool_calls: Optional[List[ToolCall]]  # Tools to invoke
    reasoning: str                     # For debugging
    confidence: float
```

#### B. Tool Registry (`src/tools/registry.py`)

Services converted to MCP-style tools with schemas:

| Tool ID | Service | Cost Tier | Requires |
|---------|---------|-----------|----------|
| `text.generate_content` | Text Service v1.2 | HIGH | strawman |
| `text.generate_hero_*` | Text Service v1.2 | HIGH | strawman |
| `illustrator.generate_*` | Illustrator v1.0 | MEDIUM | strawman |
| `analytics.generate_chart` | Analytics v3 | HIGH | strawman |
| `deck.create_presentation` | Deck Builder | MEDIUM | content |
| `conversation.ask_questions` | Internal | LOW | none |
| `conversation.propose_plan` | Internal | LOW | topic |

#### C. Guidance System (`config/guidance/director_guidance.md`)

Like CLAUDE.md - provides best practices, not gates:

```markdown
## When to ASK CLARIFYING QUESTIONS:
- Topic is vague or unclear
- Missing: audience, duration, purpose, tone
- First interaction with no context

## When to GENERATE CONTENT:
- User has approved plan/strawman
- User says "looks good", "proceed", "generate"
- NEVER without user approval (cost control)

## Cost Control:
- Do NOT call expensive tools until approval
- Prefer conversation tools when uncertain
- Never regenerate entire deck on minor feedback
```

#### D. Flexible Session Model (`src/models/session.py`)

```python
class SessionV4(BaseModel):
    id: str
    user_id: str

    # Generic context (replaces state-specific fields)
    context: Dict[str, Any] = {}  # Flexible storage

    # Progress flags (not rigid states)
    has_plan: bool = False
    has_strawman: bool = False
    has_content: bool = False
    is_complete: bool = False

    # Preserved
    conversation_history: List[Dict] = []
```

### 2.4 File Structure for v4.0

```
director_agent/v4.0/
├── config/
│   ├── guidance/
│   │   ├── director_guidance.md      # Main guidance (CLAUDE.md style)
│   │   ├── presentation_best_practices.md
│   │   └── cost_control_rules.md
│   ├── tools/
│   │   ├── tool_schemas.json         # All tool definitions
│   │   └── tool_costs.json           # Cost tiers & guardrails
│   ├── settings.py
│   └── unified_variant_registry.json # PRESERVED
│
├── src/
│   ├── agents/
│   │   └── decision_engine.py        # NEW: Single AI decision maker
│   │
│   ├── tools/
│   │   ├── registry.py               # NEW: Tool registration
│   │   ├── base_tool.py              # NEW: Base interface
│   │   ├── text_tools.py             # Wrapped Text Service
│   │   ├── illustrator_tools.py      # Wrapped Illustrator
│   │   ├── analytics_tools.py        # Wrapped Analytics
│   │   ├── deck_tools.py             # Wrapped Deck Builder
│   │   └── conversation_tools.py     # NEW: Conversation helpers
│   │
│   ├── handlers/
│   │   └── websocket.py              # MODIFIED: AI-driven routing
│   │
│   ├── models/
│   │   ├── session.py                # MODIFIED: Flexible context
│   │   ├── decision.py               # NEW: Decision models
│   │   ├── agents.py                 # PRESERVED: Slide, Strawman
│   │   └── websocket_messages.py     # PRESERVED
│   │
│   ├── services/
│   │   ├── adapters/                 # PRESERVED
│   │   └── unified_service_router.py # PRESERVED
│   │
│   ├── clients/                      # PRESERVED
│   ├── storage/                      # PRESERVED
│   └── utils/                        # PRESERVED + guidance_loader.py
│
├── main.py                           # MODIFIED: Init new components
└── requirements.txt
```

---

## Phase 3: Implementation Steps

### Step 1: Setup (Copy & Structure)
1. Create `director_agent/v4.0/` directory
2. Copy all preserved files from v3.4
3. Create new directories (`config/guidance/`, `src/tools/`)

### Step 2: Guidance System
1. Create `director_guidance.md` (best practices)
2. Create `cost_control_rules.md` (guardrails)
3. Create `tool_schemas.json` (tool definitions)

### Step 3: Tool Registry
1. Implement `base_tool.py` (interface)
2. Implement `registry.py` (registration)
3. Wrap Text Service as tools
4. Wrap Illustrator Service as tools
5. Wrap Analytics Service as tools
6. Wrap Deck Builder as tools
7. Create conversation tools (ask_questions, propose_plan)

### Step 4: Decision Engine
1. Create `decision.py` models (DecisionOutput, ToolCall)
2. Implement `decision_engine.py`
3. Build system prompt from guidance files
4. Implement decision logic

### Step 5: Session Model
1. Modify `session.py` for flexible context
2. Update `session_manager.py` for SessionV4
3. Update Supabase schema if needed

### Step 6: WebSocket Integration
1. Modify `websocket.py` to use Decision Engine
2. Remove state-based routing
3. Implement `_execute_decision()` method
4. Preserve connection management

### Step 7: Main Entry Point
1. Modify `main.py` to initialize new components
2. Update health checks

### Step 8: Testing
1. Unit tests for Decision Engine
2. Integration tests for tool invocation
3. End-to-end WebSocket tests
4. Frontend compatibility testing

---

## Critical Files Reference

### Files to CREATE (New):
- `config/guidance/director_guidance.md`
- `config/guidance/cost_control_rules.md`
- `config/tools/tool_schemas.json`
- `src/agents/decision_engine.py`
- `src/tools/registry.py`
- `src/tools/base_tool.py`
- `src/tools/text_tools.py`
- `src/tools/illustrator_tools.py`
- `src/tools/analytics_tools.py`
- `src/tools/deck_tools.py`
- `src/tools/conversation_tools.py`
- `src/models/decision.py`

### Files to MODIFY:
- `src/models/session.py` → Add flexible context
- `src/utils/session_manager.py` → Support SessionV4
- `src/handlers/websocket.py` → AI-driven routing
- `main.py` → Initialize new components

### Files to PRESERVE (Copy unchanged):
- `src/models/agents.py` (Slide, PresentationStrawman)
- `src/models/websocket_messages.py`
- `src/services/unified_service_router.py`
- `src/services/adapters/*.py`
- `src/clients/*.py`
- `src/storage/supabase.py`
- `src/utils/deck_builder_client.py`
- `src/utils/text_service_client.py`
- `src/utils/streamlined_packager.py`
- `config/unified_variant_registry.json`

### Files to DELETE (Not needed):
- `src/agents/director.py` (replaced by decision_engine.py)
- `src/agents/intent_router.py` (replaced by decision_engine.py)
- `src/workflows/state_machine.py` (no longer needed)
- `config/prompts/modular/*.md` (replaced by guidance system)

---

## Design Decisions (Confirmed by User)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Cost Control** | STRICT | Never call generation tools without explicit user approval ("generate", "proceed", "looks good") |
| **Flow Guidance** | GUIDED | AI follows best practices by default but can skip steps if user provides sufficient context |
| **Session Handling** | AUTO-PERSIST | All progress automatically saved. User can resume anytime via session_id |
| **LLM Model** | `gemini-2.5-flash` | Fast and cheap for decision-making (~0.1s latency per decision) |

### Guidance System Rules (Based on Decisions)

The `director_guidance.md` will enforce:

```markdown
## STRICT COST CONTROL RULES

### NEVER call expensive tools without explicit approval:
- Wait for: "generate", "proceed", "looks good", "create it", "yes"
- If uncertain, ASK: "Ready to generate the slides?"
- Confidence threshold: 0.95+ required for generation

### Tool Cost Tiers:
- LOW (always allowed): conversation.ask_questions, conversation.respond
- MEDIUM (after strawman approved): illustrator.*, deck.create_presentation
- HIGH (explicit approval required): text.generate_*, analytics.generate_*

## GUIDED FLOW (Not Enforced, But Best Practice)

### Recommended Path:
1. Greet → Understand topic
2. Ask clarifying questions (if needed)
3. Propose plan (slide count, assumptions)
4. Generate strawman (after plan approval)
5. Refine if needed
6. Generate content (after strawman approval)

### Skip Steps When:
- User provides rich context upfront (audience, duration, purpose) → Skip Q2
- User says "just create a simple 5-slide deck" → Skip Q2 + Q3
- User provides detailed outline → Skip to strawman

### Never Skip:
- Strawman approval before content generation
- User confirmation before final deck render
```

---

## Summary: What Gets Built

### Core New Files (12 files):
1. `config/guidance/director_guidance.md` - AI behavior rules
2. `config/guidance/cost_control_rules.md` - Tool invocation rules
3. `config/tools/tool_schemas.json` - MCP-style tool definitions
4. `src/agents/decision_engine.py` - Single AI decision maker
5. `src/tools/registry.py` - Tool registration system
6. `src/tools/base_tool.py` - Base tool interface
7. `src/tools/text_tools.py` - Text Service wrappers
8. `src/tools/illustrator_tools.py` - Illustrator wrappers
9. `src/tools/analytics_tools.py` - Analytics wrappers
10. `src/tools/deck_tools.py` - Deck Builder wrappers
11. `src/tools/conversation_tools.py` - Ask questions, propose plan
12. `src/models/decision.py` - DecisionOutput, ToolCall models

### Modified Files (4 files):
1. `src/models/session.py` - Flexible context model
2. `src/utils/session_manager.py` - SessionV4 support
3. `src/handlers/websocket.py` - AI-driven routing
4. `main.py` - New component initialization

### Preserved Files (~20 files):
All service adapters, clients, storage, message protocol, Slide/Strawman models

### Deleted Files (4 files):
- `src/agents/director.py` (2225 lines → replaced)
- `src/agents/intent_router.py` (167 lines → replaced)
- `src/workflows/state_machine.py` (deleted)
- `config/prompts/modular/*.md` (6 files → replaced by guidance)

---

## Estimated Implementation Effort

| Phase | Description | Files |
|-------|-------------|-------|
| 1. Setup | Create v4.0 directory, copy preserved files | - |
| 2. Guidance | Create guidance markdown files | 2 |
| 3. Tool Registry | Implement registry + wrap services | 7 |
| 4. Decision Engine | Core AI decision logic | 2 |
| 5. Session Model | Flexible context support | 2 |
| 6. WebSocket | AI-driven message handling | 2 |
| 7. Testing | Unit + integration tests | - |

---

*Plan Status: APPROVED - READY FOR IMPLEMENTATION*
