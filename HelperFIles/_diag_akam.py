"""Diagnose AKAM CEO text extraction."""
from bs4 import BeautifulSoup
import requests
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


url = "https://www.sec.gov/Archives/edgar/data/1086222/000108622225000028/akam-20241231.htm"
print(f"Fetching {url} ...")
r = requests.get(
    url, headers={"User-Agent": "AviskResearch research@avisk.ai"}, timeout=60)
print(f"HTTP {r.status_code}  bytes={len(r.content):,}")

soup = BeautifulSoup(r.content, 'html.parser')
for tag in soup(['script', 'style']):
    tag.decompose()
text = soup.get_text(separator='\n', strip=True)
text = re.sub(r'[ \t]{2,}', ' ', text)

# All CEO title occurrences
ceo_hits = [(m.start(), m.group())
            for m in re.finditer(r'[Cc]hief [Ee]xecutive [Oo]fficer', text)]
print(f"\nTotal 'Chief/chief Executive Officer' occurrences: {len(ceo_hits)}")

# Leighton / Thomson occurrences
leighton_hits = [(m.start(), m.group())
                 for m in re.finditer(r'Leighton|Thomson', text, re.I)]
print(
    f"'Leighton/Thomson' occurrences: {len(leighton_hits)} at positions: {[p for p,_ in leighton_hits[:8]]}")

# Show each Leighton context
for pos, word in leighton_hits[:3]:
    snippet = text[max(0, pos-200):pos+300]
    print(f"\n--- {word} @ {pos} ---")
    print(repr(snippet))

# Show each CEO title context that's near a name
print("\n=== All CEO title contexts ===")
for i, (pos, title) in enumerate(ceo_hits):
    ctx = text[max(0, pos-250):pos+100]
    # Check if there's a potential name nearby
    if re.search(r'[A-Z][a-z]+', ctx[:-100]):  # name-like word before the title
        print(f"\n--- #{i+1} @ {pos} ({title}) ---")
        print(repr(ctx))
