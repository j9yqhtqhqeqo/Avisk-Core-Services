"""
DictionaryRecommendationEngine

Recommends whether a validation pair should be Included or Excluded in the
keyword context dictionaries.

Each candidate is a pair:

  KEYWORD : RELATED_TERM

The engine compares RELATED_TERM against the historical InclusionDictionary
and ExclusionDictionary entries that already exist for that KEYWORD.
Recommendations are intentionally conservative:

  - exact historical exclusion  -> Exclude
  - exact historical inclusion  -> Include
  - suspicious fragment/code hit -> Exclude
  - otherwise compare similarity to historical include vs exclude examples

This aligns the recommendation path with how validation files are actually
resolved by ContextResolver.
"""

import ast
import logging
import math
import os
import re
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

from Utilities.PathConfiguration import PathConfiguration

logger = logging.getLogger(__name__)


# Minimum similarity needed before a historical example is treated as
# meaningful evidence.
MATCH_SIMILARITY_THRESHOLD = 0.32

# Require a visible gap between include and exclude evidence before returning
# Include. When evidence is close, bias toward Exclude.
DECISION_MARGIN = 0.05


path_config = PathConfiguration()
INCLUSION_DICTIONARY_PATH = os.path.join(
    os.path.dirname(path_config.get_new_include_dict_term_path()),
    'InclusionDictionary.txt',
)
EXCLUSION_DICTIONARY_PATH = os.path.join(
    os.path.dirname(path_config.get_new_exclude_dict_term_path()),
    'ExclusionDictionary.txt',
)


