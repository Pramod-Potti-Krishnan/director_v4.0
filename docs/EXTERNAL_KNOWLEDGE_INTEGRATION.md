# External Knowledge Integration Architecture

**Version**: 1.0
**Date**: December 21, 2024
**Status**: Design Proposal
**Author**: Director Agent Team

---

## 1. Problem & Motivation

### Current Limitation: LLM Knowledge Only

Today, presentation generation relies **exclusively** on the LLM's internal knowledge:

```
┌─────────────────────────────────────────────────────────────┐
│                    CURRENT STATE                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   User Request ──► LLM Knowledge ──► Generated Content      │
│                        ▲                                    │
│                        │                                    │
│                   (training cutoff,                         │
│                    no user-specific data)                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### The Problem

| Issue | Impact |
|-------|--------|
| **Training cutoff** | LLM doesn't know recent events, latest data |
| **No user documents** | User's proprietary content isn't used |
| **Generic content** | Presentations lack specific, differentiating insights |
| **Unverified claims** | Can't fact-check with current sources |
| **Missing data** | Charts show illustrative, not real numbers |

### The Opportunity

Users often have:
- **Uploaded documents** with specific content they want included
- **Research needs** for up-to-date information
- **Data sources** for accurate chart generation
- **Specific facts/quotes** they want highlighted

---

## 2. Knowledge Source Hierarchy

### The Three Pillars

```
┌─────────────────────────────────────────────────────────────┐
│              KNOWLEDGE SOURCE HIERARCHY                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────┐                                       │
│   │  USER UPLOADS   │  ◄── HIGHEST WEIGHT                   │
│   │  (Gemini Files) │      User explicitly provided this    │
│   └────────┬────────┘                                       │
│            │                                                │
│   ┌────────▼────────┐                                       │
│   │   WEB SEARCH    │  ◄── MEDIUM WEIGHT                    │
│   │                 │      Current, verified sources        │
│   └────────┬────────┘                                       │
│            │                                                │
│   ┌────────▼────────┐                                       │
│   │  LLM KNOWLEDGE  │  ◄── FOUNDATION                       │
│   │                 │      Broad context, structure         │
│   └─────────────────┘                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Weighting Philosophy

| Source | Weight | When to Use |
|--------|--------|-------------|
| **User Uploads** | Highest | Always prioritize user-provided content |
| **Web Search** | High | When topic needs current data, user requests research |
| **LLM Knowledge** | Foundation | Structure, context, general expertise |

### Blending Strategy

1. **User uploads override LLM** when content conflicts
2. **Web search supplements** when LLM is uncertain
3. **LLM provides structure** and fills gaps where no external data exists
4. **Never fabricate** specific data - use placeholders if no source available

---

## 3. Proposed Service: Gemini Knowledge Service

### Overview

A unified service that provides:
- **File upload & indexing** (Gemini File API)
- **Semantic search** within uploaded documents
- **Web search** for current information
- **Fact extraction** for specific data points

### Ideal Endpoints

#### 3.1 File Management

```
POST /files/upload
```
Upload and index a document for a session.

**Request:**
```json
{
  "session_id": "sess_abc123",
  "file": "<binary>",
  "filename": "Q4_Report.pdf",
  "file_type": "pdf",  // pdf, docx, txt, csv, xlsx
  "index_for_search": true
}
```

**Response:**
```json
{
  "file_id": "file_xyz789",
  "session_id": "sess_abc123",
  "status": "indexed",
  "summary": "Q4 financial report showing 23% YoY revenue growth...",
  "page_count": 15,
  "key_topics": ["revenue", "growth", "market share", "Q4 2024"],
  "extraction_hints": {
    "has_tables": true,
    "has_charts": true,
    "has_numerical_data": true
  }
}
```

---

```
GET /files/{session_id}/list
```
List all uploaded files for a session.

**Response:**
```json
{
  "session_id": "sess_abc123",
  "files": [
    {
      "file_id": "file_xyz789",
      "filename": "Q4_Report.pdf",
      "upload_time": "2024-12-21T10:30:00Z",
      "summary": "Q4 financial report...",
      "page_count": 15
    }
  ],
  "total_files": 1
}
```

---

```
GET /files/{session_id}/summary
```
Get a consolidated summary of ALL uploaded files.

**Response:**
```json
{
  "session_id": "sess_abc123",
  "total_files": 2,
  "consolidated_summary": "The documents cover Q4 2024 performance (23% YoY growth) and 2025 strategic initiatives (expansion into 3 new markets). Key themes: growth, market expansion, operational efficiency.",
  "key_themes": ["Q4 performance", "2025 strategy", "market expansion"],
  "available_data_types": ["financial_metrics", "market_data", "strategic_plans"],
  "recommended_slides": [
    {"title": "Q4 Highlights", "source": "Q4_Report.pdf", "data_type": "metrics"},
    {"title": "2025 Roadmap", "source": "Strategy_2025.docx", "data_type": "plans"}
  ]
}
```

