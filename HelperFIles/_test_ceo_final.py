"""
Comprehensive test of all CEO fixes.
Tests:
  1. _is_valid_name with middle initials
  2. _normalize_name
  3. SEC pattern extractions (middle initials, Northrop Grumman trap)
  4. Web pattern extractions
  5. FMP fetch for AAPL (should now return Timothy Cook)
  6. Full pipeline simulation for AAPL
"""
from Services.CEODataService import (
    _is_valid_name, _normalize_name,
    _extract_ceo_from_sec_text, _extract_ceo_from_web_text,
    fetch_ceo_from_fmp, fetch_ceo_from_ddgs,
)
import sys
sys.path.insert(0, '/Users/mohanganadal/Avisk/Avisk-Core-Services')


all_ok = True


def check(label, got, want):
    global all_ok
    ok = (got == want)
    if not ok:
        all_ok = False
    print('  %s %-50s got=%-25r want=%r' %
          ('✅' if ok else '❌', label+':', got, want))


print('=' * 70)
print('1. _normalize_name')
print('=' * 70)
check('Timothy D. Cook', _normalize_name('Timothy D. Cook'), 'Timothy Cook')
check('Tim Cook', _normalize_name('Tim Cook'), 'Tim Cook')
check('Timothy Donald Cook', _normalize_name(
    'Timothy Donald Cook'), 'Timothy Donald Cook')
check('A B Cook', _normalize_name('A B Cook'), 'Cook')  # strips 2 initials

print()
print('=' * 70)
print('2. _is_valid_name')
print('=' * 70)
# Should be VALID
for n in ['Tim Cook', 'Timothy Cook', 'Timothy D. Cook', 'Steve Jobs',
          'Mary Barra', 'Satya Nadella', 'Jensen Huang']:
    check('VALID: ' + n, _is_valid_name(n), True)
# Should be INVALID
for n in ['Northrop Grumman', 'Restricted Stock Unit', 'Pay Ratio',
          'Compensation Committee', 'Special Advisor', 'Timothy D. A. Cook',
          'Cook',  # single word
          'North America Inc Corp']:  # too many words and blacklisted
    check('INVALID: ' + n, _is_valid_name(n), False)

print()
print('=' * 70)
print('3. SEC 10-K pattern extraction')
print('=' * 70)
cases_sec = [
    # Middle initial cases — THE KEY FIX
    ('officer table with D.',
     '\nTimothy D. Cook    63    Chief Executive Officer\nJeff Williams    54    SVP',
     'Timothy Cook'),
    ('signature block with D.',
     '/s/ Timothy D. Cook\nApple Inc.\nChief Executive Officer',
     'Timothy Cook'),
    # Normal cases
    ('officer table plain',
     '\nTim Cook    63    Chief Executive Officer\n',
     'Tim Cook'),
    ('signature block plain',
     '/s/ Tim Cook\nApple Inc.\nChief Executive Officer',
     'Tim Cook'),
    ('reverse pattern',
     'Chief Executive Officer  Tim Cook announced results.',
     'Tim Cook'),
    # Trap cases — must return None
    ('Northrop Grumman trap',
     '\nNorthrop Grumman    Chief Executive Officer\n',
     None),
    ('Northrop with "of" guard',
     'served as Chief Executive Officer of Northrop Grumman before joining...',
     None),
    ('pay ratio trap',
     '\nPay Ratio    Chief Executive Officer\n',
     None),
    ('special advisor trap',
     '\nSpecial Advisor    Chief Executive Officer\n',
     None),
    ('art levinson mid-sentence',
     'The Committee, chaired by Art Levinson, reviewed the Chief Executive Officer compensation.',
     None),
]
for desc, text, want in cases_sec:
    got = _extract_ceo_from_sec_text(text)
    check(desc, got, want)

print()
print('=' * 70)
print('4. Web/DDGS pattern extraction')
print('=' * 70)
cases_web = [
    ('forward apple ceo',
     'Tim Cook is Apple Chief Executive Officer.',
     'Tim Cook'),
    ('reverse apple ceo',
     "Apple's Chief Executive Officer Tim Cook said...",
     'Tim Cook'),
    ('bloomberg style with D.',
     'Timothy D. Cook, Chief Executive Officer of Apple Inc., spoke at the event.',
     'Timothy Cook'),
    ('CEO: shorthand',
     'CEO: Tim Cook unveiled the new iPhone today.',
     'Tim Cook'),
    ('Northrop 50-char',
     'served as Chief Executive Officer of Northrop Grumman before joining board.',
     None),
]
for desc, text, want in cases_web:
    got = _extract_ceo_from_web_text(text)
    check(desc, got, want)

print()
print('=' * 70)
print('5. FMP fetch for AAPL (live API call)')
print('=' * 70)
name, src = fetch_ceo_from_fmp('AAPL', 2024)
print('  FMP AAPL 2024: name=%r  src=%r' % (name, src))
ok = (name == 'Timothy Cook')
if not ok:
    all_ok = False
print('  %s Expected "Timothy Cook", got %r' % ('✅' if ok else '❌', name))

print()
print('=' * 70)
print('6. DDGS fetch for AAPL (live)')
print('=' * 70)
for yr in [2013, 2015, 2019, 2023]:
    name, src = fetch_ceo_from_ddgs('Apple Inc', yr)
    # Accept any valid form: Tim Cook, Timothy Cook, Timothy Donald Cook
    ok = bool(name and 'Cook' in name and src == 'ddgs')
    if not ok:
        all_ok = False
    print('  %s AAPL %d: name=%r  src=%r' %
          ('✅' if ok else '❌', yr, name, src))

print()
print('=' * 70)
print('RESULT:', '✅ ALL OK' if all_ok else '❌ FAILURES ABOVE')
print('=' * 70)
