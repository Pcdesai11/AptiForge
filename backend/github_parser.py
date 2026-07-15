"""Analyze a public GitHub profile for languages and strengths."""

from __future__ import annotations

import os
from collections import Counter

import requests

from utils.text_cleaner import clean_text

LANG_TO_SKILL = {
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "java": "java",
    "c++": "c++",
    "c#": "c#",
    "go": "go",
    "rust": "rust",
    "ruby": "ruby",
    "swift": "swift",
    "kotlin": "kotlin",
    "html": "html",
    "css": "css",
    "dockerfile": "docker",
    "shell": "bash",
    "jupyter notebook": "python",
}

KNOWN_TOPICS = {
    "python", "javascript", "typescript", "react", "flask", "django",
    "docker", "kubernetes", "aws", "machine learning", "api", "node.js",
    "mongodb", "postgresql", "tensorflow", "pytorch", "go",
}


def analyze_github_profile(username: str, token: str | None = None) -> dict:
    """Fetch public repos and summarize languages / strengths."""
    username = (username or "").strip().lstrip("@")
    if not username:
        return {"error": "GitHub username is required"}

    token = token or os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AptiForge",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/users/{username}/repos"
    try:
        resp = requests.get(
            url,
            headers=headers,
            params={"per_page": 40, "sort": "updated"},
            timeout=20,
        )
    except requests.RequestException as exc:
        return {"error": f"GitHub request failed: {exc}"}

    if resp.status_code == 404:
        return {"error": f"GitHub user '{username}' not found"}
    if resp.status_code != 200:
        return {"error": f"GitHub API error ({resp.status_code})"}

    repos = resp.json()
    lang_counter: Counter[str] = Counter()
    topic_skills: set[str] = set()
    repo_names: list[str] = []

    for repo in repos:
        if repo.get("fork"):
            continue
        repo_names.append(repo.get("name") or "")
        language = repo.get("language")
        if language:
            lang_counter[language] += 1
        for topic in repo.get("topics") or []:
            topic_skills.add(clean_text(topic))

    return _build_summary(username, lang_counter, topic_skills, repo_names)


def _build_summary(
    username: str,
    lang_counter: Counter,
    topic_skills: set[str],
    repo_names: list[str],
) -> dict:
    skills: set[str] = set()
    top_languages = []

    for lang, count in lang_counter.most_common(8):
        top_languages.append({"language": lang, "repos": count})
        skill = LANG_TO_SKILL.get(lang.lower())
        if skill:
            skills.add(skill)

    for topic in topic_skills:
        if topic in KNOWN_TOPICS:
            skills.add(topic)
        if topic in ("nodejs", "node"):
            skills.add("node.js")
        if topic in ("k8s",):
            skills.add("kubernetes")

    strengths = []
    if top_languages:
        lead = ", ".join(f"{x['language']} ({x['repos']})" for x in top_languages[:3])
        strengths.append(f"Most-used languages: {lead}.")
    if skills:
        strengths.append(f"Detected skills from repos: {', '.join(sorted(skills))}.")
    if not strengths:
        strengths.append("No public language data found for this profile.")

    return {
        "username": username,
        "repo_count": len([n for n in repo_names if n]),
        "top_languages": top_languages,
        "skills": sorted(skills),
        "strengths": " ".join(strengths),
    }
