# Architecture Documentation

## Overview

A LangGraph-powered feedback collection and analysis system with FastAPI backend. Supports dual database backends:
- **SQLite** (local development) — built-in, zero config
- **PostgreSQL + pgvector** (AWS production) — managed RDS/Aurora with native vector search

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Web Framework | FastAPI + Uvicorn |
| Workflow Engine | LangGraph (StateGraph) |
| Database (local) | SQLite (built-in Python) |
| Database (AWS) | PostgreSQL + pgvector (RDS/Aurora) |
| Full-Text Search | SQLite FTS5 or PostgreSQL `to_tsvector` |
| Vector Search | pgvector `<=>` operator (PG) or in-process cosine similarity (SQLite) |
| Embeddings | Ollama (nomic-embed-text), OpenAI, or Google |
| LLM | Ollama (default), OpenAI, Google Gemini |
| Frontend | Plain HTML/CSS/JS (no framework) |

---

## Feedback Submission Flow

```
USER submits feedback (product, feedback_text, nps_score 1-10, user_id)
  │
  ▼
FastAPI POST /api/feedback
  │
  ▼
LangGraph Workflow (7 nodes):
  │
  ├─ 1. check_duplicates_node
  │     └─ FTS5 search for similar feedback from same user → sets duplicate_note
  │
  ├─ 2. check_technical_node
  │     └─ Keyword match for technical issues → sets is_technical flag
  │
  ├─ 3. store_feedback_node
  │     ├─ INSERT INTO feedbacks (SQLite table)
  │     └─ Compute embedding (nomic-embed-text) → INSERT INTO feedback_embeddings
  │
  ├─ 4. categorize_and_respond_node
  │     ├─ Knowledge Base search (keyword match on JSON file)
  │     └─ LLM call: categorize, respond, determine needs_review & suggested_team
  │
  ├─ 5. update_feedback_response_node
  │     ├─ UPDATE feedbacks SET llm_response, kb_references
  │     └─ UPDATE feedback_embeddings SET categories (sync categories)
  │
  ├─ 6. route_to_team_node
  │     └─ Map top category → assigned_team (or use suggested_team from LLM)
  │
  └─ 7. create_review_node (only if needs_review=True)
        └─ INSERT INTO reviews (ticket in Support Queue)
```

### Node Details

| Node | Key Logic | Error Handling |
|------|-----------|---------------|
| check_duplicates | FTS5: `SELECT FROM feedbacks_fts JOIN feedbacks WHERE MATCH ? ORDER BY rank LIMIT 3` | Silently ignored |
| check_technical | Keywords: bug, crash, error, broken, doesn't work, etc. | Silently ignored |
| store_feedback | SQLite INSERT + OllamaEmbeddings.embed_query() → struct.pack → BLOB | Sets state.error |
| categorize_and_respond | 4 separate LLM prompts: categories, response, needs_review, team. KB articles as context. | Sets state.error |
| update_feedback_response | SQLite UPDATE on both tables | Silently ignored |
| route_to_team | If LLM suggested_team, use it. Else map top category via routing_service. | Pure logic |
| create_review | INSERT INTO reviews only if needs_review=True and assigned_team != "none" | Sets state.error |

---

## PM Chat Flow

```
PM asks question (message, optional filters: product, NPS range, categories)
  │
  ▼
FastAPI POST /api/chat
  │
  ▼
LangGraph Workflow (2 nodes):
  │
  ├─ 1. retrieve_feedbacks_node
  │     └─ Semantic vector search:
  │          1. Compute embedding of query (same model as feedbacks)
  │          2. SELECT * FROM feedback_embeddings WHERE metadata filters
  │          3. For each row: deserialize BLOB → cosine similarity with query vector
  │          4. Sort by similarity DESC, return top-10
  │
  └─ 2. generate_chat_response_node
        └─ LLM call: "Here are the relevant feedbacks... Based on this data, provide insights"
```

### Cosine Similarity Computation (pure Python)

```python
dot = sum(x * y for x, y in zip(query_vec, vec))
norm_q = math.sqrt(sum(x * x for x in query_vec))
norm_v = math.sqrt(sum(x * x for x in vec))
sim = dot / (norm_q * norm_v) if norm_q and norm_v else 0
```

No numpy dependency — uses only Python's built-in `math` module.

---

## Database Schema (SQLite)

