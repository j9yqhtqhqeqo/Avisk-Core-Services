import csv, subprocess

BUCKET  = "avisk-app-data-eb7773c8"
PREFIX  = "Development/data/Stage0SourcePDFFiles"
CSV     = "/tmp/validation.csv"

moved = skipped = errors = 0

with open(CSV, newline="") as f:
    for row in csv.DictReader(f):
        if row["status"] != "wrong_folder":
            continue
        filename    = row["filename"]
        actual_year = row["actual_folder"]
        db_year     = row["db_year"]
        src = f"gs://{BUCKET}/{PREFIX}/{actual_year}/{filename}"
        dst = f"gs://{BUCKET}/{PREFIX}/{db_year}/{filename}"
        r = subprocess.run(["gsutil", "mv", src, dst], capture_output=True, text=True)
        if r.returncode == 0:
            moved += 1
            print(f"  OK  {actual_year}->{db_year}  {filename[:65]}")
        elif "No URLs matched" in r.stderr or "CommandException" in r.stderr:
            skipped += 1
            print(f"  --  already gone: {filename[:65]}")
        else:
            errors += 1
            print(f"  ERR {r.stderr.strip()[:100]}")

print(f"\nDone  moved={moved}  skipped={skipped}  errors={errors}")