---

#### 3.2 Search & Extraction

```
POST /files/{session_id}/search
```
Semantic search within uploaded documents.

**Request:**
```json
{
  "session_id": "sess_abc123",
  "query": "revenue growth metrics",
  "max_results": 5,
  "include_context": true  // Include surrounding text
}
```

**Response:**
```json
{
  "results": [
    {
      "file_id": "file_xyz789",
      "filename": "Q4_Report.pdf",
      "page": 3,
      "snippet": "Revenue grew 23% YoY to $45M, driven by enterprise segment...",
      "relevance_score": 0.95,
      "context": {
        "before": "Building on our Q3 momentum...",
        "after": "...representing our strongest quarter ever."
      }
    }
  ],
  "query": "revenue growth metrics",
  "total_matches": 12
}
```

---

```
POST /files/{session_id}/extract
```
Extract specific information types from documents.

**Request:**
```json
{
  "session_id": "sess_abc123",
  "extraction_type": "metrics",  // metrics, quotes, facts, data_tables
  "topic_filter": "revenue",     // Optional: filter by topic
  "format": "structured"         // structured, narrative
}
```

**Response (extraction_type: metrics):**
```json
{
  "extraction_type": "metrics",
  "results": [
    {
      "metric": "YoY Revenue Growth",
      "value": "23%",
      "context": "Q4 2024 vs Q4 2023",
      "source": {"file": "Q4_Report.pdf", "page": 3}
    },
    {
      "metric": "Total Revenue",
      "value": "$45M",
      "context": "Q4 2024",
      "source": {"file": "Q4_Report.pdf", "page": 3}
    }
  ]
}
```

**Response (extraction_type: quotes):**
```json
{
  "extraction_type": "quotes",
  "results": [
    {
      "quote": "This represents our strongest quarter ever.",
      "attribution": "CEO Statement",
      "context": "Regarding Q4 performance",
      "source": {"file": "Q4_Report.pdf", "page": 1}
    }
  ]
}
```

**Response (extraction_type: data_tables):**
```json
{
  "extraction_type": "data_tables",
  "results": [
    {
      "table_title": "Quarterly Revenue Breakdown",
      "headers": ["Quarter", "Revenue", "Growth"],
      "rows": [
        ["Q1", "$32M", "15%"],
        ["Q2", "$38M", "18%"],
        ["Q3", "$42M", "21%"],
        ["Q4", "$45M", "23%"]
      ],
      "source": {"file": "Q4_Report.pdf", "page": 5}
    }
  ]
}
```

---

#### 3.3 Web Search

```
POST /search/topic
```
Research a topic using web search.

**Request:**
```json
{
  "topic": "AI market trends 2024",
  "depth": "moderate",       // quick, moderate, deep
  "focus": "statistics",     // general, statistics, trends, competitors
  "max_sources": 5,
  "recency": "last_year"     // last_week, last_month, last_year, any
}
```

**Response:**
```json
{
  "topic": "AI market trends 2024",
  "summary": "The global AI market is projected to reach $407B by 2027 (Gartner). Key trends include...",
  "key_findings": [
    {
      "finding": "Global AI market projected to reach $407B by 2027",
      "source": "Gartner Research",
      "url": "https://...",
      "confidence": "high"
    },
    {
      "finding": "Enterprise AI adoption increased 35% in 2024",
      "source": "McKinsey",
      "url": "https://...",
      "confidence": "high"
    }
  ],
  "sources_consulted": 5,
  "search_depth": "moderate"
}
```

---

```
POST /search/fact-check
```
Verify a specific claim.

**Request:**
```json
{
  "claim": "The global AI market is worth $150B",
  "year": 2024
}
```

**Response:**
```json
{
  "claim": "The global AI market is worth $150B",
  "verdict": "partially_accurate",
  "corrected": "The global AI market is valued at $184B in 2024 (Statista)",
  "sources": [
    {
      "source": "Statista",
      "value": "$184B",
      "url": "https://...",
      "date": "2024-10"
    }
  ],
  "confidence": "high"
}
```

---

```
POST /search/data
```
Find specific statistics or data points.

**Request:**
```json
{
  "data_request": "SaaS market growth rate 2024",
  "data_type": "percentage",   // percentage, currency, count, ranking
  "prefer_sources": ["Gartner", "McKinsey", "Statista"]
}
```

