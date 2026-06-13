import re, os
from pathlib import Path
from config.settings import settings


class Database:
    def __init__(self):
        self.backend = "sqlite"
        self.pool = None
        self._init_pg() or self._init_sqlite()

    def _init_pg(self):
        dsn = settings.DATABASE_URL
        if not dsn:
            return False
        try:
            import psycopg2
            from psycopg2 import pool as pgpool
            from psycopg2.extras import RealDictCursor
            self.pool = pgpool.ThreadedConnectionPool(1, 10, dsn)
            self.backend = "postgres"
            self._real_dict_cursor = RealDictCursor
            self._init_pg_db()
            return True
        except Exception as e:
            print(f"PostgreSQL connection failed ({e}), falling back to SQLite")
            return False

    def _init_pg_db(self):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute("""
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
                )
            """)
            cur.execute("""
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
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback_embeddings (
                    feedback_id UUID PRIMARY KEY REFERENCES feedbacks(feedback_id),
                    embedding vector(1536) NOT NULL,
                    feedback_text TEXT DEFAULT '',
                    product TEXT DEFAULT '',
                    categories TEXT DEFAULT '[]',
                    nps_score INTEGER,
                    user_id TEXT DEFAULT 'anonymous',
                    created_at TEXT NOT NULL
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_feedbacks_fb_id ON feedbacks(feedback_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_fb_id ON feedback_embeddings(feedback_id)")
            conn.commit()
        finally:
            self._put_conn(conn)

    def _get_conn(self):
        if self.backend == "postgres":
            conn = self.pool.getconn()
            conn.cursor_factory = self._real_dict_cursor
            return conn
        import sqlite3
        conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent.parent / "feedback.db"))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _put_conn(self, conn):
        if self.backend == "postgres":
            self.pool.putconn(conn)
        else:
            conn.close()

    def _adapt_sql(self, sql):
        if self.backend == "sqlite":
            sql = sql.replace("%s", "?")
            sql = re.sub(
                r"INSERT INTO (\w+)\s*\((.+?)\)\s*VALUES\s*\((.+?)\)\s*ON CONFLICT\s*\((.+?)\)\s*DO UPDATE SET\s*(.+)",
                r"INSERT OR REPLACE INTO \1 (\2) VALUES (\3)",
                sql,
                flags=re.IGNORECASE | re.DOTALL
            )
        return sql

    def _init_sqlite(self):
        if self.backend == "sqlite":
            conn = self._get_conn()
            try:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS feedbacks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        feedback_id TEXT UNIQUE NOT NULL,
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
                    CREATE TABLE IF NOT EXISTS reviews (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        review_id TEXT UNIQUE NOT NULL,
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
                        feedback_id TEXT PRIMARY KEY,
                        embedding BLOB NOT NULL,
                        feedback_text TEXT DEFAULT '',
                        product TEXT DEFAULT '',
                        categories TEXT DEFAULT '[]',
                        nps_score INTEGER,
                        user_id TEXT DEFAULT 'anonymous',
                        created_at TEXT NOT NULL
                    );
                    CREATE VIRTUAL TABLE IF NOT EXISTS feedbacks_fts USING fts5(
                        feedback_text, content=feedbacks, content_rowid=id
                    );
                    CREATE TRIGGER IF NOT EXISTS feedbacks_ai AFTER INSERT ON feedbacks BEGIN
                        INSERT INTO feedbacks_fts(rowid, feedback_text) VALUES (new.id, new.feedback_text);
                    END;
                    CREATE TRIGGER IF NOT EXISTS feedbacks_ad AFTER DELETE ON feedbacks BEGIN
                        INSERT INTO feedbacks_fts(feedbacks_fts, rowid, feedback_text) VALUES('delete', old.id, old.feedback_text);
                    END;
                    CREATE TRIGGER IF NOT EXISTS feedbacks_au AFTER UPDATE ON feedbacks BEGIN
                        INSERT INTO feedbacks_fts(feedbacks_fts, rowid, feedback_text) VALUES('delete', old.id, old.feedback_text);
                        INSERT INTO feedbacks_fts(rowid, feedback_text) VALUES (new.id, new.feedback_text);
                    END;
                """)
                has_data = conn.execute("SELECT COUNT(*) FROM feedbacks").fetchone()[0]
                if has_data > 0:
                    try:
                        conn.execute("INSERT INTO feedbacks_fts(feedbacks_fts) VALUES('rebuild')")
                    except Exception:
                        pass
                conn.commit()
            finally:
                conn.close()

    def fetchall(self, sql, params=None):
        sql = self._adapt_sql(sql)
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(sql, params or [])
            return [dict(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)

    def fetchone(self, sql, params=None):
        sql = self._adapt_sql(sql)
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(sql, params or [])
            r = cur.fetchone()
            return dict(r) if r else None
        finally:
            self._put_conn(conn)

    def execute(self, sql, params=None):
        sql = self._adapt_sql(sql)
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(sql, params or [])
            conn.commit()
        finally:
            self._put_conn(conn)

    def execute_lastrowid(self, sql, params=None):
        sql = self._adapt_sql(sql)
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(sql, params or [])
            conn.commit()
            return cur.lastrowid
        finally:
            self._put_conn(conn)

    def is_postgres(self):
        return self.backend == "postgres"


db = Database()
