from Services.CEODataService import _is_valid_name, _extract_ceo_from_sec_text
import sys
sys.path.insert(0, '.')

bad = [
    'Special Advisor',
    'Pay Ratio',
    'Tim Cook\nMessage',
    'Restricted Stock Unit Award',
    'Compensation Committee Art Levinson',
    'Annual Incentive Plan',
    'Corporate Governance Committee',
    'Independent Director',
    'Human Capital Management',
]
print('=== Should be INVALID ===')
all_ok = True
for n in bad:
    result = _is_valid_name(n)
    flag = '✅' if not result else '❌ STILL PASSES'
    if result:
        all_ok = False
    print(f'  {flag} | {repr(n)}')

good = ['Tim Cook', 'Timothy Cook', 'Timothy Donald Cook', 'Satya Nadella',
        'Mary Barra', 'Jensen Huang', 'Andy Jassy', 'Sundar Pichai']
print()
print('=== Should be VALID ===')
for n in good:
    result = _is_valid_name(n)
    flag = '✅' if result else '❌ REJECTED'
    if not result:
        all_ok = False
    print(f'  {flag} | {n}')

# Test newline-in-text extraction
sample_newline = "Tim Cook\nMessage  Chief Executive Officer  Age 63"
sample_good = "Tim Cook   Chief Executive Officer   Age 63"
sample_pay = "Pay Ratio  Chief Executive Officer earns 1000x"
sample_advisor = "Special Advisor Chief Executive Officer duties"

print()
print('=== Extraction tests ===')
for label, text in [
    ('newline trap',  sample_newline),
    ('clean row',     sample_good),
    ('pay ratio trap', sample_pay),
    ('advisor trap',  sample_advisor),
]:
    name = _extract_ceo_from_sec_text(text)
    print(f'  {label:20} → {repr(name)}')

print()
print('All OK:', all_ok)