### Table: feedbacks
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| feedback_id | TEXT UNIQUE | UUID |
| feedback_text | TEXT | Raw user feedback |
| product | TEXT | Product name |
| nps_score | INTEGER | 1-10 |
| user_id | TEXT | User identifier |
| categories | TEXT | JSON array (e.g., `["delivery","billing"]`) |
| llm_response | TEXT | AI-generated response |
| kb_references | TEXT | JSON array of KB article titles used |
| needs_review | INTEGER | 0 or 1 |
| assigned_team | TEXT | Team name or "none" |
| created_at | TEXT | ISO datetime |
| is_technical | INTEGER | 0 or 1 |

### Table: feedback_embeddings
| Column | Type | Description |
|--------|------|-------------|
| feedback_id | TEXT PK | UUID (matches feedbacks table) |
| embedding | BLOB | float32 array packed via struct.pack |
| feedback_text | TEXT | Denormalized for search |
| product | TEXT | For metadata filtering |
| categories | TEXT | JSON array |
| nps_score | INTEGER | For metadata filtering |
| user_id | TEXT | For metadata filtering |
| created_at | TEXT | For metadata filtering |

### Table: reviews (Support Queue tickets)
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| review_id | TEXT UNIQUE | UUID |
| feedback_id | TEXT | Links to feedbacks table |
| feedback_text | TEXT | Denormalized copy |
| product | TEXT | |
| nps_score | INTEGER | |
| categories | TEXT | Comma-separated |
| assigned_team | TEXT | e.g., "Delivery Team" |
| status | TEXT | "pending" or "resolved" |
| user_id | TEXT | |
| is_technical | INTEGER | 0 or 1 |
| original_response | TEXT | AI response |
| final_response | TEXT | Human follow-up |
| notes | TEXT | Internal notes |
| duplicate_note | TEXT | Duplicate flag |
| intent_note | TEXT | Intent flag |

### Virtual Table: feedbacks_fts (FTS5)
- `feedback_text` column indexed for full-text search
- Content-synced with `feedbacks` table via triggers
- Used only for duplicate detection

---

## File Structure

```
.
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── feedback.py       # POST /api/feedback
│   │   ├── chat.py           # POST /api/chat
│   │   ├── review.py         # GET/PUT /api/reviews, /api/preview-user, /api/stats
│   │   ├── categories.py     # GET/POST/PUT /api/categories
│   │   └── provider.py       # GET/PUT /api/providers
│   ├── graph/
│   │   ├── nodes.py          # All workflow node functions
│   │   └── workflow.py       # StateGraph definitions (feedback + chat)
│   ├── models/
│   │   └── schemas.py        # Pydantic models
│   ├── services/
│   │   ├── database.py       # SQLite connection manager + schema init
│   │   ├── vector_store.py   # CRUD + FTS5 query + embedding compute + semantic search
│   │   ├── review_service.py # Review CRUD (SQLite)
│   │   ├── llm_service.py    # LLM calls: categorize, respond, chat, etc.
│   │   ├── routing_service.py# Team mapping + technical detection
│   │   ├── category_service.py# Category CRUD from JSON config
│   │   └── knowledge_base.py # KB articles (JSON file, keyword match)
│   ├── static/
│   │   ├── index.html        # Single-page application
│   │   ├── style.css         # Full styling
│   │   └── script.js         # All frontend logic
│   └── main.py               # FastAPI app + static file mount
├── config/
│   ├── settings.py           # Environment configuration
│   ├── categories.json       # Categories + few-shot examples
│   └── support_teams.json    # Team definitions
├── scripts/
│   └── seed_demo.py          # Seeds 12 demo entries with embeddings
├── docs/
│   └── ARCHITECTURE.md       # This file
├── requirements.txt
├── .env                      # API keys, model selection
├── feedback.db               # SQLite database (auto-created)
└── README.md
```

---

## Configuration

### .env
```
LLM_PROVIDER=ollama          # ollama, openai, google
EMBEDDING_PROVIDER=ollama    # ollama, openai, google
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma2:2b       # For chat/analysis
OLLAMA_EMBEDDING_MODEL=nomic-embed-text  # For embeddings
OPENAI_API_KEY=
GOOGLE_API_KEY=
```

### Provider Support

