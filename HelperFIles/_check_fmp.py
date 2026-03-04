from Services.CEODataService import _fmp_get, _is_valid_name
import sys
sys.path.insert(0, '.')

# Check /key-executives
data = _fmp_get('/key-executives', {'symbol': 'AAPL'})
print('key-executives:', data)
print()
# Check _is_valid_name with middle initial
for n in ['Timothy D. Cook', 'Tim Cook', 'Timothy Cook', 'Northrop Grumman']:
    print('_is_valid_name(%r) = %s' % (n, _is_valid_name(n)))
