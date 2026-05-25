"""
_verify_all_ceos.py
-------------------
Independent cross-reference of every row in t_ceo against FMP
(Financial Modeling Prep) historical-key-executives API.

Strategy
--------
For each unique ticker:
  1. GET /historical-key-executives  → year-ranged CEO history
  2. GET /key-executives             → current CEO (fallback for recent years)
  3. GET /profile                    → profile CEO (last fallback)

For each (ticker, year) row in t_ceo, find the FMP CEO and compare.

Result categories (per row)
---------------------------
  MATCH        – DB name and FMP name are the same person (exact or nickname)
  LIKELY_SAME  – last names match, first names are prefix-variants (Tim/Timothy)
  MISMATCH     – DB name differs from FMP name → FLAG for manual review
  NO_FMP_REF   – FMP returned no CEO data for that ticker/year (can't verify)

Outputs
-------
  HelperFIles/_ceo_verification_report.csv  – full row-level report
  Console summary: counts by category + top MISMATCH list

Usage
-----
  DEPLOYMENT_ENV=development python HelperFIles/_verify_all_ceos.py 2>&1 | grep -v "Secret Manager\|using default"
"""

from __future__ import annotations

import sys
import os
import re
import csv
import time
import unicodedata
import requests
from collections import defaultdict
from typing import Optional

sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')
os.environ.setdefault('DEPLOYMENT_ENV', 'development')

import psycopg2
import psycopg2.extras
from Utilities.Lookups import DB_Connection

# ── FMP config (from CEODataService) ─────────────────────────────────────────
FMP_API_KEY = 'j1sUHyVT1lU3gsc2l6zF2jkuleFJEA2o'
FMP_BASE    = 'https://financialmodelingprep.com/stable'
FMP_RATE    = 0.22   # ~270 calls/min
_fmp_last   = [0.0]

# ── Name particles / initials (mirrors CEODataService) ───────────────────────
_NAME_PARTICLES = {
    'van', 'von', 'de', 'del', 'della', 'di', 'du', 'le', 'la', 'los',
    'las', 'mac', 'mc', 'o', 'ibn', 'binti', 'bte', 'st', 'da',
    'el', 'al', 'bin', 'binte', 'op', 'ten', 'ter',
}
_HONORIFIC_RE = re.compile(
    r'^(?:Dr|Mr|Mrs|Ms|Miss|Prof|Sir|Dame|Lord|Hon|Rev|Gen|Col|Lt|Cpl|Capt|Adm)\.?\s+',
    re.IGNORECASE,
)
_INITIAL_RE = re.compile(r'^[A-Z]\.?$')

# Mapping of common preferred → legal (and legal → preferred) first names.
# Only add pairs where both forms are genuinely the same person.
_NICKNAME_MAP: dict[str, set[str]] = {
    'tim':      {'timothy'},
    'timothy':  {'tim'},
    'jeff':     {'jeffrey'},
    'jeffrey':  {'jeff'},
    'bob':      {'robert'},
    'robert':   {'bob'},
    'bill':     {'william'},
    'william':  {'bill'},
    'mike':     {'michael'},
    'michael':  {'mike'},
    'jim':      {'james'},
    'james':    {'jim'},
    'joe':      {'joseph'},
    'joseph':   {'joe'},
    'tom':      {'thomas'},
    'thomas':   {'tom'},
    'dan':      {'daniel'},
    'daniel':   {'dan'},
    'dave':     {'david'},
    'david':    {'dave'},
    'rick':     {'richard'},
    'richard':  {'rick', 'dick'},
    'dick':     {'richard'},
    'chuck':    {'charles'},
    'charlie':  {'charles'},
    'charles':  {'chuck', 'charlie'},
    'tony':     {'anthony'},
    'anthony':  {'tony'},
    'steve':    {'steven', 'stephen'},
    'steven':   {'steve', 'stephen'},
    'stephen':  {'steve', 'steven'},
    'mark':     {'marcus'},
    'marcus':   {'mark'},
    'rob':      {'robert'},
    'ken':      {'kenneth'},
    'kenneth':  {'ken'},
    'don':      {'donald'},
    'donald':   {'don'},
    'ron':      {'ronald'},
    'ronald':   {'ron'},
    'chris':    {'christopher'},
    'christopher': {'chris'},
    'pat':      {'patrick'},
    'patrick':  {'pat'},
    'ed':       {'edward'},
    'edward':   {'ed', 'eddie'},
    'andy':     {'andrew'},
    'andrew':   {'andy'},
    'ben':      {'benjamin'},
    'benjamin': {'ben'},
    'sam':      {'samuel'},
    'samuel':   {'sam'},
    'alex':     {'alexander'},
    'alexander': {'alex'},
    'greg':     {'gregory'},
    'gregory':  {'greg'},
    'nick':     {'nicholas'},
    'nicholas': {'nick'},
    'lew':      {'lewis'},
    'lewis':    {'lew'},
    'frank':    {'francis'},
    'francis':  {'frank'},
    'matt':     {'matthew'},
    'matthew':  {'matt'},
    'brad':     {'bradley'},
    'bradley':  {'brad'},
}


