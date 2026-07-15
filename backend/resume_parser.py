"""Extract tech skills from resume text (PDF/DOCX/TXT)."""

from __future__ import annotations

import re
from io import BytesIO

from utils.text_cleaner import clean_text

TECH_KEYWORDS = {
    "python", "java", "c++", "c#", "go", "golang", "rust", "ruby", "swift",
    "kotlin", "html", "css", "javascript", "typescript", "react", "vue",
    "angular", "next.js", "node.js", "express", "flask", "django", "fastapi",
    "sql", "mysql", "postgresql", "mongodb", "redis", "aws", "azure", "gcp",
    "docker", "kubernetes", "git", "github", "tensorflow", "pytorch",
    "pandas", "numpy", "scikit-learn", "ci/cd", "rest", "api", "graphql",
    "machine learning", "deep learning", "nlp", "linux", "bash", "terraform",
}

# Multi-word / punctuated terms checked as phrases; short aliases use word boundaries
ALIASES = {
    "golang": "go",
    "postgres": "postgresql",
    "node": "node.js",
    "nodejs": "node.js",
    "nextjs": "next.js",
    "ml": "machine learning",
    "dl": "deep learning",
    "k8s": "kubernetes",
    "apis": "api",
    "ci cd": "ci/cd",
    "c plus plus": "c++",
    "c sharp": "c#",
    "node js": "node.js",
    "next js": "next.js",
}


def extract_skills(text: str) -> list[str]:
    """Return sorted unique tech skills found in text."""
    normalized = clean_text(text)
    found: set[str] = set()

    for keyword in TECH_KEYWORDS:
        if _contains_term(normalized, keyword):
            found.add("go" if keyword == "golang" else keyword)

    for alias, canonical in ALIASES.items():
        if _contains_term(normalized, alias):
            found.add(canonical)

    return sorted(found)


def _contains_term(text: str, term: str) -> bool:
    """True when term appears as a whole token/phrase (avoids 'go' in 'django')."""
    term = term.strip().lower()
    if not term:
        return False
    # Escape, but treat spaces flexibly for multi-word skills
    pattern = r"(?<!\w)" + re.escape(term).replace(r"\ ", r"\s+") + r"(?!\w)"
    return re.search(pattern, text) is not None


def read_resume_bytes(filename: str, data: bytes) -> str:
    """Decode resume bytes based on file extension."""
    name = (filename or "").lower()

    if name.endswith(".pdf"):
        return _read_pdf(data)
    if name.endswith(".docx"):
        return _read_docx(data)
    return data.decode("utf-8", errors="ignore")


def _read_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _read_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs)
