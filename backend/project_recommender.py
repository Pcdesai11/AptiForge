"""Recommend projects from skills + goals via semantic search + optional Claude."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from anthropic_client import (
    anthropic_enabled,
    enrich_why_explanations,
    generate_custom_project,
)
from semantic_search import WEAK_SCORE_THRESHOLD, semantic_scores
from utils.text_cleaner import clean_text


def load_projects() -> list[dict]:
    current_dir = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(current_dir, "..", "data", "project_ideas.json"))
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def recommend_projects(
    user_skills: list[str] | None = None,
    learning_goals: str = "",
    top_k: int = 5,
    use_ai: bool = True,
) -> list[dict]:
    """
    Rank catalog projects with skill overlap + semantic similarity.
    Optionally enrich `why` with Anthropic and invent a custom project when fits are weak.
    """
    user_skills = [s.lower() for s in (user_skills or [])]
    projects = load_projects()
    goals_clean = clean_text(learning_goals)

    sem_scores, sem_source = semantic_scores(user_skills, learning_goals, projects)

    scored: list[tuple[float, dict]] = []

    for project in projects:
        tags = [t.lower() for t in project.get("tags", [])]
        matched = sorted(set(tags).intersection(user_skills))
        skill_score = float(len(matched))
        pid = project.get("id", project["title"])
        goal_score = float(sem_scores.get(pid, 0.0))

        # Skills count for ranking; semantic similarity boosts goal/content fit
        total = skill_score * 2.0 + goal_score * 4.0

        if total == 0 and not user_skills and not goals_clean:
            total = 0.1 if project.get("difficulty") == "beginner" else 0.0

        if total <= 0:
            continue

        why_parts = []
        if matched:
            why_parts.append(f"Matches your skills: {', '.join(matched)}.")
        if goal_score > 0.05 and (goals_clean or user_skills):
            why_parts.append("Ranks highly on semantic similarity to your profile and goals.")
        if not why_parts:
            why_parts.append("A solid next step based on available signals.")

        enriched = {
            **project,
            "matched_skills": matched,
            "score": round(total, 3),
            "semantic_score": round(goal_score, 3),
            "semantic_source": sem_source,
            "why": " ".join(why_parts),
            "why_source": "heuristic",
            "recommended_tech_stack": project.get("tech_stack", tags),
            "custom": False,
            "source": "catalog",
        }
        scored.append((total, enriched))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [item for _, item in scored[:top_k]]

    best_score = scored[0][0] if scored else 0.0
    weak_fit = (not results) or best_score < WEAK_SCORE_THRESHOLD

    # Soft catalog fallback when no overlaps at all
    if not results:
        beginners = [p for p in projects if p.get("difficulty") == "beginner"] or projects
        for p in beginners[:top_k]:
            results.append(
                {
                    **p,
                    "matched_skills": [],
                    "score": 0.0,
                    "semantic_score": 0.0,
                    "semantic_source": sem_source,
                    "why": "Suggested starter project while we gather more skill/goal signal.",
                    "why_source": "heuristic",
                    "recommended_tech_stack": p.get("tech_stack", p.get("tags", [])),
                    "custom": False,
                    "source": "catalog",
                }
            )

    # Invent a custom project when catalog fit is weak and Anthropic is available
    if use_ai and weak_fit and anthropic_enabled():
        custom = generate_custom_project(user_skills, learning_goals)
        if custom:
            # Put custom first, keep remaining catalog slots under top_k
            results = [custom] + [p for p in results if not p.get("custom")][: max(top_k - 1, 0)]

    if use_ai and anthropic_enabled() and results:
        results = enrich_why_explanations(results, user_skills, learning_goals)

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
                "custom": bool(project.get("custom")),
                "milestones": project.get("milestones") or [],
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
        badge = " (custom generated)" if step.get("custom") else ""
        lines.extend(
            [
                f"## {step.get('order')}. {step.get('title')}{badge}",
                f"- **Difficulty:** {step.get('difficulty')}",
                f"- **Tech stack:** {stack}",
                f"- **Why it fits:** {step.get('why')}",
                f"- **Description:** {step.get('description')}",
            ]
        )
        milestones = step.get("milestones") or []
        if milestones:
            lines.append("- **Milestones:**")
            for m in milestones:
                lines.append(f"  - {m}")
        lines.append("")
    return "\n".join(lines)
