# Migration: SQLite → PostgreSQL + pgvector

## Goal
Replace SQLite with PostgreSQL (for AWS RDS/Aurora) and use pgvector for indexed vector search instead of in-process cosine similarity.

---

## Changes Required

### 1. `config/settings.py` — Add `DATABASE_URL`
```python
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
```
Remove `CHROMA_PERSIST_DIR` (no longer used).

### 2. `app/services/database.py` — Rewrite
**Replace `sqlite3` with `psycopg2`** with a connection pool. Keep the same `fetchall`, `fetchone`, `execute` interface so all callers work unchanged.

| SQLite | PostgreSQL |
|---|---|
| `sqlite3.connect(path)` | `psycopg2.pool.ThreadedConnectionPool(DATABASE_URL)` |
| `?` parameter placeholder | `%s` |
| `INSERT OR REPLACE` | `INSERT ... ON CONFLICT (feedback_id) DO UPDATE SET ...` |
| `sqlite3.Row` → `dict(r)` | `psycopg2.extras.RealDictCursor` → dicts natively |
| FTS5 virtual table | PostgreSQL `to_tsvector('english', feedback_text)` with GIN index |
| FTS5 triggers | Removed (handled by application layer) |
| `PRAGMA journal_mode=WAL` | Not needed |

#### Schema changes (PostgreSQL syntax)
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS feedbacks (
    id SERIAL PRIMARY KEY,
    feedback_id UUID UNIQUE NOT NULL,
    feedback_text TEXT NOT NULL,
    product TEXT DEFAULT '',
    nps_score INTEGER,
    user_id TEXT DEFAULT 'anonymous',
    categories TEXT DEFAULT '[]',
    llm_response TEXT DEFAULT '',
    kb_references TEXT DEFAULT '[]',
    needs_review INTEGER DEFAULT 0,
    assigned_team TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    is_technical INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_feedbacks_feedback_id ON feedbacks(feedback_id);

CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    review_id UUID UNIQUE NOT NULL,
    feedback_id TEXT DEFAULT '',
    feedback_text TEXT DEFAULT '',
    product TEXT DEFAULT '',
    nps_score INTEGER,
    categories TEXT DEFAULT '',
    assigned_team TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    user_id TEXT DEFAULT 'anonymous',
    created_at TEXT NOT NULL,
    is_technical INTEGER DEFAULT 0,
    original_response TEXT DEFAULT '',
    final_response TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    duplicate_note TEXT DEFAULT '',
    intent_note TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS feedback_embeddings (
    feedback_id UUID PRIMARY KEY REFERENCES feedbacks(feedback_id),
    embedding vector(1536) NOT NULL,
    feedback_text TEXT DEFAULT '',
    product TEXT DEFAULT '',
    categories TEXT DEFAULT '[]',
    nps_score INTEGER,
    user_id TEXT DEFAULT 'anonymous',
    created_at TEXT NOT NULL
);

-- GIN index for full-text search (replaces FTS5)
CREATE INDEX IF NOT EXISTS idx_feedbacks_fts ON feedbacks
    USING GIN (to_tsvector('english', feedback_text));

-- HNSW index for approximate nearest neighbor search (optional, for scale)
CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON feedback_embeddings
    USING hnsw (embedding vector_cosine_ops);
```

#### Database class changes
```python
import psycopg2
from psycopg2 import pool as pgpool
from psycopg2.extras import RealDictCursor

class Database:
    def __init__(self, dsn=None):
        dsn = dsn or settings.DATABASE_URL
        self.pool = pgpool.ThreadedConnectionPool(1, 10, dsn)
        self._init_db()

    def _get_conn(self):
        conn = self.pool.getconn()
        conn.cursor_factory = RealDictCursor
        return conn

    def _put_conn(self, conn):
        self.pool.putconn(conn)

    def fetchall(self, sql, params=None):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(sql, params or [])
            return [dict(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)

    # Same pattern for fetchone, execute, execute_lastrowid
```

### 3. `app/services/vector_store.py` — Parameter changes + pgvector

#### `store_embedding()`
```python
# Before (SQLite)
INSERT OR REPLACE INTO feedback_embeddings ... VALUES (?, ?, ...)

# After (PostgreSQL)
INSERT INTO feedback_embeddings (...) VALUES (%s, %s, ...)
ON CONFLICT (feedback_id) DO UPDATE SET
    embedding = EXCLUDED.embedding,
    feedback_text = EXCLUDED.feedback_text,
    ...
```

#### `search_similar()` — Use pgvector `<=>` operator
```python
# Replace in-process cosine similarity with:
def search_similar(self, query_text, product_filter=None, n_results=10,
                   min_nps=None, max_nps=None, categories=None):
    query_vec = self._compute_embedding(query_text)
    if not query_vec:
        return []

    # pgvector: distance via cosine (<=>)
    conditions = []
    params = []
    if product_filter:
        conditions.append("e.product = %s")
        params.append(product_filter)
    if min_nps is not None:
        conditions.append("e.nps_score >= %s")
        params.append(min_nps)
    if max_nps is not None:
        conditions.append("e.nps_score <= %s")
        params.append(max_nps)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT e.feedback_id, e.feedback_text, e.product, e.nps_score,
               e.user_id, e.categories, e.created_at,
               1 - (e.embedding <=> %s::vector) AS similarity
        FROM feedback_embeddings e
        {where}
        ORDER BY e.embedding <=> %s::vector
        LIMIT %s
    """
    params.extend([query_vec, query_vec, n_results])

    rows = db.fetchall(sql, params)
    # Format results (same output format)
    results = []
    for r in rows:
        fb_categories = json.loads(r["categories"]) if isinstance(r["categories"], str) else r["categories"]
        if categories and not any(c.lower() in [x.lower() for x in fb_categories] for c in categories):
            continue
        results.append({
            "text": r["feedback_text"],
            "metadata": {...},
            "distance": 1 - r.get("similarity", 0)
        })
    return results
```

#### `query()` — Replace FTS5 with PostgreSQL full-text search
```python
def query(self, query_text, product_filter=None, n_results=10, ...):
    safe_query = re.sub(r'[^\w\s]', ' ', query_text).strip()
    if not safe_query:
        return []

    conditions = ["to_tsvector('english', f.feedback_text) @@ plainto_tsquery('english', %s)"]
    params = [safe_query]

    if product_filter:
        conditions.append("f.product = %s")
        params.append(product_filter)
    if min_nps is not None:
        conditions.append("f.nps_score >= %s")
        params.append(min_nps)
    if max_nps is not None:
        conditions.append("f.nps_score <= %s")
        params.append(max_nps)

    sql = f"""
        SELECT f.feedback_id, f.feedback_text, ...,
               ts_rank(to_tsvector('english', f.feedback_text),
                       plainto_tsquery('english', %s)) AS rank
        FROM feedbacks f
        WHERE {' AND '.join(conditions)}
        ORDER BY rank DESC
        LIMIT %s
    """
    params.append(safe_query)
    params.append(n_results)
    # ... same result formatting as before
```

#### Remove unused methods
- `_vector_to_blob()` — no longer needed (pgvector stores natively)
- `_blob_to_vector()` — no longer needed
- Remove `import struct, math` (no longer needed)

#### Keep `_compute_embedding()` as-is
Returns `List[float]` which pgvector accepts natively (psycopg2 adapts Python lists to vector type).

### 4. `app/services/review_service.py` — Parameter placeholder changes
- All `?` → `%s`
- Everything else stays the same (uses `db.execute()`, `db.fetchall()`, `db.fetchone()`)

### 5. `app/graph/nodes.py` — No logic changes
Uses `vector_store.*()` and `review_service.*()` methods — interface unchanged. Only parameter placeholder changes in SQL are handled by `database.py`.

### 6. `.env` — Add `DATABASE_URL`
```env
DATABASE_URL=postgresql://user:password@host:5432/feedback
```
Remove `CHROMA_PERSIST_DIR` (unused).

### 7. `requirements.txt` — Update packages
```txt
fastapi
uvicorn
langgraph
langchain
langchain-ollama
python-dotenv
psycopg2-binary          # replaces sqlite3
pgvector                 # vector extension adapter
```

Remove: `sqlite3` (built-in, not in requirements but was implicit dependency).

### 8. `scripts/seed_demo.py` — Parameter placeholder changes
- All `?` → `%s`
- `INSERT OR REPLACE` → `INSERT ... ON CONFLICT ... DO UPDATE SET ...`

### 9. `Dockerfile` — New file
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 10. `docs/ARCHITECTURE.md` — Update schema section
Update the database schema to reflect PostgreSQL + pgvector.

---

## Migration Steps (Execution Order)

1. Update `config/settings.py` — add `DATABASE_URL`
2. Rewrite `app/services/database.py` — psycopg2 pool + pgvector init
3. Update `app/services/vector_store.py` — parameter syntax + pgvector search
4. Update `app/services/review_service.py` — `?` → `%s`
5. Update `scripts/seed_demo.py` — `?` → `%s`
6. Update `requirements.txt`
7. Update `.env`
8. Add `Dockerfile`
9. Create PostgreSQL RDS/Aurora instance on AWS
10. Set `DATABASE_URL` env var in ECS/App Runner
11. Deploy

---

## What Stays the Same

| Component | Status |
|-----------|--------|
| API endpoints (`app/api/`) | No changes |
| LangGraph workflows (`app/graph/`) | No changes |
| LLM service (`app/services/llm_service.py`) | No changes |
| Knowledge base (`app/services/knowledge_base.py`) | No changes |
| Routing service (`app/services/routing_service.py`) | No changes |
| Frontend (`app/static/`) | No changes |
| All method signatures (`vector_store.*()`, `review_service.*()`) | No changes |

---

## PostgreSQL Instance Setup (AWS)

### Option A: RDS PostgreSQL + pgvector (Recommended)
```bash
# Create RDS instance with pgvector support
# aws rds create-db-instance --engine postgres \
#   --engine-version 16.3 --db-instance-class db.t3.micro \
#   --db-name feedback --master-username feedback_admin

# Connect and enable extension
# CREATE EXTENSION vector;
```

### Option B: Aurora Serverless v2
```bash
# Create Aurora PostgreSQL cluster
# Enable pgvector via cluster parameter group
# Serverless auto-scales from 0.5 to N ACUs
```

### Connection string format
```
DATABASE_URL=postgresql://feedback_admin:password@feedback.c9abc123.us-east-1.rds.amazonaws.com:5432/feedback
```

---

## Rollback Plan

If PostgreSQL migration has issues:
1. Keep SQLite code path as fallback
2. Or revert to SQLite by restoring `database.py` and reverting requirements
3. Data can be migrated with a script
