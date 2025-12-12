# Director Agent - AI Presentation Assistant

## Version 3.4 - Content Generation & Text Service v1.2 Integration

**🎨 MAJOR FEATURE UPDATE**: v3.4 adds Stage 6 (CONTENT_GENERATION) with full Text Service v1.2 integration for generating presentation content.

**Key Features:**
- ✅ **Stage 6 - CONTENT_GENERATION**: Generate rich slide content automatically
- ✅ **Text Service v1.2**: Dual architecture (element-based for content, single-call for heroes)
- ✅ **Hero Slides**: Beautiful gradient title, section divider, and closing slides (L29 layout)
- ✅ **Content Slides**: 26 variants across 10 slide types with deterministic assembly (L25 layout)
- ✅ **Service Router**: Intelligent routing between hero and content endpoints
- ✅ **Content Transformer**: Maps generated content to layout formats
- ✅ **ADC Security**: Continues v3.3's Application Default Credentials approach

**What's New in v3.4:**
- 6-stage workflow (added CONTENT_GENERATION after GENERATE_STRAWMAN)
- Integration with Text Service v1.2 deployed at Railway
- Hero slide generation with v1.1-quality gradients and typography
- Content slide generation with parallel element-based assembly
- Complete end-to-end presentation generation with visual content

**Documentation:**
- 📖 [V3.4_IMPLEMENTATION_PLAN.md](./docs/V3.4_IMPLEMENTATION_PLAN.md) - Stage 6 implementation details
- 📖 [SECURITY.md](./SECURITY.md) - Security guide and setup
- 📖 [TAXONOMY_ARCHITECTURE_V3.4_V1.1.md](../../TAXONOMY_ARCHITECTURE_V3.4_V1.1.md) - Architecture overview

---

## Overview

The Director Agent is a 6-stage state machine that orchestrates complete presentation generation. It combines conversational AI for requirements gathering with automated content generation to produce visually stunning presentations ready for delivery.

## Architecture

This agent implements a complete 6-stage presentation generation pipeline:
- **State-Driven Workflow**: Clear progression through 6 stages from greeting to content generation
- **Intent-Based Routing**: Natural language understanding for user interactions
- **WebSocket Communication**: Real-time bidirectional messaging for live updates
- **Modular Prompt System**: Maintainable and versioned prompts for each stage
- **ADC Security**: Application Default Credentials (ADC) for Google Cloud services
- **Text Service Integration**: Seamless routing to Text Service v1.2 for content generation
- **Dual Content Architecture**: Hero slides (single-call) vs content slides (element-based)
- **Service Router**: Intelligent endpoint selection based on slide classification
- **Content Transformer**: Maps generated content to L25/L29 layout formats
- **Multi-Model Support**: Works with Google Gemini (via Vertex AI), OpenAI, and Anthropic

## Core Components

### 1. Director Agent (`src/agents/director.py`)
- Manages 6-stage presentation workflow
- Handles state-specific processing for each stage
- Implements modular prompt loading
- Orchestrates content generation in Stage 6

### 2. Intent Router (`src/agents/intent_router.py`)
- Classifies user messages into specific intents
- Maps intents to state transitions
- Enables natural conversation flow

### 3. WebSocket Handler (`src/handlers/websocket.py`)
- Manages WebSocket connections
- Routes messages based on intent
- Implements streamlined protocol
- Sends real-time content generation updates

### 4. Session Manager (`src/utils/session_manager.py`)
- Manages session state and persistence
- Handles conversation history
- Integrates with Supabase storage
- Stores generated presentation data

### 5. Service Router v1.2 (`src/utils/service_router_v1_2.py`)
- Routes slides to Text Service v1.2 endpoints
- Differentiates hero slides (L29) from content slides (L25)
- Handles hero endpoints: `/v1.2/hero/title`, `/v1.2/hero/section`, `/v1.2/hero/closing`
- Handles content endpoint: `/v1.2/generate`
- Packages responses in consistent flat structure

### 6. Hero Request Transformer (`src/utils/hero_request_transformer.py`)
- Transforms Director slide specs to hero endpoint payloads
- Builds narrative, topics, and context for hero generation
- Includes theme, audience, presentation metadata