def _strip_accents(s: str) -> str:
    """Normalize accented chars: é→e, ñ→n, etc."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )


def _normalize(name: str) -> str:
    """Strip honorifics, middle initials, particles; lowercase; remove accents."""
    if not name:
        return ''
    name = _HONORIFIC_RE.sub('', name).strip()
    parts = [
        w for w in name.split()
        if not _INITIAL_RE.fullmatch(w) and w.lower() not in _NAME_PARTICLES
    ]
    return _strip_accents(' '.join(parts)).lower().strip()


def _compare_names(db_name: str, fmp_name: str) -> str:
    """
    Returns:
      'MATCH'       – same person, exact normalized
      'LIKELY_SAME' – same last name, first is nickname variant or prefix
      'MISMATCH'    – clearly different people
    """
    if not db_name or not fmp_name:
        return 'NO_FMP_REF'

    db  = _normalize(db_name)
    fmp = _normalize(fmp_name)

    if db == fmp:
        return 'MATCH'

    db_parts  = db.split()
    fmp_parts = fmp.split()

    # Need at least 2 words each
    if len(db_parts) < 2 or len(fmp_parts) < 2:
        return 'MISMATCH'

    db_last  = db_parts[-1]
    fmp_last = fmp_parts[-1]

    if db_last != fmp_last:
        return 'MISMATCH'

    # Last names match — check first name compatibility
    db_first  = db_parts[0]
    fmp_first = fmp_parts[0]

    if db_first == fmp_first:
        return 'MATCH'  # first and last match, middle words differed → same person

    # Nickname / prefix check
    nicknames_of_db  = _NICKNAME_MAP.get(db_first, set())
    nicknames_of_fmp = _NICKNAME_MAP.get(fmp_first, set())
    if fmp_first in nicknames_of_db or db_first in nicknames_of_fmp:
        return 'LIKELY_SAME'

    # Prefix check: 'tim' vs 'timothy', 'jeff' vs 'jeffrey'
    if db_first.startswith(fmp_first) or fmp_first.startswith(db_first):
        return 'LIKELY_SAME'

    return 'MISMATCH'


# ── FMP helpers ───────────────────────────────────────────────────────────────

def _fmp_get(path: str, params: dict = None) -> list | dict | None:
    now = time.monotonic()
    wait = FMP_RATE - (now - _fmp_last[0])
    if wait > 0:
        time.sleep(wait)
    _fmp_last[0] = time.monotonic()

    p = dict(params or {})
    p['apikey'] = FMP_API_KEY
    try:
        r = requests.get(f"{FMP_BASE}{path}", params=p, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"  [FMP error] {path}: {e}", file=sys.stderr)
    return None


def _normalize_fmp_name(raw: str) -> str:
    """Apply same normalization as CEODataService._normalize_name."""
    raw = _HONORIFIC_RE.sub('', raw).strip()
    return ' '.join(
        w for w in raw.split()
        if not _INITIAL_RE.fullmatch(w) and w.lower() not in _NAME_PARTICLES
    ).strip()


# Cache per ticker
_historical: dict[str, list] = {}   # ticker → FMP historical execs
_current:    dict[str, list] = {}   # ticker → FMP current execs
_profile:    dict[str, dict | None] = {}  # ticker → FMP profile


def _build_fmp_ceo_map(ticker: str) -> dict[int, tuple[str, str]]:
    """
    Returns {year: (ceo_name_normalized, source)} for all covered years.
    Merges historical, current, and profile data.
    Source priority: historical > current > profile
    """
    result: dict[int, tuple[str, str]] = {}

    # 1. Historical endpoint — year ranges
    if ticker not in _historical:
        _historical[ticker] = _fmp_get('/historical-key-executives', {'symbol': ticker}) or []

    for ex in _historical[ticker]:
        title = (ex.get('title') or '').lower()
        if 'chief executive' not in title and title.strip() != 'ceo':
            continue
        raw_name = (ex.get('name') or '').strip()
        if not raw_name:
            continue
        name = _normalize_fmp_name(raw_name)
        if not name:
            continue

        start_raw = str(ex.get('yearActive') or ex.get('startDate') or '')[:4]
        end_raw   = str(ex.get('endDate')    or ex.get('endYear')   or '')[:4]
        try:
            start = int(start_raw) if start_raw.isdigit() else 2012
        except ValueError:
            start = 2012
        try:
            end = int(end_raw) if end_raw.isdigit() else 2026
        except ValueError:
            end = 2026
        end = min(end, 2026)
        for yr in range(start, end + 1):
            if yr not in result:
                result[yr] = (name, 'fmp_historical')

    # 2. Current key-executives — use for years not yet covered (≥2023 typically)
    if ticker not in _current:
        data = _fmp_get('/key-executives', {'symbol': ticker}) or []
        _current[ticker] = data if isinstance(data, list) else []

    for ex in _current[ticker]:
        title = (ex.get('title') or '').lower()
        if 'chief executive' not in title and 'ceo' not in title:
            continue
        raw_name = (ex.get('name') or '').strip()
        if not raw_name:
            continue
        name = _normalize_fmp_name(raw_name)
        if not name:
            continue
        # Fill any year 2020-2026 not already set by historical
        for yr in range(2020, 2027):
            if yr not in result:
                result[yr] = (name, 'fmp_key_executives')
        break  # only the first CEO-titled entry

    # 3. Profile CEO — only for very recent uncovered years
    if ticker not in _profile:
        data = _fmp_get('/profile', {'symbol': ticker})
        if isinstance(data, list) and data:
            _profile[ticker] = data[0]
        elif isinstance(data, dict) and data:
            _profile[ticker] = data
        else:
            _profile[ticker] = None

    prof = _profile.get(ticker)
    if isinstance(prof, dict):
        raw = (prof.get('ceo') or '').strip()
        name = _normalize_fmp_name(raw) if raw else ''
        if name:
            for yr in range(2023, 2027):
                if yr not in result:
                    result[yr] = (name, 'fmp_profile')

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Connecting to DB …")
    conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT ceo_id, company_name, ticker, year, ceo_name, source
        FROM   t_ceo
        ORDER  BY ticker, year
    """)
    rows = cur.fetchall()
    conn.close()

    total = len(rows)
    print(f"  {total} rows loaded from t_ceo")

    # Group by ticker to minimise FMP API calls
    by_ticker: dict[str, list] = defaultdict(list)
    for r in rows:
        by_ticker[r['ticker'] or 'UNKNOWN'].append(r)

    tickers = sorted(by_ticker.keys())
    print(f"  {len(tickers)} unique tickers  →  fetching FMP data …\n")

    OUT_PATH = '/Users/mohanganadal/Avisk/Avisk-Core-Services/HelperFIles/_ceo_verification_report.csv'
    counters = {'MATCH': 0, 'LIKELY_SAME': 0, 'MISMATCH': 0, 'NO_FMP_REF': 0}
    mismatches = []

    with open(OUT_PATH, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow([
            'ticker', 'company_name', 'year', 'db_ceo', 'fmp_ceo',
            'fmp_source', 'status', 'db_source'
        ])

        for i, ticker in enumerate(tickers, 1):
            if i % 50 == 0 or i == 1:
                print(f"  [{i}/{len(tickers)}] Processing {ticker} …")

            fmp_map = _build_fmp_ceo_map(ticker)

            for row in by_ticker[ticker]:
                year     = row['year']
                db_name  = (row['ceo_name'] or '').strip()
                db_src   = row['source'] or ''
                company  = row['company_name'] or ''

                if year in fmp_map:
                    fmp_name, fmp_src = fmp_map[year]
                else:
                    fmp_name, fmp_src = '', ''

                if not fmp_name:
                    status = 'NO_FMP_REF'
                elif not db_name:
                    status = 'NO_FMP_REF'
                else:
                    status = _compare_names(db_name, fmp_name)

                counters[status] = counters.get(status, 0) + 1

                writer.writerow([
                    ticker, company, year,
                    db_name, fmp_name, fmp_src,
                    status, db_src
                ])

                if status == 'MISMATCH':
                    mismatches.append({
                        'ticker':   ticker,
                        'company':  company,
                        'year':     year,
                        'db_name':  db_name,
                        'fmp_name': fmp_name,
                        'fmp_src':  fmp_src,
                        'db_src':   db_src,
                    })

    # ── Summary ──────────────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print("  CEO VERIFICATION SUMMARY")
    print("=" * 72)
    print(f"  Total rows evaluated : {total}")
    print(f"  ✅  MATCH            : {counters['MATCH']}")
    print(f"  🟡  LIKELY_SAME      : {counters['LIKELY_SAME']}  (preferred/legal name variants)")
    print(f"  🔴  MISMATCH         : {counters['MISMATCH']}  ← needs review")
    print(f"  ⚪  NO_FMP_REF       : {counters['NO_FMP_REF']}  (FMP has no data for that year)")
    print(f"\n  Full report → {OUT_PATH}")

    if mismatches:
        # Group mismatches by ticker for readability
        mismatch_by_ticker: dict[str, list] = defaultdict(list)
        for m in mismatches:
            mismatch_by_ticker[m['ticker']].append(m)

        print()
        print("=" * 72)
        print(f"  🔴 ALL MISMATCHES  ({len(mismatches)} rows across {len(mismatch_by_ticker)} tickers)")
        print("=" * 72)
        for tkr in sorted(mismatch_by_ticker.keys()):
            for m in sorted(mismatch_by_ticker[tkr], key=lambda x: x['year']):
                print(
                    f"  {m['ticker']:<6} {m['year']}  "
                    f"DB='{m['db_name']}'  "
                    f"FMP='{m['fmp_name']}'  "
                    f"[fmp_src={m['fmp_src']}  db_src={m['db_src']}]"
                )

    print()
    print("Done.")


if __name__ == '__main__':
    main()
