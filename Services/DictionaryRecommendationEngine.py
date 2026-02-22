"""
DictionaryRecommendationEngine

Recommends whether a candidate keyword should be Included or Excluded from
each of the three Avisk dictionary contexts:

  • internalization   → t_internalization_dictionary (dictionary_id, keywords, internalization_id)
  • exposure_pathway  → t_exposure_pathway_dictionary (dictionary_id, keywords, exposure_path_id)
  • mitigation        → t_mitigation                  (dictionary_id, keywords)

The engine loads all existing keywords from each context and computes
character-n-gram TF-IDF cosine similarity between the candidate and the
existing terms. High similarity → Include; low similarity → Exclude.

An existing Exclude flat-file list is also consulted to identify terms that
have already been manually marked for exclusion.

Usage::

    from Services.DictionaryRecommendationEngine import DictionaryRecommendationEngine

    engine = DictionaryRecommendationEngine()
    engine.load()

    results = engine.recommend('climate transition')
    # {
    #   'term': 'climate transition',
    #   'contexts': {
    #     'internalization':  { 'action': 'Include', 'confidence': 0.84, 'reason': '...', 'scores': {...} },
    #     'exposure_pathway': { 'action': 'Include', 'confidence': 0.71, 'reason': '...', 'scores': {...} },
    #     'mitigation':       { 'action': 'Exclude', 'confidence': 0.52, 'reason': '...', 'scores': {...} },
    #   }
    # }

    batch = engine.recommend_batch(['carbon', 'lawsuit', 'offset', 'net zero'])
"""

import re
import math
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────

# Minimum cosine similarity to the context vocabulary to recommend Include.
# Below this threshold the term is considered unrelated to the context → Exclude.
INCLUDE_SIMILARITY_THRESHOLD = 0.08

# Minimum number of existing dictionary terms in a context before we trust
# the similarity signal. If fewer terms exist the context is "empty" and we
# return a low-confidence Exclude.
MIN_CONTEXT_TERMS = 3


# ── Context definitions ───────────────────────────────────────────────────────

CONTEXTS = {
    'internalization': {
        'table':       't_internalization_dictionary',
        'keyword_col': 'keywords',
        'description': 'Risk factor internalization — how ESG risks affect company performance',
    },
    'exposure_pathway': {
        'table':       't_exposure_pathway_dictionary',
        'keyword_col': 'keywords',
        'description': 'Exposure pathways — channels through which ESG risks reach the company',
    },
    'mitigation': {
        'table':       't_mitigation',
        'keyword_col': 'keywords',
        'description': 'Mitigation strategies — how the company responds to ESG risks',
    },
}


# ─────────────────────────────────────────────────────────────────────────────