### 7. Content Transformer (`src/utils/content_transformer.py`)
- Maps generated content to layout formats (L25/L29)
- Handles hero slides (complete inline HTML) separately from content slides
- Prepares data for layout architect service

## States and Flow

The agent progresses through these 6 stages:

1. **PROVIDE_GREETING** → Initial welcome and context gathering
2. **ASK_CLARIFYING_QUESTIONS** → Gather detailed presentation requirements
3. **CREATE_CONFIRMATION_PLAN** → Propose presentation structure with slide breakdown
4. **GENERATE_STRAWMAN** → Create initial presentation outline with classifications
5. **REFINE_STRAWMAN** → Iteratively improve the presentation structure
6. **CONTENT_GENERATION** → **NEW in v3.4** - Generate visual content for all slides

### Stage 6: Content Generation Workflow

```
User accepts strawman
        ↓
Director enters CONTENT_GENERATION state
        ↓
For each slide in strawman:
    ├─ Classify slide type
    │   ├─ Hero slide? (title/section/closing)
    │   │   └─> Route to /v1.2/hero/{type}
    │   └─ Content slide? (matrix/grid/table/etc)
    │       └─> Route to /v1.2/generate
    ↓
    ├─ Build request payload
    │   ├─ Hero: narrative, topics, context
    │   └─ Content: variant_id, slide_spec, presentation_spec
    ↓
    ├─ Call Text Service v1.2
    │   ├─ Text Service generates content
    │   │   ├─ Hero: Single LLM call with rich prompt
    │   │   └─ Content: Element-based parallel generation
    │   └─ Returns HTML + metadata
    ↓
    ├─ Transform content to layout format
    │   ├─ Hero: Pass complete inline HTML to L29
    │   └─ Content: Map elements to L25 rich_content
    ↓
    └─ Send to Layout Architect for rendering
        ↓
Collect all rendered slides
        ↓
Package presentation with URLs
        ↓
Return presentation_url to user
```

**Key Features:**
- ✅ Parallel slide generation for speed
- ✅ Real-time progress updates via WebSocket
- ✅ Hero slides with gradients and large typography (96px/84px/72px fonts)
- ✅ Content slides with deterministic template assembly
- ✅ Complete presentations ready for viewing

## Setup Instructions

### Prerequisites

- Python 3.9+
- Supabase account and project
- **v3.3 NEW**: gcloud CLI (for local development) OR service account JSON (for production)

### v3.3 Authentication Setup

**⚠️ v3.3 uses Application Default Credentials instead of API keys**

#### Local Development
```bash
# Install gcloud CLI
brew install google-cloud-sdk  # macOS
# Or visit: https://cloud.google.com/sdk/docs/install

# Authenticate with Google Cloud
gcloud auth application-default login

# Set project
gcloud config set project deckster-xyz
```

#### Railway Production
1. Create service account in GCP Console
2. Download JSON key file
3. Add `GCP_SERVICE_ACCOUNT_JSON` to Railway environment variables
4. See [SECURITY.md](./SECURITY.md) for detailed instructions

### Installation

1. **Clone or copy this directory**:
```bash
cd agents/director_agent/v3.3
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
# v3.3: No GOOGLE_API_KEY needed!
# Edit .env for Supabase and other services
```

5. **Set up Supabase**:
   - Create a new Supabase project at https://supabase.com
   - Create the sessions table using the SQL below
   - Copy your project URL and anon key to .env

### Supabase Setup

Run this SQL in your Supabase SQL editor:

```sql
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  current_state TEXT NOT NULL DEFAULT 'PROVIDE_GREETING',
  conversation_history JSONB DEFAULT '[]'::jsonb,
  user_initial_request TEXT,
  clarifying_answers JSONB,
  confirmation_plan JSONB,
  presentation_strawman JSONB,
  refinement_feedback TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
```

## Running the Agent

### Development Mode

```bash
python main.py
```