**Response:**
```json
{
  "data_request": "SaaS market growth rate 2024",
  "results": [
    {
      "value": "18.5%",
      "description": "Global SaaS market CAGR 2024-2028",
      "source": "Gartner",
      "url": "https://...",
      "date": "2024-09",
      "confidence": "high"
    }
  ],
  "alternatives": [
    {
      "value": "20%",
      "description": "SaaS revenue growth YoY",
      "source": "Bessemer",
      "confidence": "medium"
    }
  ]
}
```

---

## 4. Director Responsibilities

### 4.1 Knowledge Discovery at Strawman Stage

**When**: After user provides topic, BEFORE generating strawman

```python
async def _gather_knowledge_context(self, session: SessionV4) -> KnowledgeContext:
    """Gather external knowledge before strawman generation."""

    knowledge = KnowledgeContext()

    # 1. Check for user uploads
    if session.has_uploads:
        uploads_summary = await self.knowledge_client.get_files_summary(session.id)
        knowledge.uploads = uploads_summary

    # 2. Determine if web research needed
    if self._topic_needs_research(session.topic):
        research = await self.knowledge_client.search_topic(
            topic=session.topic,
            depth="moderate"
        )
        knowledge.web_research = research

    return knowledge
```

### 4.2 Knowledge-Aware Strawman Generation

**Director prompt addition:**

```
## EXTERNAL KNOWLEDGE CONTEXT

### User Uploaded Documents:
{knowledge.uploads.consolidated_summary}

Key themes from uploads: {knowledge.uploads.key_themes}
Available data: {knowledge.uploads.available_data_types}

### Web Research Findings:
{knowledge.web_research.summary}

Key statistics found:
{for finding in knowledge.web_research.key_findings}
- {finding.finding} (Source: {finding.source})
{endfor}

## INSTRUCTIONS:
1. PRIORITIZE content from user uploads - they provided these for a reason
2. USE web research findings for current data and trends
3. FILL GAPS with LLM knowledge for structure and context
4. CITE sources when using specific data points
5. DO NOT fabricate specific numbers - use [DATA NEEDED] placeholder if no source
```

### 4.3 Per-Slide Knowledge Retrieval

**When**: During slide content generation

```python
async def _enrich_slide_with_knowledge(
    self,
    slide: Dict,
    session: SessionV4,
    knowledge_context: KnowledgeContext
) -> Dict:
    """Enrich slide generation request with relevant knowledge."""

    slide_topic = slide.get('title', '')
    slide_purpose = slide.get('purpose', '')

    # Search uploads for relevant content
    if knowledge_context.uploads:
        relevant_content = await self.knowledge_client.search_files(
            session_id=session.id,
            query=f"{slide_topic} {slide_purpose}",
            max_results=3
        )
        slide['external_knowledge'] = {
            'from_uploads': relevant_content.results
        }

    # For data-heavy slides, extract specific data
    if slide_purpose in ['metrics', 'data_showcase', 'traction']:
        extracted_data = await self.knowledge_client.extract(
            session_id=session.id,
            extraction_type='metrics',
            topic_filter=slide_topic
        )
        slide['external_knowledge']['extracted_data'] = extracted_data.results

    return slide
```

### 4.4 Cost Management

**Caching Strategy:**

```python
class KnowledgeCache:
    """Cache knowledge queries to reduce API costs."""

    def __init__(self):
        self.session_cache = {}  # session_id -> cached results
        self.ttl = 3600  # 1 hour TTL

    async def get_or_fetch(self, session_id: str, query: str, fetch_fn):
        cache_key = f"{session_id}:{hash(query)}"
        if cache_key in self.session_cache:
            return self.session_cache[cache_key]

        result = await fetch_fn()
        self.session_cache[cache_key] = result
        return result
```

**When to call external knowledge:**

| Stage | Call Knowledge Service? | Rationale |
|-------|-------------------------|-----------|
| Initial topic analysis | Yes (once) | Understand uploads, do research |
| Strawman generation | Use cached | Already have context |
| Per-slide generation | Selective | Only for data-heavy slides |
| Refinement | Selective | Only if new topics introduced |

---

## 5. Text Service Responsibilities

### 5.1 Accept Knowledge Context

Text Service should accept external knowledge in generation requests:

```json
{
  "variant_id": "...",
  "slide_spec": { ... },
  "external_knowledge": {
    "from_uploads": [
      {
        "snippet": "Revenue grew 23% YoY to $45M...",
        "source": "Q4_Report.pdf",
        "relevance": 0.95
      }
    ],
    "from_web": [
      {
        "finding": "AI market projected to reach $407B",
        "source": "Gartner"
      }
    ],
    "extracted_data": [
      {"metric": "YoY Growth", "value": "23%", "source": "Q4_Report.pdf"}
    ]
  }
}
```

