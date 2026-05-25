from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
	sys.path.insert(0, str(ROOT_DIR))

import psycopg2  # type: ignore[reportMissingModuleSource]

from Utilities.Lookups import DB_Connection


CSV_PATH = ROOT_DIR / 'Clients' / 'sp500_market_cap_ranked.csv'
SYSTEM_USER = 'SectorTopListClassifier'

SUFFIX_PATTERN = re.compile(
	r'\b('
	r'CORPORATION|CORP|INCORPORATED|INC|COMPANY|CO|HOLDINGS|HOLDING|'
	r'GROUP|PLC|LTD|LIMITED|N V|N\.V|S A|S\.A|LP|LLC'
	r')\b'
)
CLASS_PATTERN = re.compile(r'\bCLASS\s+[A-Z]\b')
CAMELCASE_PATTERN = re.compile(r'(?<=[a-z])(?=[A-Z])')
NUMBER_CASE_PATTERN = re.compile(r'(?<=[A-Za-z])(?=\d[A-Za-z])|(?<=\d)(?=[A-Za-z])')
DESCRIPTOR_PATTERN = re.compile(
	r'\b('
	r'THE|ORDINARY|SHARE|SHARES|COMMON|STOCK|TRUST|HLDG|HLDGS'
	r')\b'
)
NON_ALNUM_PATTERN = re.compile(r'[^A-Z0-9]+')
WHITESPACE_PATTERN = re.compile(r'\s+')
EXPLICIT_COMPANY_ALIASES = {
	'RTX': 'RAYTHEON TECHNOLOGIES',
	'A O SMITH': 'SMITH AO',
	'BNY MELLON': 'BANK OF NEW YORK MELLON',
	'MOODY S': 'MOODYS',
	'FREEPORT MC MO RAN': 'FREEPORT MC MORAN COPPER AND GOLD',
	'W W GRAINGER': 'WW GRAINGER',
	'D R HORTON': 'DR HORTON',
	'WABTEC': 'WESTINGHOUSE AIR BRAKE TECHNOLOGIES',
	'HARTFORD': 'HARTFORD FINANCIAL SERVICES',
	'COGNIZANT': 'COGNIZANT TECHNOLOGY SOLUTIONS',
	'EST E LAUDER COMPANIES': 'ESTEE LAUDER COMPANIES',
	'LABCORP': 'LABORATORY OF AMERICA',
	'C H ROBINSON': 'CH ROBINSON WORLDWIDE',
	'DU PONT': 'DUPONT DE NEMOURS',
	'J B HUNT': 'JB HUNT TRANSPORT SERVICES',
	'DECKERS BRANDS': 'DECKERS OUTDOOR',
	'SUPERMICRO': 'SUPER MICRO COMPUTER',
	'MOLSON COORS BEVERAGE': 'MOLSON COORS BREWING',
	'BXP': 'BOSTON PROPERTIES',
	'CONAGRA BRANDS': 'CON AGRA FOODS',
	'DA VITA': 'DA VITA HEALTH CARE PARTNERS',
	'LILLY ELI': 'ELI LILLY AND',
	'PARAMOUNT SKYDANCE': 'PARAMOUNT GLOBAL',
}


@dataclass(frozen=True)
class RankedCompany:
	rank: int
	company: str
	category: str


@dataclass(frozen=True)
class RankedIndexes:
	by_normalized_name: dict[str, RankedCompany]
	by_sorted_tokens: dict[str, list[RankedCompany]]
	by_acronym: dict[str, list[RankedCompany]]


def normalize_company_name(company_name: str) -> str:
	normalized = (company_name or '').strip()
	normalized = CAMELCASE_PATTERN.sub(' ', normalized)
	normalized = NUMBER_CASE_PATTERN.sub(' ', normalized)
	normalized = normalized.upper()
	normalized = normalized.replace('&', ' AND ')
	normalized = CLASS_PATTERN.sub(' ', normalized)
	normalized = normalized.replace('(', ' ').replace(')', ' ')
	normalized = SUFFIX_PATTERN.sub(' ', normalized)
	normalized = DESCRIPTOR_PATTERN.sub(' ', normalized)
	normalized = NON_ALNUM_PATTERN.sub(' ', normalized)
	normalized = WHITESPACE_PATTERN.sub(' ', normalized).strip()
	return normalized


