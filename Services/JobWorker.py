#!/usr/bin/env python3
"""
Avisk Background Job Worker
============================
Runs as a standalone process (systemd service) on the VM.
Polls t_scraping_jobs every 5 seconds and executes queued jobs.

Supported job_type values:
  - 'financial_metrics'   → FinancialDataScraper + MarketDataFetcher share-patch
  - 'document_download'   → SustainabilityReportDownloader

Usage:
  python Services/JobWorker.py
"""

import json
import logging
import os
import sys
import time
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# ── Make sure the app root is on the Python path ──────────────────────────
APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

# ── Logging setup ──────────────────────────────────────────────────────────
_LOG_DIR = Path(os.environ.get("AVISK_LOG_DIR", "/opt/avisk/logs"))
try:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _log_file = str(_LOG_DIR / "worker.log")
except Exception:
    _log_file = None  # stdout only if log dir unavailable

_handlers: list = [logging.StreamHandler()]
if _log_file:
    try:
        _handlers.append(logging.FileHandler(_log_file, mode="a"))
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=_handlers,
)
logger = logging.getLogger("JobWorker")


# ── Cancellation support ───────────────────────────────────────────────────

class _JobCancelled(Exception):
    """Raised inside a runner when the frontend requests cancellation."""
    pass


def _check_cancel(conn, job_id: str) -> None:
    """Raise _JobCancelled if the frontend has flagged this job for cancellation."""
    from Services.JobQueue import is_cancel_requested
    try:
        if is_cancel_requested(conn, job_id):
            raise _JobCancelled()
    except _JobCancelled:
        raise
    except Exception:
        pass  # DB hiccup — don't abort the job


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_conn():
    from Utilities.Lookups import DB_Connection
    import psycopg2
    return psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)


def _log(conn, job_id: str, line: str) -> None:
    from Services.JobQueue import append_log
    try:
        append_log(
            conn, job_id, f"[{datetime.now().strftime('%H:%M:%S')}] {line}")
    except Exception:
        pass  # logging failures are non-fatal


def _upd(conn, job_id: str, **fields) -> None:
    from Services.JobQueue import update_job
    try:
        update_job(conn, job_id, **fields)
    except Exception as e:
        logger.warning(f"update_job failed: {e}")


# ── Job runners ────────────────────────────────────────────────────────────

def _run_financial_metrics(conn, job_id: str, payload: dict) -> list:
    """Extract EDGAR XBRL metrics for each company in payload — parallel."""
    companies   = payload.get("companies", [])
    years       = payload.get("years", [])
    skip_exist  = payload.get("skip_existing", True)
    max_workers = payload.get("max_workers", 5)
    total       = len(companies)

    _upd(conn, job_id, total=total, progress=0,
         current_item=f"Initialising — {max_workers} parallel workers…")
    _log(conn, job_id,
         f"Financial metrics job started — {total} companies, "
         f"years {years}, skip_existing={skip_exist}, workers={max_workers}")

    from Services.FinancialDataScraper import FinancialDataScraper
    from Services.MarketDataFetcher import MarketDataFetcher

    summary   = []
    completed = 0
    lock       = threading.Lock()
    cancelled  = threading.Event()
    active_set: set = set()   # symbols currently being processed

    def _process_one(co):
        nonlocal completed
        if cancelled.is_set():
            raise _JobCancelled()
        _check_cancel(conn, job_id)
        sym  = co["symbol"]
        name = co["company_name"]
        # Each thread gets its own DB connection + scraper
        db_t     = _get_conn()
        scraper  = FinancialDataScraper(db_connection=db_t, years_needed=years)
        with lock:
            active_set.add(sym)
            _upd(conn, job_id,
                 current_item=f"⚡ {', '.join(sorted(active_set))}  ({completed}/{total} done)")
        try:
            if skip_exist:
                existing = scraper.get_existing_years(name)
                if set(years).issubset(existing):
                    entry = {"symbol": sym, "status": "skipped", "saved": 0}
                    msg   = f"⏭ {sym} — skipped (all years in DB)"
                else:
                    rows, saved = scraper.scrape_and_save(sym, name)
                    entry = {"symbol": sym, "status": "ok", "saved": saved}
                    msg   = f"✅ {sym} — {saved} year-rows saved"
            else:
                rows, saved = scraper.scrape_and_save(sym, name)
                entry = {"symbol": sym, "status": "ok", "saved": saved}
                msg   = f"✅ {sym} — {saved} year-rows saved"
        except _JobCancelled:
            raise
        except Exception as exc:
            entry = {"symbol": sym, "status": "error", "saved": 0, "error": str(exc)}
            msg   = f"❌ {sym} — {exc}"
        finally:
            try:
                db_t.close()
            except Exception:
                pass

        with lock:
            completed += 1
            active_set.discard(sym)
            summary.append(entry)
            _upd(conn, job_id,
                 progress=completed,
                 current_item=(
                     f"⚡ {', '.join(sorted(active_set))}  ({completed}/{total} done)"
                     if active_set else
                     f"{completed}/{total} done"
                 ))
            _log(conn, job_id, msg)
        return entry

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_process_one, co): co for co in companies}
            for fut in as_completed(futures):
                try:
                    fut.result()
                except _JobCancelled:
                    cancelled.set()
                    pool.shutdown(wait=False, cancel_futures=True)
                    raise _JobCancelled()
    except _JobCancelled:
        raise

    # ── Auto-patch missing shares_outstanding (sequential — single connection) ──
    _upd(conn, job_id, current_item="Patching shares…")
    _log(conn, job_id, "Patching missing shares_outstanding…")
    patched = 0
    db2     = _get_conn()
    fetcher = MarketDataFetcher(db2)
    for co in companies:
        try:
            filled, _ = fetcher.patch_missing_shares(co["symbol"], co["company_name"])
            patched += filled
        except Exception:
            pass
    _log(conn, job_id, f"Shares patch complete — {patched} rows filled")
    db2.close()
    return summary