### 5.2 Use Knowledge in Prompts

**Text Service prompt enhancement:**

```
## EXTERNAL KNOWLEDGE (USE THIS!)

### From User Documents:
{for item in external_knowledge.from_uploads}
- "{item.snippet}" (Source: {item.source})
{endfor}

### From Research:
{for item in external_knowledge.from_web}
- {item.finding} (Source: {item.source})
{endfor}

### Extracted Data Points:
{for data in external_knowledge.extracted_data}
- {data.metric}: {data.value}
{endfor}

## INSTRUCTIONS:
1. INCORPORATE the above information into your content
2. CITE sources naturally: "According to Q4 Report..."
3. PRIORITIZE user document content over web research
4. Use LLM knowledge to structure and explain, not to invent data
```

### 5.3 Source Attribution

Generated content should include source markers:

```html
<p>Revenue grew <span class="sourced" data-source="Q4_Report.pdf">23% year-over-year</span>,
reaching <span class="sourced" data-source="Q4_Report.pdf">$45M</span> in Q4.</p>
```

---

## 6. Analytics Service Responsibilities

### 6.1 Data Extraction for Charts

Analytics Service is particularly valuable for chart generation:

**Request enhancement:**

```json
{
  "chart_type": "bar",
  "data_request": {
    "source": "external_knowledge",
    "extracted_data": [
      {"label": "Q1", "value": 32, "unit": "M"},
      {"label": "Q2", "value": 38, "unit": "M"},
      {"label": "Q3", "value": 42, "unit": "M"},
      {"label": "Q4", "value": 45, "unit": "M"}
    ],
    "source_attribution": "Q4_Report.pdf, Page 5"
  }
}
```

### 6.2 Real Data vs Illustrative Data

**Priority order:**

1. **User uploads** → Use exact data from documents
2. **Web search** → Use verified external statistics
3. **LLM estimation** → Only if explicitly allowed, mark as "illustrative"

**Labeling:**

```json
{
  "chart_data": [ ... ],
  "data_source": "Q4_Report.pdf",
  "data_confidence": "verified",  // verified, estimated, illustrative
  "footnote": "Source: Company Q4 Report, December 2024"
}
```

---

## 7. Cost/Performance Considerations

### 7.1 API Call Costs

| Operation | Estimated Cost | Frequency |
|-----------|---------------|-----------|
| File upload & indexing | ~$0.05/page | Once per file |
| File summary | ~$0.02 | Once per session |
| Semantic search | ~$0.01/query | 1-3 per slide |
| Data extraction | ~$0.02/extraction | 1-2 per data slide |
| Web search (topic) | ~$0.05 | Once per topic |
| Web search (fact-check) | ~$0.02 | As needed |

**Estimated total per presentation**: $0.50 - $2.00 (depending on uploads and research)

### 7.2 Latency Impact

| Operation | Latency | Mitigation |
|-----------|---------|------------|
| File indexing | 5-30s | Async, background |
| Summary generation | 2-5s | Cache, parallelize |
| Search queries | 0.5-1s | Batch, cache |
| Web research | 3-10s | Cache, timeout |

**Strategy**: Front-load knowledge gathering at strawman stage, cache for slide generation.

### 7.3 Caching Strategy

```python
KNOWLEDGE_CACHE_CONFIG = {
    "file_summary": {
        "ttl": 3600,        # 1 hour - files don't change
        "scope": "session"
    },
    "search_results": {
        "ttl": 300,         # 5 min - same queries likely
        "scope": "query"
    },
    "web_research": {
        "ttl": 3600,        # 1 hour - web results stable
        "scope": "topic"
    }
}
```

### 7.4 Graceful Degradation

**If knowledge service unavailable:**

```python
async def _gather_knowledge_safe(self, session):
    """Gather knowledge with fallback to LLM-only."""
    try:
        return await self._gather_knowledge_context(session)
    except KnowledgeServiceError as e:
        logger.warning(f"Knowledge service unavailable: {e}")
        return KnowledgeContext(
            status="degraded",
            message="Using LLM knowledge only - external sources unavailable"
        )
```

---

## 8. Phased Implementation Approach

### Phase 0: Service Development (External Team)

**Goal**: Gemini Knowledge Service implements the endpoints

