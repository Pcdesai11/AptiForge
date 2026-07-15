"""Recommend projects from skills + optional learning goals."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from utils.text_cleaner import clean_text

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def load_projects() -> list[dict]:
    current_dir = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(current_dir, "..", "data", "project_ideas.json"))
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def recommend_projects(
    user_skills: list[str] | None = None,
    learning_goals: str = "",
    top_k: int = 5,
) -> list[dict]:
    """
    Score catalog projects by skill overlap + goal similarity.
    Each result includes matched tags and a short 'why' explanation.
    """
    user_skills = [s.lower() for s in (user_skills or [])]
    projects = load_projects()
    goals_clean = clean_text(learning_goals)
    goal_scores = _goal_similarity_scores(goals_clean, projects) if goals_clean else {}

    scored: list[tuple[float, dict]] = []

    for project in projects:
        tags = [t.lower() for t in project.get("tags", [])]
        matched = sorted(set(tags).intersection(user_skills))
        skill_score = float(len(matched))
        goal_score = float(goal_scores.get(project.get("id", project["title"]), 0.0))

        # Prefer skills, boost when goals align
        total = skill_score * 2.0 + goal_score * 3.0

        # Soft fallback: if no skills/goals match anything, still surface beginners lightly
        if total == 0 and not user_skills and not goals_clean:
            total = 0.1 if project.get("difficulty") == "beginner" else 0.0

        if total <= 0:
            continue

        why_parts = []
        if matched:
            why_parts.append(f"Matches your skills: {', '.join(matched)}.")
        if goal_score > 0.05 and goals_clean:
            why_parts.append("Aligns with your stated learning goals.")
        if not why_parts:
            why_parts.append("A solid next step based on available signals.")

        enriched = {
            **project,
            "matched_skills": matched,
            "score": round(total, 3),
            "why": " ".join(why_parts),
            "recommended_tech_stack": project.get("tech_stack", tags),
        }
        scored.append((total, enriched))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [item for _, item in scored[:top_k]]

    # If nothing matched, return top beginner/general projects with neutral why
    if not results:
        beginners = [p for p in projects if p.get("difficulty") == "beginner"] or projects
        for p in beginners[:top_k]:
            results.append(
                {
                    **p,
                    "matched_skills": [],
                    "score": 0.0,
                    "why": "Suggested starter project while we gather more skill/goal signal.",
                    "recommended_tech_stack": p.get("tech_stack", p.get("tags", [])),
                }
            )
    return results


def build_roadmap(projects: list[dict], title: str = "My AptiForge Roadmap") -> dict:
    """Create a simple ordered roadmap payload suitable for export."""
    steps = []
    for i, project in enumerate(projects, start=1):
        steps.append(
            {
                "order": i,
                "title": project.get("title"),
                "difficulty": project.get("difficulty"),
                "tech_stack": project.get("recommended_tech_stack")
                or project.get("tech_stack")
                or project.get("tags", []),
                "why": project.get("why", ""),
                "description": project.get("description", ""),
            }
        )
    return {
        "title": title,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_count": len(steps),
        "steps": steps,
    }


def export_roadmap_markdown(roadmap: dict) -> str:
    """Render roadmap dict as Markdown text."""
    lines = [
        f"# {roadmap.get('title', 'AptiForge Roadmap')}",
        "",
        f"_Created: {roadmap.get('created_at', '')}_",
        "",
    ]
    for step in roadmap.get("steps", []):
        stack = ", ".join(step.get("tech_stack") or [])
        lines.extend(
            [
                f"## {step.get('order')}. {step.get('title')}",
                f"- **Difficulty:** {step.get('difficulty')}",
                f"- **Tech stack:** {stack}",
                f"- **Why it fits:** {step.get('why')}",
                f"- **Description:** {step.get('description')}",
                "",
            ]
        )
    return "\n".join(lines)


def _goal_similarity_scores(goals_clean: str, projects: list[dict]) -> dict[str, float]:
    """TF-IDF cosine similarity between goals and each project's focus text."""
    ids = []
    corpus = []
    for project in projects:
        pid = project.get("id", project["title"])
        ids.append(pid)
        text = " ".join(
            [
                project.get("title", ""),
                project.get("description", ""),
                project.get("learning_focus", ""),
                " ".join(project.get("tags", [])),
                " ".join(project.get("tech_stack", [])),
            ]
        )
        corpus.append(clean_text(text))

    if HAS_SKLEARN and len(corpus) >= 1:
        try:
            vectorizer = TfidfVectorizer(stop_words="english")
            matrix = vectorizer.fit_transform([goals_clean] + corpus)
            sims = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
            return {pid: float(score) for pid, score in zip(ids, sims)}
        except ValueError:
            pass

    # Fallback: keyword overlap ratio
    goal_tokens = set(goals_clean.split())
    scores = {}
    for pid, text in zip(ids, corpus):
        tokens = set(text.split())
        if not tokens:
            scores[pid] = 0.0
        else:
            scores[pid] = len(goal_tokens & tokens) / max(len(goal_tokens), 1)
    return scores
