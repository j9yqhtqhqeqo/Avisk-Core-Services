"""
Avisk Job Queue Helpers
=======================
Shared utilities for submitting, querying, and listing background scraping jobs.
Uses t_scraping_jobs in PostgreSQL as the job store.

Used by:
  - Streamlit pages (submit + poll)
  - JobWorker.py (claim + update)
"""

import json
from typing import Optional

import psycopg2
import psycopg2.extras

# ---------------------------------------------------------------------------
# Table DDL — auto-created on first use
# ---------------------------------------------------------------------------
_DDL = """
CREATE TABLE IF NOT EXISTS t_scraping_jobs (
    job_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type      TEXT NOT NULL,
    status        TEXT DEFAULT 'queued',
    payload       JSONB NOT NULL DEFAULT '{}',
    progress      INTEGER DEFAULT 0,
    total         INTEGER DEFAULT 0,
    current_item  TEXT DEFAULT '',
    log_lines     TEXT DEFAULT '',
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ,
    error_msg     TEXT,
    result_json   JSONB
);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_status
    ON t_scraping_jobs (status);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_created
    ON t_scraping_jobs (created_at DESC);
"""

# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _conn():
    from Utilities.Lookups import DB_Connection
    return psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)


def ensure_jobs_table() -> None:
    """Create t_scraping_jobs if it does not yet exist (idempotent)."""
    try:
        c = _conn()
        with c.cursor() as cur:
            for stmt in _DDL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
        c.commit()
        c.close()
    except Exception as exc:
        # Non-fatal — table may already exist or DB may be briefly unavailable
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def submit_job(job_type: str, payload: dict) -> str:
    """
    Insert a new job into the queue.
    Returns the new job_id (UUID as str).
    """
    c = _conn()
    with c.cursor() as cur:
        cur.execute(
            "INSERT INTO t_scraping_jobs (job_type, payload) "
            "VALUES (%s, %s) RETURNING job_id",
            (job_type, psycopg2.extras.Json(payload)),
        )
        job_id = str(cur.fetchone()[0])
    c.commit()
    c.close()
    return job_id


def get_job(job_id: str) -> dict:
    """Return the full job row as a dict, or {} if not found."""
    c = _conn()
    with c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM t_scraping_jobs WHERE job_id = %s", (job_id,)
        )
        row = cur.fetchone()
    c.close()
    return dict(row) if row else {}


def get_recent_jobs(job_type: Optional[str] = None, limit: int = 15) -> list:
    """Return the most recent jobs (newest first), optionally filtered by type."""
    c = _conn()
    with c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if job_type:
            cur.execute(
                "SELECT job_id, job_type, status, progress, total, "
                "current_item, created_at, started_at, completed_at, error_msg "
                "FROM t_scraping_jobs WHERE job_type = %s "
                "ORDER BY created_at DESC LIMIT %s",
                (job_type, limit),
            )
        else:
            cur.execute(
                "SELECT job_id, job_type, status, progress, total, "
                "current_item, created_at, started_at, completed_at, error_msg "
                "FROM t_scraping_jobs "
                "ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
        rows = [dict(r) for r in cur.fetchall()]
    c.close()
    return rows


def cancel_job(job_id: str) -> str:
    """
    Request cancellation of a job.

    - 'queued'  → cancelled immediately; returns 'cancelled'
    - 'running' → marked 'cancelling'; worker stops after the current company;
                  returns 'cancelling'
    - other     → no change; returns '' (job already terminal)
    """
    c = _conn()
    result = ""
    with c.cursor() as cur:
        # Queued → cancel instantly
        cur.execute(
            "UPDATE t_scraping_jobs SET status = 'cancelled', completed_at = NOW() "
            "WHERE job_id = %s AND status = 'queued' RETURNING job_id",
            (job_id,),
        )
        if cur.fetchone():
            result = "cancelled"
        else:
            # Running → request graceful stop
            cur.execute(
                "UPDATE t_scraping_jobs SET status = 'cancelling' "
                "WHERE job_id = %s AND status = 'running' RETURNING job_id",
                (job_id,),
            )
            if cur.fetchone():
                result = "cancelling"
    c.commit()
    c.close()
    return result


def is_cancel_requested(conn, job_id: str) -> bool:
    """Return True if the frontend has requested cancellation (status = 'cancelling').
    Called by the worker inside per-company loops."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM t_scraping_jobs "
            "WHERE job_id = %s AND status = 'cancelling'",
            (job_id,),
        )
        return cur.fetchone() is not None


# ---------------------------------------------------------------------------
# Worker-internal helpers (used by JobWorker.py only)
# ---------------------------------------------------------------------------

def claim_next_job(conn) -> Optional[tuple]:
    """
    Atomically claim the next queued job.
    Returns (job_id_str, job_type, payload_dict) or None.
    Must be called with an already-open connection.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE t_scraping_jobs
            SET status = 'running', started_at = NOW()
            WHERE job_id = (
                SELECT job_id FROM t_scraping_jobs
                WHERE status = 'queued'
                ORDER BY created_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING job_id, job_type, payload
            """,
        )
        row = cur.fetchone()
    conn.commit()
    if row is None:
        return None
    job_id, job_type, payload = row
    if isinstance(payload, str):
        payload = json.loads(payload)
    return str(job_id), job_type, payload


def update_job(conn, job_id: str, **fields) -> None:
    """
    Update arbitrary fields on a job row.
    Pass completed_at=True to use NOW() SQL expression.
    """
    sets, params = [], []
    for k, v in fields.items():
        if k == "completed_at" and v is True:
            sets.append("completed_at = NOW()")
        elif k == "started_at" and v is True:
            sets.append("started_at = NOW()")
        else:
            sets.append(f"{k} = %s")
            params.append(v)
    if not sets:
        return
    params.append(job_id)
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE t_scraping_jobs SET {', '.join(sets)} WHERE job_id = %s",
            params,
        )
    conn.commit()


def append_log(conn, job_id: str, line: str, max_chars: int = 100_000) -> None:
    """Append a log line, capping total log at max_chars (tail kept)."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE t_scraping_jobs "
            "SET log_lines = RIGHT(log_lines || %s, %s) "
            "WHERE job_id = %s",
            (line + "\n", max_chars, job_id),
        )
    conn.commit()