The server will start on `http://localhost:8000`

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t director-agent .
docker run -p 8000:8000 --env-file .env director-agent
```

## API Endpoints

### WebSocket Connection
```
ws://localhost:8000/ws?session_id={session_id}&user_id={user_id}
```

### REST Endpoints
- `GET /` - API information
- `GET /health` - Health check
- `GET /test-handler` - Test handler initialization

## WebSocket Message Protocol

### Client → Server
```json
{
  "type": "user_message",
  "data": {
    "text": "I need a presentation about AI"
  }
}
```

### Server → Client (Streamlined Protocol)

#### Chat Message
```json
{
  "type": "chat_message",
  "data": {
    "text": "What's the target audience for your presentation?",
    "format": "markdown"
  }
}
```

#### Action Request
```json
{
  "type": "action_request",
  "data": {
    "prompt_text": "Should I proceed with this plan?",
    "actions": [
      {
        "label": "Accept",
        "value": "accept",
        "primary": true
      },
      {
        "label": "Revise",
        "value": "revise",
        "primary": false
      }
    ]
  }
}
```

#### Slide Update
```json
{
  "type": "slide_update",
  "data": {
    "operation": "full_update",
    "metadata": {
      "title": "AI Presentation",
      "total_slides": 10
    },
    "slides": [...]
  }
}
```

## Configuration Options

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SUPABASE_URL` | Supabase project URL | Yes | - |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Yes | - |
| `GCP_PROJECT_ID` | Google Cloud project ID for Vertex AI | Yes (for Gemini) | - |
| `GCP_SERVICE_ACCOUNT_JSON` | Service account JSON (production) | Yes (Railway) | - |
| `GOOGLE_API_KEY` | Google Gemini API key (deprecated, use ADC) | One of AI keys | - |
| `OPENAI_API_KEY` | OpenAI API key | One of AI keys | - |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | One of AI keys | - |
| `TEXT_SERVICE_URL` | Text Service v1.2 base URL | Yes | `https://web-production-5daf.up.railway.app` |
| `LAYOUT_ARCHITECT_URL` | Layout Architect service URL | Yes | `http://localhost:8504` |
| `PORT` | Server port | No | 8000 |
| `DEBUG` | Debug mode | No | false |
| `USE_STREAMLINED_PROTOCOL` | Use streamlined WebSocket protocol | No | true |
| `STREAMLINED_PROTOCOL_PERCENTAGE` | A/B testing percentage | No | 100 |

**v3.4 New Requirements:**
- `TEXT_SERVICE_URL`: Points to Text Service v1.2 (Railway production or local)
- `LAYOUT_ARCHITECT_URL`: Points to Layout Architect for slide rendering
- `GCP_PROJECT_ID`: Required for Vertex AI integration in Text Service

## Testing

### Stage 6 Content Generation Testing

Test the complete content generation workflow:

```bash
cd agents/director_agent/v3.4
python3 tests/stage6_only/test_content_generation.py
```

**What This Tests:**
- ✅ Complete Stage 6 workflow with 3-slide presentation
- ✅ Hero slides (title, closing) routed to `/v1.2/hero/*` endpoints
- ✅ Content slide (matrix_2x2) routed to `/v1.2/generate` endpoint
- ✅ Text Service v1.2 integration at Railway
- ✅ Layout Architect rendering
- ✅ Presentation URL generation

**Expected Output:**
```
============================================================
Director v3.4 - Stage 6 Content Generation Test
============================================================

Test Configuration:
  Text Service: https://web-production-5daf.up.railway.app
  Layout Architect: http://localhost:8504
  Slides: 3 (title_slide, matrix_2x2, closing_slide)

Starting Stage 6 Content Generation...

Slide 1/3: title_slide (L29 Hero)
  ✓ Routed to /v1.2/hero/title
  ✓ Generated beautiful gradient HTML
  ✓ Status: 200 OK

Slide 2/3: matrix_2x2 (L25 Content)
  ✓ Routed to /v1.2/generate
  ✓ Generated 4 elements in parallel
  ✓ Status: 200 OK

Slide 3/3: closing_slide (L29 Hero)
  ✓ Routed to /v1.2/hero/closing
  ✓ Generated CTA button with gradients
  ✓ Status: 200 OK

Stage 6 Results:
  Successful: 3/3 ✅
  Failed: 0/3
  Duration: 9.37s

Presentation URL: http://localhost:8504/p/8b4c2ef2-669f-48a5-bda4-7c8971160183

✅ All slides generated successfully!
```

