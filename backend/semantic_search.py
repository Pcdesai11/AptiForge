"""Semantic project search: local TF-IDF vectors, optional Pinecone index."""

from __future__ import annotations

import hashlib
import os
import re
from functools import lru_cache

from utils.text_cleaner import clean_text

try:
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.preprocessing import normalize

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

EMBED_DIM = 64
WEAK_SCORE_THRESHOLD = 1.5


def pinecone_enabled() -> bool:
    return bool(os.getenv("PINECONE_API_KEY", "").strip()) and bool(
        os.getenv("PINECONE_INDEX", "").strip()
    )


def project_document(project: dict) -> str:
    return clean_text(
        " ".join(
            [
                project.get("title", ""),
                project.get("description", ""),
                project.get("learning_focus", ""),
                " ".join(project.get("tags", [])),
                " ".join(project.get("tech_stack", [])),
            ]
        )
    )


def query_document(skills: list[str], learning_goals: str) -> str:
    return clean_text(f"{' '.join(skills)} {learning_goals}")


@lru_cache(maxsize=1)
def _fit_local_model(corpus_key: str, corpus: tuple[str, ...]):
    """Fit TF-IDF (+ SVD densifier for Pinecone-compatible vectors)."""
    if not HAS_SKLEARN or not corpus:
        return None
    vectorizer = TfidfVectorizer(stop_words="english", max_features=2048)
    tfidf = vectorizer.fit_transform(list(corpus))
    n_components = min(EMBED_DIM, max(2, tfidf.shape[0] - 1), tfidf.shape[1])
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    dense = normalize(svd.fit_transform(tfidf))
    return vectorizer, svd, dense


def local_semantic_scores(skills: list[str], learning_goals: str, projects: list[dict]) -> dict[str, float]:
    """Return id -> similarity using local TF-IDF cosine similarity."""
    query = query_document(skills, learning_goals)
    if not query or not projects:
        return {}

    ids = [p.get("id", p["title"]) for p in projects]
    corpus = [project_document(p) for p in projects]
    corpus_key = hashlib.sha1("||".join(corpus).encode("utf-8")).hexdigest()

    if HAS_SKLEARN:
        try:
            fitted = _fit_local_model(corpus_key, tuple(corpus))
            if fitted is None:
                raise ValueError("no model")
            vectorizer, _svd, _dense = fitted
            # Recompute full matrix for query similarity (cached model gives vectorizer)
            matrix = vectorizer.transform([query] + corpus)
            sims = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
            return {pid: float(s) for pid, s in zip(ids, sims)}
        except Exception:
            pass

    q_tokens = set(query.split())
    scores = {}
    for pid, doc in zip(ids, corpus):
        tokens = set(doc.split())
        scores[pid] = len(q_tokens & tokens) / max(len(q_tokens), 1) if tokens else 0.0
    return scores


def dense_vector_for_text(text: str, projects: list[dict]) -> list[float] | None:
    """Build a fixed dense vector for Pinecone upsert/query."""
    if not HAS_SKLEARN or not text.strip() or not projects:
        return None
    corpus = [project_document(p) for p in projects]
    corpus_key = hashlib.sha1("||".join(corpus).encode("utf-8")).hexdigest()
    try:
        fitted = _fit_local_model(corpus_key, tuple(corpus))
        if fitted is None:
            return None
        vectorizer, svd, _ = fitted
        tfidf = vectorizer.transform([clean_text(text)])
        vec = normalize(svd.transform(tfidf))[0]
        # Pad/truncate to EMBED_DIM for a stable Pinecone dimension
        values = vec.tolist()
        if len(values) < EMBED_DIM:
            values = values + [0.0] * (EMBED_DIM - len(values))
        return values[:EMBED_DIM]
    except Exception:
        return None


_UPSERTED_INDEX = None


def pinecone_semantic_scores(skills: list[str], learning_goals: str, projects: list[dict]) -> dict[str, float]:
    """
    Query Pinecone for semantic neighbors. Upserts catalog vectors once per process
    when PINECONE_API_KEY + PINECONE_INDEX are set.
    """
    if not pinecone_enabled() or not projects:
        return {}

    try:
        from pinecone import Pinecone
    except ImportError:
        print("pinecone package not installed; skipping Pinecone search")
        return {}

    api_key = os.getenv("PINECONE_API_KEY", "")
    index_name = os.getenv("PINECONE_INDEX", "")
    query = query_document(skills, learning_goals)
    query_vec = dense_vector_for_text(query, projects)
    if not query_vec:
        return {}

    try:
        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)
        _ensure_pinecone_upserts(index, index_name, projects)

        result = index.query(vector=query_vec, top_k=min(20, len(projects)), include_metadata=True)
        matches = result.get("matches") if isinstance(result, dict) else getattr(result, "matches", [])
        scores: dict[str, float] = {}
        for match in matches or []:
            if isinstance(match, dict):
                meta = match.get("metadata") or {}
                pid = meta.get("original_id") or match.get("id")
                score = float(match.get("score") or 0.0)
            else:
                meta = getattr(match, "metadata", None) or {}
                pid = (meta.get("original_id") if isinstance(meta, dict) else None) or getattr(match, "id", None)
                score = float(getattr(match, "score", 0.0) or 0.0)
            if pid:
                scores[str(pid)] = score
        return scores
    except Exception as exc:  # noqa: BLE001
        print(f"Pinecone search failed: {exc}")
        return {}


def _ensure_pinecone_upserts(index, index_name: str, projects: list[dict]) -> None:
    """Best-effort upsert of catalog documents as dense vectors (once per cold start)."""
    global _UPSERTED_INDEX
    if _UPSERTED_INDEX == index_name:
        return

    vectors = []
    for project in projects:
        pid = str(project.get("id") or project.get("title"))
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "-", pid)[:512]
        values = dense_vector_for_text(project_document(project), projects)
        if not values:
            continue
        vectors.append(
            {
                "id": safe_id,
                "values": values,
                "metadata": {
                    "title": project.get("title", ""),
                    "original_id": pid,
                },
            }
        )
    if not vectors:
        return
    for i in range(0, len(vectors), 50):
        index.upsert(vectors=vectors[i : i + 50])
    _UPSERTED_INDEX = index_name


def semantic_scores(skills: list[str], learning_goals: str, projects: list[dict]) -> tuple[dict[str, float], str]:
    """
    Prefer Pinecone when configured; otherwise local TF-IDF.
    Returns (scores_by_id, source_label).
    """
    if pinecone_enabled():
        scores = pinecone_semantic_scores(skills, learning_goals, projects)
        if scores:
            return scores, "pinecone"
    return local_semantic_scores(skills, learning_goals, projects), "tfidf"
