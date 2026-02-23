"""
One-time fix for t_data_source records with bad future year values (year > 2026).

Strategy per record:
  1. Scan the source_url filename for all 20xx years; pick the most recent <= current year
  2. If found in filename → update DB year, move file to correct year folder
  3. If not in filename → try reading the actual PDF file for a year
  4. If still not found → flag as unresolved (print for manual review)

Run on the VM (where the files live):
  gcloud compute ssh avisk-core-services-vm1 --zone=us-central1-a \
    --command "cd /opt/avisk/app && python3 HelperFIles/fix_bad_years.py"
"""
import psycopg2
from Utilities.PathConfiguration import PathConfiguration
from Utilities.Lookups import DB_Connection
import sys
import re
import shutil
from pathlib import Path

# Support running from any working directory
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))


THIS_YEAR = 2026


def plausible_years_from_string(s: str) -> list:
    """Return all 20xx years found in s that are <= THIS_YEAR, newest first."""
    candidates = [int(m) for m in re.findall(r'20\d{2}', s)]
    return sorted([y for y in candidates if 2000 <= y <= THIS_YEAR], reverse=True)


def year_from_pdf(filepath: Path) -> int:
    """Try to extract a plausible year from PDF metadata/content. Returns None if unavailable."""
    try:
        import fitz  # pymupdf
        doc = fitz.open(str(filepath))
        meta = doc.metadata or {}
        for field in ('creationDate', 'modDate'):
            val = meta.get(field, '')
            years = plausible_years_from_string(val)
            if years:
                doc.close()
                return years[0]
        # Scan first 3 pages text
        for page_num in range(min(3, doc.page_count)):
            text = doc[page_num].get_text()
            years = plausible_years_from_string(text)
            if years:
                doc.close()
                return years[0]
        doc.close()
    except ImportError:
        pass  # pymupdf not installed — skip PDF reading
    except Exception as e:
        print(f"    [PDF parse error] {e}")
    return None


# ── Resolve base directory via PathConfiguration (works locally and on VM) ───
path_cfg = PathConfiguration()
STAGE0_BASE = Path(path_cfg.get_stage0_input_path())
print(f"Stage0 base: {STAGE0_BASE}")


def find_file(bad_year: int, filename: str) -> Path:
    """Return the path to the file in the bad_year folder, or None."""
    p = STAGE0_BASE / str(bad_year) / filename
    return p if p.exists() else None


# ── Connect ───────────────────────────────────────────────────────────────────
conn = psycopg2.connect(DB_Connection().DB_CONNECTION_STRING)
cur = conn.cursor()

cur.execute("""
    SELECT unique_id, year, company_name, source_url
    FROM t_data_source
    WHERE year > 2026
    ORDER BY year
""")
bad_rows = cur.fetchall()
print(f"Bad records to fix: {len(bad_rows)}\n")

fixed = []
unresolved = []

for unique_id, bad_year, company, filename in bad_rows:
    corrected_year = None

    # Step 1: look in the filename itself (excluding the bad_year suffix)
    # Strip the trailing -YEAR or _YEAR that was appended by the downloader
    name_without_suffix = re.sub(
        rf'[-_]{bad_year}(\.\w+)?$', '', filename or '')
    years_in_name = plausible_years_from_string(name_without_suffix)
    if years_in_name:
        corrected_year = years_in_name[0]

    # Step 2: try the actual file
    if not corrected_year and filename:
        filepath = find_file(BASE_DIRS, bad_year, filename)
        if filepath:
            corrected_year = year_from_pdf(filepath)

    if corrected_year:
        print(
            f"  [FIX]  id={unique_id}  {bad_year} → {corrected_year}  {company}  {filename}")

        # Move file if it exists on this machine
        if filename:
            src = find_file(bad_year, filename)
            if src:
                dst_dir = STAGE0_BASE / str(corrected_year)
                dst_dir.mkdir(parents=True, exist_ok=True)
                dst = dst_dir / filename
                if not dst.exists():
                    shutil.move(str(src), str(dst))
                    print(f"         moved: {src} → {dst}")
                else:
                    print(f"         dst already exists, skipping move")
            else:
                print(f"         file not found on disk — DB-only fix")

        # Update DB
        cur.execute(
            "UPDATE t_data_source SET year = %s WHERE unique_id = %s",
            (corrected_year, unique_id)
        )
        fixed.append(unique_id)

    else:
        print(
            f"  [???]  id={unique_id}  year={bad_year}  {company}  {filename}  ← UNRESOLVED")
        unresolved.append((unique_id, bad_year, company, filename))

conn.commit()
cur.close()
conn.close()

print(f"\n{'='*60}")
print(f"Fixed:      {len(fixed)}")
print(f"Unresolved: {len(unresolved)}")
if unresolved:
    print("\nUnresolved records (manual review needed):")
    for row in unresolved:
        print(f"  id={row[0]}  year={row[1]}  {row[2]}  {row[3]}")