### Manual WebSocket Testing

1. Connect to WebSocket:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws?session_id=test-123&user_id=user-456');

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  console.log('Received:', JSON.parse(event.data));
};

// Send a message
ws.send(JSON.stringify({
  type: 'user_message',
  data: { text: 'I need a presentation about AI in healthcare' }
}));
```

2. Use the test endpoint:
```bash
curl http://localhost:8000/test-handler
```

### Health Check
```bash
curl http://localhost:8000/health
```

### Testing Text Service Integration

Test hero slide generation directly:
```bash
curl -X POST https://web-production-5daf.up.railway.app/v1.2/hero/title \
  -H "Content-Type: application/json" \
  -d '{
    "slide_number": 1,
    "slide_type": "title_slide",
    "narrative": "AI transforming healthcare",
    "topics": ["Machine Learning", "Patient Outcomes"],
    "context": {
      "theme": "professional",
      "audience": "healthcare professionals"
    }
  }'
```

Expected: Beautiful gradient HTML with 96px fonts and text shadows

## Troubleshooting

### Common Issues

1. **"No AI API key configured"**
   - Ensure at least one AI service API key is set in `.env`
   - Google Gemini is recommended for best performance

2. **"Supabase configuration missing"**
   - Add your Supabase project URL and anon key to `.env`
   - Ensure the sessions table is created in your database

3. **WebSocket connection fails**
   - Check that both `session_id` and `user_id` are provided
   - Verify the server is running on the correct port

4. **Import errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version is 3.9 or higher

## Development

### Project Structure
```
director_agent/v3.4/
├── main.py                          # FastAPI application entry
├── config/
│   ├── settings.py                  # Configuration management
│   ├── prompts/
│   │   └── modular/                 # State-specific prompts (6 stages)
│   └── deck_builder/
│       └── layout_schemas.json      # Layout schema mappings
├── src/
│   ├── agents/
│   │   ├── director.py             # Main Director agent (6-stage workflow)
│   │   └── intent_router.py        # Intent classification
│   ├── handlers/
│   │   └── websocket.py            # WebSocket connection handler
│   ├── models/                     # Pydantic data models
│   ├── storage/                    # Supabase integration
│   ├── utils/
│   │   ├── service_router_v1_2.py  # Routes to Text Service v1.2
│   │   ├── hero_request_transformer.py  # Hero payload builder
│   │   ├── content_transformer.py   # Layout format mapper
│   │   └── gcp_auth.py             # ADC authentication
│   └── workflows/
│       └── state_machine.py        # 6-stage state machine
├── tests/
│   └── stage6_only/                # Stage 6 testing
│       ├── test_content_generation.py  # Full Stage 6 test
│       └── output/                 # Test result logs
├── requirements.txt                # Dependencies
├── .env.example                    # Environment template
├── README.md                       # This file
└── docs/
    └── V3.4_IMPLEMENTATION_PLAN.md  # Stage 6 implementation guide
```

**New in v3.4:**
- `service_router_v1_2.py`: Routes slides to correct Text Service endpoints
- `hero_request_transformer.py`: Builds hero slide request payloads
- `content_transformer.py`: Maps generated content to L25/L29 formats
- `tests/stage6_only/`: Dedicated Stage 6 testing suite
- `layout_schemas.json`: Schema mappings for all 26 content variants + 3 hero types

### Adding New States

1. Add the state to the workflow in `src/workflows/state_machine.py`
2. Create a new prompt in `config/prompts/modular/`
3. Update the Director Agent to handle the new state
4. Add intent mappings in the Intent Router

### Customizing Prompts

Prompts are stored in `config/prompts/modular/`:
- `base_prompt.md` - Shared base instructions
- State-specific prompts for each workflow state

## License

This implementation is based on the Phase 1 Architecture design and is intended for educational and development purposes.

## Support

For issues or questions about this implementation:
1. Check the troubleshooting section above
2. Review the architecture documentation
3. Ensure all dependencies are correctly installed
4. Verify your API keys and Supabase configuration