def company_tokens(company_name: str) -> list[str]:
	return [token for token in normalize_company_name(company_name).split() if token]


def token_signature(tokens: list[str]) -> str:
	return ' '.join(sorted(tokens))


def company_acronym(tokens: list[str]) -> str:
	acronym_parts = [token[0] for token in tokens if token and token[0].isalpha()]
	return ''.join(acronym_parts)


def category_for_rank(rank: int) -> str:
	if rank <= 10:
		return 'Top 10'
	if rank <= 25:
		return 'Top 25'
	if rank <= 50:
		return 'Top 50'
	if rank <= 100:
		return 'Top 100'
	if rank <= 250:
		return 'Top250'
	return 'Top 500'


def load_ranked_companies(csv_path: Path) -> dict[str, RankedCompany]:
	dataframe = pd.read_csv(csv_path)
	dataframe.columns = [column.strip().lower() for column in dataframe.columns]
	dataframe['company'] = dataframe['company'].astype(str).str.strip()
	dataframe['rank'] = pd.to_numeric(dataframe['rank'], errors='coerce')
	dataframe = dataframe.dropna(subset=['company', 'rank']).copy()
	dataframe['rank'] = dataframe['rank'].astype(int)

	ranked_companies: dict[str, RankedCompany] = {}
	for row in dataframe[['rank', 'company']].itertuples(index=False, name=None):
		rank, company = cast(tuple[int, str], row)
		normalized_name = normalize_company_name(company)
		ranked_company = RankedCompany(
			rank=rank,
			company=company,
			category=category_for_rank(rank),
		)
		existing = ranked_companies.get(normalized_name)
		if existing is None or ranked_company.rank < existing.rank:
			ranked_companies[normalized_name] = ranked_company

	return ranked_companies


def build_ranked_indexes(ranked_companies: dict[str, RankedCompany]) -> RankedIndexes:
	by_sorted_tokens: dict[str, list[RankedCompany]] = {}
	by_acronym: dict[str, list[RankedCompany]] = {}

	for normalized_name, ranked_company in ranked_companies.items():
		tokens = normalized_name.split()
		signature = token_signature(tokens)
		by_sorted_tokens.setdefault(signature, []).append(ranked_company)

		acronym = company_acronym(tokens)
		if len(acronym) >= 2:
			by_acronym.setdefault(acronym, []).append(ranked_company)

	return RankedIndexes(
		by_normalized_name=ranked_companies,
		by_sorted_tokens=by_sorted_tokens,
		by_acronym=by_acronym,
	)


def resolve_ranked_company(company_name: str, ranked_indexes: RankedIndexes) -> RankedCompany | None:
	raw_name = (company_name or '').upper()
	if 'NEWS CORP' in raw_name and 'CLASS A' in raw_name:
		news_a_match = ranked_indexes.by_normalized_name.get('NEWS A')
		if news_a_match is not None:
			return news_a_match
	if 'NEWS CORP' in raw_name and 'CLASS B' in raw_name:
		news_b_match = ranked_indexes.by_normalized_name.get('NEWS B')
		if news_b_match is not None:
			return news_b_match

	normalized_name = normalize_company_name(company_name)
	direct_match = ranked_indexes.by_normalized_name.get(normalized_name)
	if direct_match is not None:
		return direct_match

	alias_target = EXPLICIT_COMPANY_ALIASES.get(normalized_name)
	if alias_target is not None:
		alias_match = ranked_indexes.by_normalized_name.get(alias_target)
		if alias_match is not None:
			return alias_match

	tokens = company_tokens(company_name)
	if not tokens:
		return None

	signature = token_signature(tokens)
	signature_matches = ranked_indexes.by_sorted_tokens.get(signature, [])
	if len(signature_matches) == 1:
		return signature_matches[0]

	if len(tokens) == 1 and len(tokens[0]) <= 5:
		acronym_matches = ranked_indexes.by_acronym.get(tokens[0], [])
		if len(acronym_matches) == 1:
			return acronym_matches[0]

	input_token_set = set(tokens)
	best_match: RankedCompany | None = None
	best_score = 0.0
	ambiguous = False

	for official_name, ranked_company in ranked_indexes.by_normalized_name.items():
		official_tokens = official_name.split()
		official_token_set = set(official_tokens)
		if tokens[0] != official_tokens[0]:
			continue
		overlap = input_token_set & official_token_set
		if not overlap:
			continue

		if not (input_token_set.issubset(official_token_set) or official_token_set.issubset(input_token_set)):
			continue

		score = len(overlap) / max(len(input_token_set), len(official_token_set))
		if score < 0.5:
			continue

		if score > best_score:
			best_match = ranked_company
			best_score = score
			ambiguous = False
		elif abs(score - best_score) < 1e-9:
			ambiguous = True

	if not ambiguous and best_match is not None:
		return best_match

	return None


