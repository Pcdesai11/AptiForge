"""Extract tech skills from resume text (PDF/DOCX/TXT)."""

from __future__ import annotations

import re
from io import BytesIO

from utils.text_cleaner import clean_text

ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx", ".txt"}

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

RESUME_HINTS = {
    "experience", "education", "skills", "skill", "summary", "objective",
    "employment", "internship", "intern", "university", "college", "bachelor",
    "master", "degree", "resume", "curriculum vitae", "cv", "projects",
    "certification", "certifications", "work history", "professional",
    "linkedin", "github", "phone", "email", "responsibilities",
    "achievements", "profile", "career", "gpa", "coursework",
}


class ResumeValidationError(ValueError):
    """Raised when an upload does not look like a usable resume."""


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


def validate_resume_upload(filename: str, data: bytes) -> str:
    """
    Parse and validate an uploaded file as a resume.
    Returns extracted text, or raises ResumeValidationError with a clear message.
    """
    name = (filename or "").strip()
    if not name:
        raise ResumeValidationError("Please choose a resume file to upload.")

    lower = name.lower()
    ext = ""
    if "." in lower:
        ext = "." + lower.rsplit(".", 1)[-1]

    if ext not in ALLOWED_RESUME_EXTENSIONS:
        raise ResumeValidationError(
            "That file doesn't look like a resume. Please upload a PDF, DOCX, or TXT resume."
        )

    if not data or len(data) < 20:
        raise ResumeValidationError(
            "This file is empty or too small to be a resume. Please upload a complete resume."
        )

    # Reject obvious non-document binaries even if misnamed .txt
    if ext == ".txt" and b"\x00" in data[:2000]:
        raise ResumeValidationError(
            "That file doesn't look like a resume. Please upload a PDF, DOCX, or TXT resume."
        )

    try:
        text = read_resume_bytes(name, data)
    except Exception as exc:
        raise ResumeValidationError(
            "We couldn't read that file as a resume. Please upload a text-based PDF, DOCX, or TXT."
        ) from exc

    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    if len(cleaned) < 40:
        raise ResumeValidationError(
            "We couldn't find enough readable text in that file. "
            "It may be an image-only PDF or not a resume - try a text-based PDF, DOCX, or TXT."
        )

    if not looks_like_resume(cleaned):
        raise ResumeValidationError(
            "This doesn't appear to be a resume. Upload a resume with sections like "
            "experience, education, or skills (PDF, DOCX, or TXT)."
        )

    return text


def looks_like_resume(text: str) -> bool:
    """Heuristic: resume-like markers and/or tech skills + contact signals."""
    normalized = clean_text(text)
    if not normalized:
        return False

    hint_hits = sum(1 for hint in RESUME_HINTS if _contains_term(normalized, hint))
    skills = extract_skills(text)
    has_email = bool(re.search(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", text, re.I))
    has_phone = bool(re.search(r"(\+?\d[\d\s().-]{7,}\d)", text))

    if hint_hits >= 2:
        return True
    if hint_hits >= 1 and (skills or has_email or has_phone):
        return True
    if len(skills) >= 3 and (has_email or has_phone or hint_hits >= 1):
        return True
    if hint_hits >= 1 and len(normalized) >= 200:
        return True
    return False


def _contains_term(text: str, term: str) -> bool:
    """True when term appears as a whole token/phrase (avoids 'go' in 'django')."""
    term = term.strip().lower()
    if not term:
        return False
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
