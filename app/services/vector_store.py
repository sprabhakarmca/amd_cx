import json, uuid, re, math, struct
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.services.database import db
from config.settings import settings


class VectorStore:
    def _compute_embedding(self, text: str) -> List[float]:
        try:
            if settings.EMBEDDING_PROVIDER == "vllm":
                from langchain_openai import OpenAIEmbeddings
                embeddings = OpenAIEmbeddings(
                    model=settings.VLLM_EMBEDDING_MODEL,
                    api_key="EMPTY",
                    base_url=settings.VLLM_EMBEDDING_BASE_URL
                )
                return embeddings.embed_query(text)
            from langchain_ollama import OllamaEmbeddings
            embeddings = OllamaEmbeddings(
                model=settings.OLLAMA_EMBEDDING_MODEL,
                base_url=settings.OLLAMA_BASE_URL
            )
            return embeddings.embed_query(text)
        except Exception as e:
            print(f"Embedding failed, falling back to text search: {e}")
            return []

    def _vector_to_blob(self, vector: List[float]) -> bytes:
        return struct.pack(f'{len(vector)}f', *vector)

    def _blob_to_vector(self, blob: bytes) -> List[float]:
        return list(struct.unpack(f'{len(blob)//4}f', blob))

    # ----- CRUD -----

    def add_feedback(self, feedback_text: str, product: str, nps_score: int,
                     user_id: Optional[str] = None, categories: Optional[List[str]] = None,
                     feedback_id: Optional[str] = None, needs_review: bool = False,
                     assigned_team: str = "", kb_references: Optional[List[str]] = None,
                     created_at: Optional[str] = None) -> str:
        if not feedback_id:
            feedback_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO feedbacks (feedback_id, feedback_text, product, nps_score, user_id, "
            "categories, needs_review, assigned_team, kb_references, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [feedback_id, feedback_text, product, nps_score, user_id or "anonymous",
             json.dumps(categories or []), 1 if needs_review else 0, assigned_team,
             json.dumps(kb_references or []), created_at or datetime.now().isoformat()]
        )
        return feedback_id

    def update_feedback_response(self, feedback_id: str, llm_response: str,
                                 kb_references: list = None) -> bool:
        existing = db.fetchone("SELECT id FROM feedbacks WHERE feedback_id=%s", [feedback_id])
        if not existing:
            return False
        db.execute(
            "UPDATE feedbacks SET llm_response=%s, kb_references=%s WHERE feedback_id=%s",
            [llm_response, json.dumps(kb_references or []), feedback_id]
        )
        return True

    def update_feedback_categories(self, feedback_id: str, categories: List[str]) -> bool:
        existing = db.fetchone("SELECT id FROM feedbacks WHERE feedback_id=%s", [feedback_id])
        if not existing:
            return False
        db.execute(
            "UPDATE feedbacks SET categories=%s WHERE feedback_id=%s",
            [json.dumps(categories or []), feedback_id]
        )
        return True

    # ----- Embeddings -----

    def store_embedding(self, feedback_id: str, feedback_text: str, product: str,
                        categories: List[str], nps_score: int, user_id: str,
                        created_at: str):
        try:
            vector = self._compute_embedding(feedback_text)
            if db.is_postgres():
                db.execute(
                    "INSERT INTO feedback_embeddings "
                    "(feedback_id, embedding, feedback_text, product, categories, nps_score, user_id, created_at) "
                    "VALUES (%s, %s::vector, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (feedback_id) DO UPDATE SET "
                    "embedding=%s::vector, feedback_text=%s, product=%s, categories=%s, "
                    "nps_score=%s, user_id=%s, created_at=%s",
                    [feedback_id, vector, feedback_text, product, json.dumps(categories or []),
                     nps_score, user_id, created_at,
                     vector, feedback_text, product, json.dumps(categories or []),
                     nps_score, user_id, created_at]
                )
            else:
                blob = self._vector_to_blob(vector)
                db.execute(
                    "INSERT OR REPLACE INTO feedback_embeddings "
                    "(feedback_id, embedding, feedback_text, product, categories, nps_score, user_id, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    [feedback_id, blob, feedback_text, product, json.dumps(categories or []),
                     nps_score, user_id, created_at]
                )
        except Exception:
            pass

    def update_embedding_categories(self, feedback_id: str, categories: List[str]):
        db.execute(
            "UPDATE feedback_embeddings SET categories=%s WHERE feedback_id=%s",
            [json.dumps(categories or []), feedback_id]
        )

    # ----- Vector Search -----

    def search_similar(self, query_text: str, product_filter: Optional[str] = None,
                       n_results: int = 10, min_nps: Optional[int] = None,
                       max_nps: Optional[int] = None,
                       categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        query_vec = self._compute_embedding(query_text)
        if query_vec:
            if db.is_postgres():
                return self._search_pg(query_vec, product_filter, n_results, min_nps, max_nps, categories)
            return self._search_sqlite(query_vec, product_filter, n_results, min_nps, max_nps, categories)

        return self._query_sqlite(query_text, product_filter, n_results, min_nps, max_nps, categories) if not db.is_postgres() else self._query_pg(query_text, product_filter, n_results, min_nps, max_nps, categories)

    def _search_pg(self, query_vec, product_filter, n_results, min_nps, max_nps, categories):
        conditions = []
        params = [query_vec]
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
        params.append(query_vec)
        params.append(n_results)

        sql = f"""
            SELECT e.feedback_id, e.feedback_text, e.product, e.nps_score,
                   e.user_id, e.categories, e.created_at,
                   1 - (e.embedding <=> %s::vector) AS sim
            FROM feedback_embeddings e
            {where}
            ORDER BY e.embedding <=> %s::vector
            LIMIT %s
        """
        rows = db.fetchall(sql, params)
        return self._format_search_results(rows, categories, use_sim=True)

    def _search_sqlite(self, query_vec, product_filter, n_results, min_nps, max_nps, categories):
        conditions = []
        params = []
        if product_filter:
            conditions.append("product=%s")
            params.append(product_filter)
        if min_nps is not None:
            conditions.append("nps_score>=%s")
            params.append(min_nps)
        if max_nps is not None:
            conditions.append("nps_score<=%s")
            params.append(max_nps)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = db.fetchall(f"SELECT * FROM feedback_embeddings {where}", params)
        if not rows:
            return []

        scored = []
        for r in rows:
            fb_categories = json.loads(r.get("categories") or "[]")
            if categories:
                if not any(c.lower() in [x.lower() for x in fb_categories] for c in categories):
                    continue
            vec = self._blob_to_vector(r["embedding"])
            dot = sum(x * y for x, y in zip(query_vec, vec))
            nq = math.sqrt(sum(x * x for x in query_vec))
            nv = math.sqrt(sum(x * x for x in vec))
            sim = dot / (nq * nv) if nq and nv else 0
            scored.append((sim, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return self._format_search_results([r for _, r in scored[:n_results]], categories, use_sim=False)

    def _format_search_results(self, rows, categories, use_sim):
        results = []
        for r in rows:
            fb_categories = json.loads(r["categories"]) if isinstance(r["categories"], str) else r["categories"]
            if categories:
                if not any(c.lower() in [x.lower() for x in fb_categories] for c in categories):
                    continue
            results.append({
                "text": r["feedback_text"],
                "metadata": {
                    "feedback_id": r["feedback_id"],
                    "product": r["product"],
                    "nps_score": r["nps_score"],
                    "user_id": r["user_id"],
                    "categories": fb_categories,
                    "timestamp": r["created_at"]
                },
                "distance": 1 - (r["sim"] if use_sim else 0)
            })
        return results

    # ----- Full-Text Search (for duplicate detection) -----

    def query(self, query_text: str, product_filter: Optional[str] = None,
              n_results: int = 10, min_nps: Optional[int] = None,
              max_nps: Optional[int] = None,
              categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if db.is_postgres():
            return self._query_pg(query_text, product_filter, n_results, min_nps, max_nps, categories)
        return self._query_sqlite(query_text, product_filter, n_results, min_nps, max_nps, categories)

    def _query_pg(self, query_text, product_filter, n_results, min_nps, max_nps, categories):
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
            SELECT f.feedback_id, f.feedback_text, f.product, f.nps_score, f.user_id,
                   f.categories, f.llm_response, f.kb_references, f.needs_review,
                   f.assigned_team, f.created_at, f.is_technical,
                   ts_rank(to_tsvector('english', f.feedback_text),
                           plainto_tsquery('english', %s)) AS rank
            FROM feedbacks f
            WHERE {' AND '.join(conditions)}
            ORDER BY rank DESC
            LIMIT %s
        """
        params.append(safe_query)
        params.append(n_results)
        return self._format_query_results(db.fetchall(sql, params), categories)

    def _query_sqlite(self, query_text, product_filter, n_results, min_nps, max_nps, categories):
        safe_query = re.sub(r'[^\w\s]', ' ', query_text).strip()
        if not safe_query:
            return []

        conditions = ["feedbacks_fts MATCH %s"]
        params = [safe_query]
        if product_filter:
            conditions.append("f.product=%s")
            params.append(product_filter)
        if min_nps is not None:
            conditions.append("f.nps_score>=%s")
            params.append(min_nps)
        if max_nps is not None:
            conditions.append("f.nps_score<=%s")
            params.append(max_nps)

        sql = f"""
            SELECT f.feedback_id, f.feedback_text, f.product, f.nps_score, f.user_id,
                   f.categories, f.llm_response, f.kb_references, f.needs_review,
                   f.assigned_team, f.created_at, f.is_technical
            FROM feedbacks_fts AS fts
            JOIN feedbacks AS f ON f.id = fts.rowid
            WHERE {' AND '.join(conditions)}
            ORDER BY rank
            LIMIT %s
        """
        params.append(n_results)
        rows = db.fetchall(sql, params)
        return self._format_query_results(rows, categories)

    def _format_query_results(self, rows, categories):
        results = []
        for r in rows:
            fb_categories = json.loads(r.get("categories") or "[]")
            if categories:
                if not any(c.lower() in [x.lower() for x in fb_categories] for c in categories):
                    continue
            results.append({
                "text": r["feedback_text"],
                "metadata": {
                    "feedback_id": r["feedback_id"],
                    "product": r["product"],
                    "nps_score": r["nps_score"],
                    "user_id": r["user_id"],
                    "categories": fb_categories,
                    "llm_response": r["llm_response"],
                    "kb_references": json.loads(r.get("kb_references") or "[]"),
                    "needs_review": bool(r["needs_review"]),
                    "assigned_team": r["assigned_team"],
                    "timestamp": r["created_at"],
                    "is_technical": bool(r["is_technical"])
                }
            })
        return results

    # ----- Listing -----

    def get_all_feedbacks(self, product_filter: Optional[str] = None,
                          min_nps: Optional[int] = None, max_nps: Optional[int] = None,
                          categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        conditions = []
        params = []
        if product_filter:
            conditions.append("product=%s")
            params.append(product_filter)
        if min_nps is not None:
            conditions.append("nps_score>=%s")
            params.append(min_nps)
        if max_nps is not None:
            conditions.append("nps_score<=%s")
            params.append(max_nps)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = db.fetchall(f"SELECT * FROM feedbacks {where} ORDER BY created_at DESC", params)

        results = []
        for r in rows:
            fb_categories = json.loads(r.get("categories") or "[]")
            if categories:
                if not any(c.lower() in [x.lower() for x in fb_categories] for c in categories):
                    continue
            results.append({
                "text": r["feedback_text"],
                "metadata": {
                    "feedback_id": r["feedback_id"],
                    "product": r["product"],
                    "nps_score": r["nps_score"],
                    "user_id": r["user_id"],
                    "categories": fb_categories,
                    "llm_response": r["llm_response"],
                    "kb_references": json.loads(r.get("kb_references") or "[]"),
                    "needs_review": bool(r["needs_review"]),
                    "assigned_team": r["assigned_team"],
                    "timestamp": r["created_at"],
                    "is_technical": bool(r["is_technical"])
                },
                "id": r["feedback_id"]
            })
        return results

    def get_all_user_ids(self) -> List[str]:
        rows = db.fetchall(
            "SELECT DISTINCT user_id FROM feedbacks WHERE user_id != %s ORDER BY user_id",
            ["anonymous"]
        )
        return [r["user_id"] for r in rows]

    def get_feedback_with_response(self, feedback_id: str) -> Optional[Dict[str, Any]]:
        r = db.fetchone("SELECT * FROM feedbacks WHERE feedback_id=%s", [feedback_id])
        if not r:
            return None
        return {
            "id": r["feedback_id"],
            "feedback_text": r["feedback_text"],
            "product": r["product"],
            "nps_score": r["nps_score"],
            "user_id": r["user_id"],
            "categories": json.loads(r.get("categories") or "[]"),
            "created_at": r["created_at"],
            "ai_response": r["llm_response"]
        }


vector_store = VectorStore()