def _run_document_download(conn, job_id: str, payload: dict) -> list:
    """Download documents for each company in payload — parallel."""
    companies         = payload.get("companies", [])
    years             = payload.get("years")           # may be None (all years)
    content_types     = payload.get("content_types", [1])
    force_reload      = payload.get("force_reload", False)
    use_storage       = payload.get("use_storage", True)
    output_dir        = payload.get("output_dir", None)
    current_sector_id = payload.get("current_sector_id", None)
    delay_seconds     = payload.get("delay_seconds", 2.0)
    bypass_symbols    = set(payload.get("bypass_symbols", []))
    max_workers       = payload.get("max_workers", 5)
    total_selected    = len(companies)

    # Pre-filter bypassed companies
    companies_to_run = [c for c in companies if c["symbol"] not in bypass_symbols]
    bypassed = total_selected - len(companies_to_run)
    total    = len(companies_to_run)

    _upd(conn, job_id, total=total, progress=0,
         current_item=f"Initialising — {max_workers} parallel workers…")
    _log(conn, job_id,
         f"Document download job started — {total} companies to process, "
         f"{bypassed} bypassed, workers={max_workers}")

    from Services.SustainabilityReportDownloader import SustainabilityReportDownloader

    results   = []
    completed = 0
    lock       = threading.Lock()
    cancelled  = threading.Event()
    active_set: set = set()   # symbols currently being processed

    def _process_one(co):
        nonlocal completed
        if cancelled.is_set():
            raise _JobCancelled()
        _check_cancel(conn, job_id)
        sym  = co["symbol"]
        name = co["company_name"]
        # Each thread gets its own downloader instance (not thread-safe to share)
        dl = SustainabilityReportDownloader(
            download_dir=output_dir,
            delay_seconds=delay_seconds,
            current_sector_id=current_sector_id,
            use_storage=use_storage,
            year_filter=years,
            content_types=content_types,
            force_reload=force_reload,
        )
        with lock:
            active_set.add(sym)
            _upd(conn, job_id,
                 current_item=f"⚡ {', '.join(sorted(active_set))}  ({completed}/{total} done)")
        try:
            website = dl.get_company_website(sym, name)
            result  = dl.process_company(sym, name, website)
            status_str = result.get("status", "done") if isinstance(result, dict) else str(result)
            dl_count   = result.get("reports_downloaded", 0) if isinstance(result, dict) else 0
            err_detail = result.get("error", "") if isinstance(result, dict) else ""
            if status_str == "error":
                icon = "❌"
                msg  = f"❌ {sym} — {err_detail or 'error returned by downloader'}"
            elif dl_count == 0 and not status_str.startswith("skipped"):
                icon = "⚠️"
                msg  = f"⚠️ {sym} — {status_str} (0 downloads)"
            else:
                icon = "✅"
                msg  = f"✅ {sym} — {status_str}" + (f" ({dl_count} downloads)" if dl_count > 0 else "")
        except _JobCancelled:
            raise
        except Exception as exc:
            result = {"symbol": sym, "status": "error", "error": str(exc)}
            msg    = f"❌ {sym} — {exc}"
        finally:
            try:
                dl._save_metadata()
                dl.close()
            except Exception:
                pass

        with lock:
            completed += 1
            active_set.discard(sym)
            results.append(result)
            _upd(conn, job_id,
                 progress=completed,
                 current_item=(
                     f"⚡ {', '.join(sorted(active_set))}  ({completed}/{total} done)"
                     if active_set else
                     f"{completed}/{total} done"
                 ))
            _log(conn, job_id, msg)
        return result

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_process_one, co): co for co in companies_to_run}
            for fut in as_completed(futures):
                try:
                    fut.result()
                except _JobCancelled:
                    cancelled.set()
                    pool.shutdown(wait=False, cancel_futures=True)
                    raise _JobCancelled()
    except _JobCancelled:
        raise

    return results


# ── Main dispatch ──────────────────────────────────────────────────────────