class DictionaryRecommendationEngine:
    """
    Recommend Include / Exclude for KEYWORD:RELATED_TERM validation pairs.

    Parameters
    ----------
    db_connection : optional
        Retained for backward compatibility. Not used by the current engine.

    exclude_terms : optional
        Retained for backward compatibility. Not used by the current engine.
    """

    def __init__(self, db_connection=None, exclude_terms=None):
        self.db_connection = db_connection
        self.exclude_terms = exclude_terms
        self._include_history: Dict[str, List[str]] = {}
        self._exclude_history: Dict[str, List[str]] = {}
        self._loaded = False

    def load(self):
        """Load historical include/exclude dictionaries from disk."""
        self._include_history = self._load_dictionary(
            INCLUSION_DICTIONARY_PATH)
        self._exclude_history = self._load_dictionary(
            EXCLUSION_DICTIONARY_PATH)
        logger.info(
            "Loaded %s include keywords and %s exclude keywords",
            len(self._include_history),
            len(self._exclude_history),
        )
        self._loaded = True

    def _load_dictionary(self, file_path: str) -> Dict[str, List[str]]:
        if not os.path.exists(file_path):
            logger.warning("Dictionary file not found: %s", file_path)
            return {}

        with open(file_path, 'r') as handle:
            raw = handle.read().strip() or '{}'

        try:
            parsed = ast.literal_eval(raw)
        except Exception as exc:
            logger.warning(
                "Failed to parse dictionary file %s: %s", file_path, exc)
            return {}

        history: Dict[str, List[str]] = {}
        for keyword, values in parsed.items():
            key = str(keyword).upper().strip()
            history[key] = self._as_string_list(values)
        return history

    @staticmethod
    def _as_string_list(values) -> List[str]:
        if isinstance(values, list):
            return [str(value).upper().strip() for value in values if str(value).strip()]
        if isinstance(values, tuple):
            return [str(value).upper().strip() for value in values if str(value).strip()]
        if values is None:
            return []
        value = str(values).upper().strip()
        return [value] if value else []

    @staticmethod
    def _word_tokens(text: str) -> List[str]:
        return re.findall(r"[a-z0-9][a-z0-9\-']*", text.lower())

    @staticmethod
    def _ngrams(text: str, n: int = 2) -> List[str]:
        cleaned = re.sub(r'[^a-z0-9 ]', ' ', text.lower())
        tokens = cleaned.split()
        result: List[str] = []
        for token in tokens:
            if len(token) < n:
                result.append(token)
            else:
                result.extend(token[i:i + n]
                              for i in range(len(token) - n + 1))
        return result

    def _term_features(self, text: str) -> List[str]:
        return self._word_tokens(text) + self._ngrams(text, n=2)

    def _build_idf(self, terms: Iterable[str]) -> Dict[str, float]:
        terms = list(terms)
        if not terms:
            return {}

        document_frequency: Dict[str, int] = defaultdict(int)
        for term in terms:
            for feature in set(self._term_features(term)):
                document_frequency[feature] += 1

        total = len(terms)
        return {
            feature: math.log((total + 1) / (count + 1)) + 1.0
            for feature, count in document_frequency.items()
        }

    def _vectorise(self, text: str, idf: Dict[str, float]) -> Dict[str, float]:
        term_frequency: Dict[str, int] = defaultdict(int)
        for feature in self._term_features(text):
            term_frequency[feature] += 1

        vector = {
            feature: count * idf.get(feature, 0.5)
            for feature, count in term_frequency.items()
        }
        norm = math.sqrt(sum(value ** 2 for value in vector.values())) or 1.0
        return {feature: value / norm for feature, value in vector.items()}

    @staticmethod
    def _cosine(left: Dict[str, float], right: Dict[str, float]) -> float:
        return sum(left.get(key, 0.0) * value for key, value in right.items())

    def _similarity_to_history(self, candidate: str, history_terms: List[str]) -> Dict[str, object]:
        if not history_terms:
            return {
                'max_similarity': 0.0,
                'mean_similarity': 0.0,
                'combined': 0.0,
                'closest_term': '',
                'shared_tokens': [],
            }

        idf = self._build_idf(history_terms)
        candidate_vector = self._vectorise(candidate, idf)

        scores: List[Tuple[float, str]] = []
        for history_term in history_terms:
            history_vector = self._vectorise(history_term, idf)
            scores.append(
                (self._cosine(candidate_vector, history_vector), history_term))

        scores.sort(reverse=True, key=lambda item: item[0])
        max_similarity, closest_term = scores[0]
        top_scores = [score for score, _ in scores[:10]]
        mean_similarity = sum(top_scores) / len(top_scores)
        combined = 0.7 * max_similarity + 0.3 * mean_similarity

        return {
            'max_similarity': max_similarity,
            'mean_similarity': mean_similarity,
            'combined': combined,
            'closest_term': closest_term,
            'shared_tokens': self._shared_word_tokens(candidate, closest_term),
        }

    def _shared_word_tokens(self, left: str, right: str) -> List[str]:
        left_tokens = {token for token in self._word_tokens(
            left) if len(token) >= 3}
        right_tokens = {token for token in self._word_tokens(
            right) if len(token) >= 3}
        return sorted(left_tokens & right_tokens)

    @staticmethod
    def _url_like_pattern(text: str) -> bool:
        text_lower = text.lower().strip()
        return bool(
            re.search(r"(https?://|www\.|\.com\b|\.org\b|\.net\b|/)", text_lower)
        )

    def _has_oversized_word(self, text: str) -> bool:
        return any(len(token) > 25 for token in re.findall(r"[A-Za-z]+", text))

    def _forced_exclude_reason(self, related_term: str) -> Optional[str]:
        if self._url_like_pattern(related_term):
            return 'Related term looks like a URL or path and should be excluded.'
        if self._has_oversized_word(related_term):
            return 'Related term contains a word longer than 25 letters and should be excluded.'
        return None

    def _is_suspicious_fragment_match(self, keyword: str, related_term: str) -> bool:
        keyword_clean = keyword.upper().strip()
        related_clean = related_term.upper().strip()
        if not keyword_clean or keyword_clean == related_clean:
            return False

        if keyword_clean not in related_clean:
            return False

        related_tokens = {token.upper()
                          for token in self._word_tokens(related_term)}
        if keyword_clean in related_tokens:
            return False

        return keyword_clean.isdigit() or len(keyword_clean) <= 3

    def _confidence_from_gap(self, winner: float, loser: float) -> float:
        gap = max(winner - loser, 0.0)
        return round(min(0.35 + gap * 2.5, 0.99), 3)

    def _recommend_pair(self, keyword: str, related_term: str) -> Dict[str, object]:
        keyword_clean = str(keyword).upper().strip()
        related_clean = str(related_term).upper().strip()
        include_terms = self._include_history.get(keyword_clean, [])
        exclude_terms = self._exclude_history.get(keyword_clean, [])

        forced_exclude_reason = self._forced_exclude_reason(related_clean)
        if forced_exclude_reason:
            return {
                'keyword': keyword_clean,
                'related_term': related_clean,
                'action': 'Exclude',
                'confidence': 0.99,
                'reason': forced_exclude_reason,
                'closest_include_term': '',
                'closest_exclude_term': '',
                'include_max_similarity': 0.0,
                'include_mean_similarity': 0.0,
                'exclude_max_similarity': 0.0,
                'exclude_mean_similarity': 0.0,
            }

        if related_clean in exclude_terms:
            return {
                'keyword': keyword_clean,
                'related_term': related_clean,
                'action': 'Exclude',
                'confidence': 1.0,
                'reason': 'Exact match found in ExclusionDictionary for this keyword.',
                'closest_include_term': '',
                'closest_exclude_term': related_clean,
                'include_max_similarity': 0.0,
                'include_mean_similarity': 0.0,
                'exclude_max_similarity': 1.0,
                'exclude_mean_similarity': 1.0,
            }

        if related_clean in include_terms:
            return {
                'keyword': keyword_clean,
                'related_term': related_clean,
                'action': 'Include',
                'confidence': 1.0,
                'reason': 'Exact match found in InclusionDictionary for this keyword.',
                'closest_include_term': related_clean,
                'closest_exclude_term': '',
                'include_max_similarity': 1.0,
                'include_mean_similarity': 1.0,
                'exclude_max_similarity': 0.0,
                'exclude_mean_similarity': 0.0,
            }

        if self._is_suspicious_fragment_match(keyword_clean, related_clean):
            return {
                'keyword': keyword_clean,
                'related_term': related_clean,
                'action': 'Exclude',
                'confidence': 0.98,
                'reason': (
                    'Related term appears to contain the keyword only as a short '
                    'fragment/code match, which is usually a false positive.'
                ),
                'closest_include_term': '',
                'closest_exclude_term': '',
                'include_max_similarity': 0.0,
                'include_mean_similarity': 0.0,
                'exclude_max_similarity': 0.0,
                'exclude_mean_similarity': 0.0,
            }

        if not include_terms and not exclude_terms:
            return {
                'keyword': keyword_clean,
                'related_term': related_clean,
                'action': 'Exclude',
                'confidence': 0.15,
                'reason': 'No historical include/exclude entries exist for this keyword.',
                'closest_include_term': '',
                'closest_exclude_term': '',
                'include_max_similarity': 0.0,
                'include_mean_similarity': 0.0,
                'exclude_max_similarity': 0.0,
                'exclude_mean_similarity': 0.0,
            }

        include_stats = self._similarity_to_history(
            related_clean, include_terms)
        exclude_stats = self._similarity_to_history(
            related_clean, exclude_terms)

        include_score = float(include_stats['combined'])
        exclude_score = float(exclude_stats['combined'])

        if exclude_score >= MATCH_SIMILARITY_THRESHOLD and (
            exclude_score >= include_score + DECISION_MARGIN or
            float(exclude_stats['max_similarity']) >= 0.5
        ):
            reason = (
                f"Closer to excluded term '{exclude_stats['closest_term']}' "
                f"(score: {exclude_score:.2f}) than to included history "
                f"(score: {include_score:.2f})."
            )
            if exclude_stats['shared_tokens']:
                reason += f" Shared tokens with excluded history: {', '.join(exclude_stats['shared_tokens'])}."
            return {
                'keyword': keyword_clean,
                'related_term': related_clean,
                'action': 'Exclude',
                'confidence': self._confidence_from_gap(exclude_score, include_score),
                'reason': reason,
                'closest_include_term': str(include_stats['closest_term']),
                'closest_exclude_term': str(exclude_stats['closest_term']),
                'include_max_similarity': round(float(include_stats['max_similarity']), 4),
                'include_mean_similarity': round(float(include_stats['mean_similarity']), 4),
                'exclude_max_similarity': round(float(exclude_stats['max_similarity']), 4),
                'exclude_mean_similarity': round(float(exclude_stats['mean_similarity']), 4),
            }

        if include_score >= MATCH_SIMILARITY_THRESHOLD and (
            include_score >= exclude_score + DECISION_MARGIN and (
                bool(include_stats['shared_tokens']) or
                float(include_stats['max_similarity']) >= 0.45
            )
        ):
            reason = (
                f"Closer to included term '{include_stats['closest_term']}' "
                f"(score: {include_score:.2f}) than to excluded history "
                f"(score: {exclude_score:.2f})."
            )
            if include_stats['shared_tokens']:
                reason += f" Shared tokens with included history: {', '.join(include_stats['shared_tokens'])}."
            return {
                'keyword': keyword_clean,
                'related_term': related_clean,
                'action': 'Include',
                'confidence': self._confidence_from_gap(include_score, exclude_score),
                'reason': reason,
                'closest_include_term': str(include_stats['closest_term']),
                'closest_exclude_term': str(exclude_stats['closest_term']),
                'include_max_similarity': round(float(include_stats['max_similarity']), 4),
                'include_mean_similarity': round(float(include_stats['mean_similarity']), 4),
                'exclude_max_similarity': round(float(exclude_stats['max_similarity']), 4),
                'exclude_mean_similarity': round(float(exclude_stats['mean_similarity']), 4),
            }

        return {
            'keyword': keyword_clean,
            'related_term': related_clean,
            'action': 'Exclude',
            'confidence': self._confidence_from_gap(max(exclude_score, include_score), min(exclude_score, include_score)),
            'reason': (
                'No strong positive evidence from historical inclusion entries. '
                f"Closest include score: {include_score:.2f}; closest exclude score: {exclude_score:.2f}."
            ),
            'closest_include_term': str(include_stats['closest_term']),
            'closest_exclude_term': str(exclude_stats['closest_term']),
            'include_max_similarity': round(float(include_stats['max_similarity']), 4),
            'include_mean_similarity': round(float(include_stats['mean_similarity']), 4),
            'exclude_max_similarity': round(float(exclude_stats['max_similarity']), 4),
            'exclude_mean_similarity': round(float(exclude_stats['mean_similarity']), 4),
        }

    def _coerce_candidate(self, candidate) -> Tuple[str, str]:
        if isinstance(candidate, dict):
            keyword = candidate.get('Keyword', candidate.get('keyword', ''))
            related_term = candidate.get(
                'Related Term', candidate.get('related_term', ''))
            return str(keyword), str(related_term)
        if isinstance(candidate, (list, tuple)) and len(candidate) >= 2:
            return str(candidate[0]), str(candidate[1])
        return str(candidate), str(candidate)

    def recommend(self, keyword: str, related_term: Optional[str] = None) -> Dict[str, object]:
        if not self._loaded:
            logger.warning('Engine not loaded — call load() first.')
        if related_term is None:
            related_term = keyword
        return self._recommend_pair(keyword, related_term)

    def recommend_batch(self, candidates) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        for candidate in candidates:
            keyword, related_term = self._coerce_candidate(candidate)
            rows.append(self.recommend(keyword, related_term))
        return rows

    def recommend_to_rows(self, candidates) -> List[Dict[str, object]]:
        return self.recommend_batch(candidates)