class DictionaryRecommendationEngine:
    """
    Recommends Include / Exclude for candidate keywords by measuring their
    n-gram TF-IDF cosine similarity against existing terms in each of the
    three dictionary context tables.

    Parameters
    ----------
    db_connection : psycopg2 connection, optional
        An open psycopg2 connection.  If None the engine falls back to
        file-based exclusion lists only and marks everything as low-confidence.

    exclude_terms : list of str, optional
        Terms already in the Exclusion flat file.  These are pre-seeded as
        known negatives even before similarity is computed.
    """

    def __init__(self, db_connection=None, exclude_terms: Optional[List[str]] = None):
        self.db_connection = db_connection
        self._known_exclusions: List[str] = [
            t.lower().strip() for t in (exclude_terms or [])
        ]
        # Per-context vocabulary: context_name → list of lowercase keyword strings
        self._vocab: Dict[str, List[str]] = {}
        # Per-context IDF weights
        self._idf: Dict[str, Dict[str, float]] = {}
        self._loaded = False

    # ── Loading ───────────────────────────────────────────────────────────────

    def load(self):
        """
        Fetch existing keywords from all three dictionary tables and build
        TF-IDF vocabularies.  Call once before recommend().
        """
        for ctx_name, cfg in CONTEXTS.items():
            terms = self._fetch_terms(cfg['table'], cfg['keyword_col'])
            self._vocab[ctx_name] = terms
            self._idf[ctx_name] = self._build_idf(terms)
            logger.info(
                f"[{ctx_name}] Loaded {len(terms)} existing dictionary terms "
                f"from {cfg['table']}"
            )
        self._loaded = True

    def _fetch_terms(self, table: str, col: str) -> List[str]:
        """Fetch keyword strings from a dictionary table."""
        terms: List[str] = []
        if not self.db_connection:
            logger.warning(
                f"No DB connection — cannot load terms from {table}")
            return terms
        try:
            cur = self.db_connection.cursor()
            cur.execute(f"SELECT {col} FROM {table} WHERE {col} IS NOT NULL")
            for (kw,) in cur.fetchall():
                cleaned = str(kw).lower().strip()
                if cleaned:
                    terms.append(cleaned)
            cur.close()
        except Exception as e:
            logger.warning(f"Failed to fetch terms from {table}: {e}")
        return terms

    # ── N-gram TF-IDF helpers ─────────────────────────────────────────────────

    @staticmethod
    def _ngrams(text: str, n: int = 2) -> List[str]:
        """Character n-grams (bi-grams default) — robust to spelling variants."""
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

    @staticmethod
    def _word_tokens(text: str) -> List[str]:
        """Simple word tokeniser."""
        return re.findall(r"[a-z][a-z0-9\-']*", text.lower())

    def _term_features(self, text: str) -> List[str]:
        """Combine word tokens + character bigrams for richer matching."""
        return self._word_tokens(text) + self._ngrams(text, n=2)

    def _build_idf(self, terms: List[str]) -> Dict[str, float]:
        """Build IDF weights treating each keyword as a 'document'."""
        if not terms:
            return {}
        df: Dict[str, int] = defaultdict(int)
        for term in terms:
            for feat in set(self._term_features(term)):
                df[feat] += 1
        N = len(terms)
        return {
            feat: math.log((N + 1) / (freq + 1)) + 1.0
            for feat, freq in df.items()
        }

    def _vectorise(self, text: str, idf: Dict[str, float]) -> Dict[str, float]:
        """Create a normalised TF-IDF vector for a text string."""
        tf: Dict[str, int] = defaultdict(int)
        feats = self._term_features(text)
        for f in feats:
            tf[f] += 1
        vec = {f: count * idf.get(f, 0.5) for f, count in tf.items()}
        norm = math.sqrt(sum(v ** 2 for v in vec.values())) or 1.0
        return {f: v / norm for f, v in vec.items()}

    @staticmethod
    def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
        return sum(a.get(k, 0.0) * v for k, v in b.items())

    def _max_similarity_to_vocab(
        self, candidate: str, ctx_name: str
    ) -> Tuple[float, str]:
        """
        Return (max_cosine_similarity, most_similar_existing_term) for the
        candidate against all terms in the context vocabulary.
        """
        idf = self._idf.get(ctx_name, {})
        vocab = self._vocab.get(ctx_name, [])
        if not vocab or not idf:
            return 0.0, ''

        cand_vec = self._vectorise(candidate, idf)
        best_score = 0.0
        best_term = ''
        for existing_term in vocab:
            ev = self._vectorise(existing_term, idf)
            score = self._cosine(cand_vec, ev)
            if score > best_score:
                best_score = score
                best_term = existing_term
        return best_score, best_term

    def _mean_similarity_to_vocab(self, candidate: str, ctx_name: str) -> float:
        """Mean cosine similarity of candidate against top-20 closest vocab terms."""
        idf = self._idf.get(ctx_name, {})
        vocab = self._vocab.get(ctx_name, [])
        if not vocab or not idf:
            return 0.0

        cand_vec = self._vectorise(candidate, idf)
        scores = sorted(
            (self._cosine(cand_vec, self._vectorise(t, idf)) for t in vocab),
            reverse=True,
        )
        top = scores[:20]
        return sum(top) / len(top) if top else 0.0

    # ── Per-context recommendation ────────────────────────────────────────────

    def _recommend_in_context(self, ctx_name: str, candidate: str) -> Dict:
        vocab = self._vocab.get(ctx_name, [])
        idf = self._idf.get(ctx_name, {})
        cand_lower = candidate.lower().strip()

        # ── Fast-path: already a known exclusion ──────────────────────────────
        if cand_lower in self._known_exclusions:
            return {
                'action':     'Exclude',
                'confidence': 1.0,
                'reason':     'Term is already in the Exclusion flat file.',
                'scores': {
                    'max_similarity':  0.0,
                    'mean_similarity': 0.0,
                    'combined': -1.0,
                },
            }

        # ── Fast-path: not enough context to decide ───────────────────────────
        if len(vocab) < MIN_CONTEXT_TERMS:
            return {
                'action':     'Exclude',
                'confidence': 0.1,
                'reason': (
                    f"Context '{ctx_name}' has fewer than {MIN_CONTEXT_TERMS} "
                    f"existing terms — cannot compute similarity reliably."
                ),
                'scores': {
                    'max_similarity':  0.0,
                    'mean_similarity': 0.0,
                    'combined':        0.0,
                },
            }

        # ── Similarity signals ────────────────────────────────────────────────
        max_sim, closest_term = self._max_similarity_to_vocab(
            candidate, ctx_name)
        mean_sim = self._mean_similarity_to_vocab(candidate, ctx_name)

        # Weighted combination (max catches exact/near matches; mean gauges
        # general topical overlap)
        combined = 0.65 * max_sim + 0.35 * mean_sim

        # ── Decision ──────────────────────────────────────────────────────────
        if combined >= INCLUDE_SIMILARITY_THRESHOLD:
            action = 'Include'
            confidence = round(
                min(combined / max(INCLUDE_SIMILARITY_THRESHOLD * 3, 0.001), 1.0), 3)
            reason = (
                f"Similar to existing {ctx_name} term '{closest_term}' "
                f"(max sim: {max_sim:.2f}, mean sim: {mean_sim:.2f}). "
                f"Recommend adding to {CONTEXTS[ctx_name]['description']}."
            )
        else:
            action = 'Exclude'
            confidence = round(min((INCLUDE_SIMILARITY_THRESHOLD - combined) /
                                   max(INCLUDE_SIMILARITY_THRESHOLD, 0.001), 1.0), 3)
            reason = (
                f"Low similarity to {ctx_name} vocabulary "
                f"(max sim: {max_sim:.2f}, mean sim: {mean_sim:.2f}, "
                f"threshold: {INCLUDE_SIMILARITY_THRESHOLD}). "
                f"Term does not appear relevant to "
                f"{CONTEXTS[ctx_name]['description']}."
            )

        return {
            'action':     action,
            'confidence': confidence,
            'reason':     reason,
            'scores': {
                'max_similarity':  round(max_sim, 4),
                'mean_similarity': round(mean_sim, 4),
                'combined':        round(combined, 4),
            },
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def recommend(self, candidate: str) -> Dict:
        """
        Recommend Include / Exclude for `candidate` in all three dictionary
        contexts.

        Returns
        -------
        dict with shape::

            {
              'term': 'climate transition',
              'contexts': {
                'internalization':  {
                    'action':     'Include',
                    'confidence': 0.84,       # 0 = uncertain, 1 = very confident
                    'reason':     'Similar to existing term ...',
                    'scores': {
                        'max_similarity':  0.91,
                        'mean_similarity': 0.42,
                        'combined':        0.74,
                    }
                },
                'exposure_pathway': { ... },
                'mitigation':       { ... },
              }
            }
        """
        if not self._loaded:
            logger.warning("Engine not loaded — call load() first.")

        return {
            'term': candidate,
            'contexts': {
                ctx: self._recommend_in_context(ctx, candidate)
                for ctx in CONTEXTS
            },
        }

    def recommend_batch(self, candidates: List[str]) -> List[Dict]:
        """
        Recommend Include / Exclude for a list of candidate terms.

        Parameters
        ----------
        candidates : list of str

        Returns
        -------
        list of recommend() dicts, one per candidate.
        """
        return [self.recommend(c) for c in candidates]

    # ── Convenience: flat summary for DataFrame display ───────────────────────

    def recommend_to_rows(self, candidates: List[str]) -> List[Dict]:
        """
        Like recommend_batch() but returns one flat row per
        (candidate, context) combination — easy to load into a DataFrame.

        Columns: term, context, action, confidence, reason,
                 max_similarity, mean_similarity, combined
        """
        rows: List[Dict] = []
        for rec in self.recommend_batch(candidates):
            for ctx_name, ctx_rec in rec['contexts'].items():
                rows.append({
                    'term':            rec['term'],
                    'context':         ctx_name,
                    'action':          ctx_rec['action'],
                    'confidence':      ctx_rec['confidence'],
                    'reason':          ctx_rec['reason'],
                    'max_similarity':  ctx_rec['scores']['max_similarity'],
                    'mean_similarity': ctx_rec['scores']['mean_similarity'],
                    'combined':        ctx_rec['scores']['combined'],
                })
        return rows
