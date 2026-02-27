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

POLL_INTERVAL_SECONDS = 5  # seconds between polls when queue is empty


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
    """Extract EDGAR XBRL metrics for each company in payload."""
    companies = payload.get("companies", [])
    years = payload.get("years", [])
    skip_exist = payload.get("skip_existing", True)
    total = len(companies)

    _upd(conn, job_id, total=total, progress=0, current_item="Initialising…")
    _log(conn, job_id,
         f"Financial metrics job started — {total} companies, "
         f"years {years}, skip_existing={skip_exist}")

    from Services.FinancialDataScraper import FinancialDataScraper
    from Services.MarketDataFetcher import MarketDataFetcher

    db2 = _get_conn()
    scraper = FinancialDataScraper(db_connection=db2, years_needed=years)
    summary = []

    for i, co in enumerate(companies, 1):
        _check_cancel(conn, job_id)          # ← honour frontend cancel request
        sym = co["symbol"]
        name = co["company_name"]
        _upd(conn, job_id, progress=i, current_item=f"{sym} ({i}/{total})")
        _log(conn, job_id, f"[{i}/{total}] {sym} — {name}")

        try:
            if skip_exist:
                existing = scraper.get_existing_years(name)
                if set(years).issubset(existing):
                    summary.append(
                        {"symbol": sym, "status": "skipped", "saved": 0})
                    _log(conn, job_id, f"  → skipped (all years in DB)")
                    continue

            rows, saved = scraper.scrape_and_save(sym, name)
            summary.append({"symbol": sym, "status": "ok", "saved": saved})
            _log(conn, job_id, f"  → {saved} year-rows saved")
        except Exception as exc:
            summary.append({"symbol": sym, "status": "error",
                            "saved": 0, "error": str(exc)})
            _log(conn, job_id, f"  → ERROR: {exc}")

    # ── Auto-patch missing shares_outstanding ──────────────────────────────
    _upd(conn, job_id, current_item="Patching shares…")
    _log(conn, job_id, "Patching missing shares_outstanding…")
    patched = 0
    fetcher = MarketDataFetcher(db2)
    for co in companies:
        try:
            filled, _ = fetcher.patch_missing_shares(
                co["symbol"], co["company_name"])
            patched += filled
        except Exception:
            pass
    _log(conn, job_id, f"Shares patch complete — {patched} rows filled")
    db2.close()
    return summary


def _run_document_download(conn, job_id: str, payload: dict) -> list:
    """Download documents for each company in payload."""
    companies = payload.get("companies", [])
    years = payload.get("years")          # may be None (all years)
    content_types = payload.get("content_types", [1])
    force_reload = payload.get("force_reload", False)
    use_storage = payload.get("use_storage", True)
    output_dir = payload.get("output_dir", None)
    current_sector_id = payload.get("current_sector_id", None)
    delay_seconds = payload.get("delay_seconds", 2.0)
    bypass_symbols = set(payload.get("bypass_symbols", []))
    total_selected = len(companies)

    # Pre-filter bypassed companies
    companies_to_run = [c for c in companies
                        if c["symbol"] not in bypass_symbols]
    bypassed = total_selected - len(companies_to_run)
    total = len(companies_to_run)

    _upd(conn, job_id, total=total, progress=0, current_item="Initialising…")
    _log(conn, job_id,
         f"Document download job started — {total} companies to process, "
         f"{bypassed} bypassed (already in DB)")

    from Services.SustainabilityReportDownloader import SustainabilityReportDownloader

    downloader = SustainabilityReportDownloader(
        download_dir=output_dir,
        delay_seconds=delay_seconds,
        current_sector_id=current_sector_id,
        use_storage=use_storage,
        year_filter=years,
        content_types=content_types,
        force_reload=force_reload,
    )

    results = []
    for i, co in enumerate(companies_to_run, 1):
        _check_cancel(conn, job_id)          # ← honour frontend cancel request
        sym = co["symbol"]
        name = co["company_name"]
        _upd(conn, job_id, progress=i, current_item=f"{sym} ({i}/{total})")
        _log(conn, job_id, f"[{i}/{total}] {sym} — {name}")

        try:
            website = downloader.get_company_website(sym, name)
            result = downloader.process_company(sym, name, website)
            results.append(result)
            status_str = result.get("status", "done")
            dl_count = result.get("reports_downloaded", 0)
            _log(conn, job_id, f"  → {status_str} ({dl_count} downloads)")
        except Exception as exc:
            results.append(
                {"symbol": sym, "status": "error", "error": str(exc)})
            _log(conn, job_id, f"  → ERROR: {exc}")

    try:
        downloader._save_metadata()
        downloader.close()
    except Exception:
        pass

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

def main() -> None:
    from Services.JobQueue import ensure_jobs_table, claim_next_job

    logger.info("Avisk Job Worker starting up…")

    # Ensure the jobs table exists
    try:
        ensure_jobs_table()
        logger.info("t_scraping_jobs table ready.")
    except Exception as exc:
        logger.error(f"Could not ensure jobs table: {exc}")

    consecutive_errors = 0

    while True:
        try:
            conn = _get_conn()
            row = claim_next_job(conn)
            if row:
                job_id, job_type, payload = row
                logger.info(f"▶  Claimed job {job_id}  type={job_type}")
                _process_job(conn, job_id, job_type, payload)
                consecutive_errors = 0
            conn.close()

        except Exception as exc:
            consecutive_errors += 1
            wait = min(60, POLL_INTERVAL_SECONDS * consecutive_errors)
            logger.error(
                f"Worker loop error (attempt {consecutive_errors}): {exc}  "
                f"Retrying in {wait}s…"
            )
            time.sleep(wait)
            continue

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