| Endpoint | Priority | Complexity |
|----------|----------|------------|
| `POST /files/upload` | P0 | Medium |
| `GET /files/{session_id}/summary` | P0 | Low |
| `POST /files/{session_id}/search` | P0 | Medium |
| `POST /files/{session_id}/extract` | P1 | High |
| `POST /search/topic` | P1 | Medium |
| `POST /search/fact-check` | P2 | Medium |
| `POST /search/data` | P2 | Medium |

### Phase 1: Director Integration - Uploads (Week 1-2)

**Goal**: Director uses uploaded documents in generation

| Task | Effort | Impact |
|------|--------|--------|
| Create `KnowledgeClient` wrapper | 4h | Foundation |
| Add file summary to strawman context | 4h | Core value |
| Pass upload snippets to Text Service | 4h | Integration |
| Add source attribution to responses | 2h | Quality |
| Cache implementation | 4h | Performance |

### Phase 2: Per-Slide Knowledge (Week 3)

**Goal**: Each slide generation queries relevant knowledge

| Task | Effort | Impact |
|------|--------|--------|
| Implement per-slide search | 4h | Core value |
| Add data extraction for Analytics slides | 4h | Data quality |
| Batch and optimize queries | 4h | Performance |

### Phase 3: Web Research (Week 4-5)

**Goal**: Web search integration for current information

| Task | Effort | Impact |
|------|--------|--------|
| Topic research at strawman stage | 4h | Core value |
| Fact-checking integration | 4h | Quality |
| Data search for Analytics | 4h | Data quality |
| Graceful degradation | 2h | Reliability |

### Phase 4: Optimization (Week 6)

**Goal**: Tune performance, costs, and quality

| Task | Effort | Impact |
|------|--------|--------|
| Cost monitoring dashboard | 4h | Operations |
| Cache hit rate optimization | 4h | Performance |
| Source attribution UI | 4h | UX |
| A/B test knowledge impact | 8h | Validation |

---

## 9. Success Metrics

### Quality Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| User upload utilization | 0% | 90%+ |
| Source attribution rate | 0% | 80%+ |
| Data accuracy (user docs) | N/A | 95%+ |
| Fabricated data incidents | Unknown | <1% |

### Performance Metrics

| Metric | Target |
|--------|--------|
| Knowledge gathering latency | <5s |
| Per-slide knowledge query | <1s |
| Cache hit rate | >70% |
| Service availability | 99.5% |

### Cost Metrics

| Metric | Target |
|--------|--------|
| Knowledge cost per presentation | <$2 |
| Knowledge cost per slide | <$0.20 |

---

## 10. Summary

### What Changes

| Component | Change |
|-----------|--------|
| **New Service** | Gemini Knowledge Service (file uploads + web search) |
| **Director** | Gathers knowledge at strawman stage, passes to services |
| **Text Service** | Uses external knowledge in prompts, cites sources |
| **Analytics** | Uses extracted data for accurate charts |

### Knowledge Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                      KNOWLEDGE FLOW                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User Uploads ──┐                                                │
│                 ├──► Gemini Knowledge Service ──► Director       │
│  Web Search ────┘                                                │
│                                                                  │
│  Director builds KnowledgeContext:                               │
│  ├── uploads_summary: "Q4 report shows 23% growth..."            │
│  ├── relevant_snippets: [...]                                    │
│  ├── web_findings: [...]                                         │
│  └── extracted_data: [...]                                       │
│                                                                  │
│  Director passes to services:                                    │
│  ├── Text Service: snippets, quotes, context                     │
│  ├── Analytics: extracted data tables, metrics                   │
│  └── Illustrator: themes, concepts (minimal impact)              │
│                                                                  │
│  Result: Content uses user's data, cites sources, avoids hallucination  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **User uploads are highest priority** - they provided this content intentionally
2. **Web research fills gaps** - for current data and verification
3. **LLM provides structure** - expertise in presentation flow, not fabricated data
4. **Always attribute sources** - transparency builds trust
5. **Graceful degradation** - work without knowledge service if unavailable

---

## Appendix: Endpoint Contract Summary

### File Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/files/upload` | POST | Upload and index document |
| `/files/{session_id}/list` | GET | List session files |
| `/files/{session_id}/summary` | GET | Consolidated summary |
| `/files/{session_id}/search` | POST | Semantic search |
| `/files/{session_id}/extract` | POST | Extract metrics/quotes/data |

### Web Search

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/search/topic` | POST | Research a topic |
| `/search/fact-check` | POST | Verify a claim |
| `/search/data` | POST | Find specific statistics |

### Common Response Structure

```json
{
  "status": "success",
  "data": { ... },
  "meta": {
    "latency_ms": 150,
    "cache_hit": false,
    "tokens_used": 500,
    "cost_estimate": 0.02
  }
}
```