def _process_job(conn, job_id: str, job_type: str, payload: dict) -> None:
    """Dispatch to the correct runner, then mark the job done or failed."""
    import psycopg2.extras

    try:
        if job_type == "financial_metrics":
            result = _run_financial_metrics(conn, job_id, payload)
        elif job_type == "document_download":
            result = _run_document_download(conn, job_id, payload)
        else:
            raise ValueError(f"Unknown job_type: {job_type!r}")

        _upd(
            conn, job_id,
            status="completed",
            completed_at=True,
            current_item="Done ✅",
            result_json=psycopg2.extras.Json(result),
        )
        logger.info(f"Job {job_id} ({job_type}) completed successfully.")

    except _JobCancelled:
        _upd(conn, job_id,
             status="cancelled",
             completed_at=True,
             current_item="Cancelled ✋")
        _log(conn, job_id, "Job cancelled by user request.")
        logger.info(f"Job {job_id} cancelled by user.")

    except Exception as exc:
        tb = traceback.format_exc()
        _upd(conn, job_id,
             status="failed",
             completed_at=True,
             current_item="Failed ❌",
             error_msg=str(exc))
        _log(conn, job_id, f"FATAL: {exc}\n{tb}")
        logger.error(f"Job {job_id} failed: {exc}")


# ── Entry point ────────────────────────────────────────────────────────────

def _drain_queue() -> None:
    """
    Claim and execute every currently-queued job, then return.
    Called after each NOTIFY (or the 60s fallback timeout).
    """
    from Services.JobQueue import claim_next_job
    while True:
        try:
            conn = _get_conn()
            row = claim_next_job(conn)
            if not row:
                conn.close()
                return          # queue empty — go back to sleep
            job_id, job_type, payload = row
            logger.info(f"▶  Claimed job {job_id}  type={job_type}")
            _process_job(conn, job_id, job_type, payload)
            conn.close()
        except Exception as exc:
            logger.error(f"Error draining queue: {exc}")
            time.sleep(5)
            return


def main() -> None:
    import select as _select
    from Services.JobQueue import ensure_jobs_table

    logger.info("Avisk Job Worker starting up…")

    try:
        ensure_jobs_table()
        logger.info("t_scraping_jobs table ready.")
    except Exception as exc:
        logger.error(f"Could not ensure jobs table: {exc}")

    # ── Stale job recovery ─────────────────────────────────────────────────
    # If a previous worker was killed mid-job, those jobs are still marked
    # 'running' in the DB but nothing is executing them.  Mark them failed
    # so the UI doesn't show phantom progress and the user can resubmit.
    try:
        _rc = _get_conn()
        with _rc.cursor() as _rcur:
            _rcur.execute(
                """
                UPDATE t_scraping_jobs
                SET status       = 'failed',
                    completed_at = NOW(),
                    error_msg    = 'Worker process was restarted while this job was running. '
                                   'Please resubmit the job.',
                    current_item = 'Failed ❌ (worker restarted)'
                WHERE status IN ('running', 'cancelling')
                RETURNING job_id
                """
            )
            stale = _rcur.fetchall()
        _rc.commit()
        _rc.close()
        if stale:
            logger.warning(
                f"Marked {len(stale)} stale job(s) as failed on startup: "
                + ", ".join(str(r[0]) for r in stale)
            )
        else:
            logger.info("No stale running jobs found.")
    except Exception as exc:
        logger.error(f"Stale job recovery failed: {exc}")

    # ── LISTEN/NOTIFY loop ─────────────────────────────────────────────────
    # The worker blocks here consuming zero CPU/resources until submit_job()
    # sends a NOTIFY.  Falls back to a 60-second safety-net poll.
    # No constant polling — no resource waste when the queue is empty.
    LISTEN_TIMEOUT = 60   # seconds; safety-net re-check even with no NOTIFY

    listen_conn = None

    def _connect_listener():
        c = _get_conn()
        c.autocommit = True
        with c.cursor() as cur:
            cur.execute("LISTEN avisk_job_queue;")
        logger.info(
            "Listening on avisk_job_queue (idle until a job is submitted).")
        return c

    while True:
        # (Re-)establish the LISTEN connection if needed
        if listen_conn is None or listen_conn.closed:
            try:
                listen_conn = _connect_listener()
                # Drain anything queued while we were reconnecting
                _drain_queue()
            except Exception as exc:
                logger.error(f"Could not connect listener: {exc}")
                time.sleep(10)
                continue

        try:
            # Block until a NOTIFY arrives or the timeout expires — zero CPU
            readable = _select.select([listen_conn], [], [], LISTEN_TIMEOUT)[0]

            if readable:
                listen_conn.poll()              # consume the notification
                while listen_conn.notifies:     # clear the notification list
                    n = listen_conn.notifies.pop(0)
                    logger.info(f"NOTIFY received  payload={n.payload}")

            # Whether woken by NOTIFY or timeout, drain all queued jobs
            _drain_queue()

        except Exception as exc:
            logger.error(f"Listener error: {exc} — reconnecting…")
            try:
                listen_conn.close()
            except Exception:
                pass
            listen_conn = None
            time.sleep(5)


if __name__ == "__main__":
    main()