def fetch_companies(connection: Any) -> list[tuple[int, str, str | None]]:
	cursor = connection.cursor()
	cursor.execute(
		"""
		SELECT company_id, conformed_name, topxsp500category
		FROM t_sec_company
		ORDER BY company_id
		"""
	)
	rows = cursor.fetchall()
	cursor.close()
	return rows


def build_updates(
	companies: list[tuple[int, str, str | None]],
	ranked_indexes: RankedIndexes,
) -> tuple[list[tuple[str, int]], list[tuple[int, str]], list[tuple[int, str, str]]]:
	updates: list[tuple[str, int]] = []
	unmatched: list[tuple[int, str]] = []
	matches: list[tuple[int, str, str]] = []

	for company_id, conformed_name, current_category in companies:
		ranked_company = resolve_ranked_company(conformed_name, ranked_indexes)
		if ranked_company is None:
			unmatched.append((company_id, conformed_name))
			continue

		matches.append((company_id, conformed_name, ranked_company.category))
		if current_category != ranked_company.category:
			updates.append((ranked_company.category, company_id))

	return updates, unmatched, matches


def apply_updates(connection: Any, updates: list[tuple[str, int]]) -> None:
	if not updates:
		return

	cursor = connection.cursor()
	cursor.executemany(
		"""
		UPDATE t_sec_company
		SET topxsp500category = %s,
			modify_dt = CURRENT_TIMESTAMP,
			modify_by = %s
		WHERE company_id = %s
		""",
		[(category, SYSTEM_USER, company_id) for category, company_id in updates],
	)
	cursor.close()
	connection.commit()


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description='Update t_sec_company.topxsp500category from the ranked S&P 500 CSV.'
	)
	parser.add_argument(
		'--csv-path',
		type=Path,
		default=CSV_PATH,
		help='Path to the ranked S&P 500 CSV file.',
	)
	parser.add_argument(
		'--apply',
		action='store_true',
		help='Apply updates to the database. Without this flag the script runs in dry-run mode.',
	)
	parser.add_argument(
		'--show-unmatched',
		type=int,
		default=20,
		help='Number of unmatched company names to print in the summary.',
	)
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	ranked_companies = load_ranked_companies(args.csv_path)
	ranked_indexes = build_ranked_indexes(ranked_companies)

	connection_string = DB_Connection().DB_CONNECTION_STRING
	if not connection_string:
		raise ValueError('DB_CONNECTION_STRING is not configured')

	connection = psycopg2.connect(connection_string)
	try:
		companies = fetch_companies(connection)
		updates, unmatched, matches = build_updates(companies, ranked_indexes)

		print(f'Total companies in t_sec_company: {len(companies)}')
		print(f'Matched to ranked S&P 500 list: {len(matches)}')
		print(f'Rows needing category changes: {len(updates)}')
		print(f'Unmatched companies: {len(unmatched)}')

		if unmatched and args.show_unmatched > 0:
			print('Sample unmatched companies:')
			for company_id, company_name in unmatched[:args.show_unmatched]:
				print(f'  {company_id}: {company_name}')

		if args.apply:
			apply_updates(connection, updates)
			print('Database update complete.')
		else:
			print('Dry run complete. Re-run with --apply to persist changes.')
	finally:
		connection.close()


if __name__ == '__main__':
	main()