| Provider | Chat Model | Embedding Model |
|----------|------------|----------------|
| Ollama | gemma2:2b (or any pulled model) | nomic-embed-text |
| OpenAI | gpt-4o-mini | text-embedding-3-small |
| Google | gemini-2.0-flash | text-embedding-004 |

Chat and embedding providers can be mixed independently.

### Categories (`config/categories.json`)
13 categories with few-shot examples for LLM classification:
delivery, billing, product, quality, customer service, features, usability,
support, installation, warranty, cancellation, return, assembly

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves web UI (static/index.html) |
| `/api/feedback` | POST | Submit feedback → LangGraph workflow |
| `/api/chat` | POST | PM Chat → semantic search → LLM response |
| `/api/categories` | GET | List categories + few-shot examples |
| `/api/provider` | GET/PUT | Get/set LLM + embedding provider |
| `/api/reviews` | GET | List reviews (pending/all) with team/category filter |
| `/api/reviews/{id}` | GET/PUT | Get/update review (notes, follow-up, resolve) |
| `/api/preview-user` | GET | User POV: all feedbacks with status |
| `/api/stats` | GET | Aggregate stats |
| `/api/user-ids` | GET | Distinct user IDs |
| `/api/teams` | GET | All teams (from routing + review data) |
| `/health` | GET | Server health check |

---

## Support Queue Workflow

```
Support Queue (support tab in UI)
  │
  ├─ Select a card → action bar appears (fixed bottom)
  │
  ├─ View Details → modal with full feedback + AI response
  │
  ├─ Add Notes → internal timestamped note (not visible to user)
  │
  ├─ Send Follow-up → final response + auto-resolve
  │
  └─ Resolve → mark as resolved (with optional note)
```

### Review Statuses
- **pending**: Review ticket open, awaiting human action
- **resolved**: Human responded or marked done

### User POV Preview Statuses
- **completed**: No ticket needed (AI handled)
- **pending**: Ticket exists, waiting for human
- **resolved**: Ticket resolved

---

## Database Backends

### Configuration

The system auto-selects the backend based on the `DATABASE_URL` environment variable:

| Variable | Effect |
|----------|--------|
| Not set / empty | SQLite (local `feedback.db`) |
| `postgresql://user:pass@host:5432/db` | PostgreSQL + pgvector |

### Backend-specific behavior

| Feature | SQLite | PostgreSQL + pgvector |
|---------|--------|----------------------|
| Vector storage | BLOB (struct.pack float32) | Native `vector(1536)` column |
| Vector search | Load all → Python cosine similarity | `ORDER BY embedding <=> %s::vector LIMIT N` (indexed) |
| Full-text search | FTS5 virtual table + triggers | `to_tsvector('english', ...) @@ plainto_tsquery('english', %s)` |
| Duplicate detection | FTS5 MATCH | PostgreSQL full-text search |
| Connection | Single file, WAL mode | Connection pool (ThreadedConnectionPool) |

### Schema Notes

For PostgreSQL, the `embedding` column uses the `vector` type with 1536 dimensions (supports all embedding providers: OpenAI 1536d, Ollama/Google 768d). An HNSW index can be added for faster approximate nearest neighbor search at scale.

---

## Data Flow Summary

```
Feedback Submission → SQLite/PostgreSQL feedbacks + feedback_embeddings
                           ↓
                    LLM categorizes
                           ↓
                    If needs_review → reviews table (ticket)
                    If not → "completed" status in preview

PM Chat Query → Compute embedding → Vector search (pgvector or cosine sim)
                     ↓
              Top-10 relevant feedbacks → LLM generates insights

Support Queue → Reads from reviews table (filtered by status/team)
                     ↓
              Actions (notes/follow-up/resolve) → UPDATE reviews
```

---

## Maintenance

### Reset All Data
```bash
# SQLite
rm feedback.db
python scripts/seed_demo.py

# PostgreSQL
# DROP SCHEMA public CASCADE; CREATE SCHEMA public;
python scripts/seed_demo.py  # uses DATABASE_URL from .env
```

### Rebuild FTS5 Index (SQLite only)
If the FTS index gets out of sync, the system auto-rebuilds on startup.

### Rebuild pgvector Index (PostgreSQL only)
```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_hnsw 
ON feedback_embeddings USING hnsw (embedding vector_cosine_ops);
```

### Clear Seed + Embeddings
```bash
python scripts/seed_demo.py  # Rebuilds everything
```
