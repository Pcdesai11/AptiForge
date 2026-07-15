"""Optional Anthropic (Claude) helpers for AptiForge."""

from __future__ import annotations

import json
import os
import re
from typing import Any

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")


def anthropic_enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def _client():
    from anthropic import Anthropic

    return Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _extract_json(text: str) -> Any:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def enrich_why_explanations(
    projects: list[dict],
    skills: list[str],
    learning_goals: str = "",
) -> list[dict]:
    """
    Keep ranking intact; replace each project's `why` with a richer Claude explanation.
    Falls back silently to the original why on any failure.
    """
    if not anthropic_enabled() or not projects:
        return projects

    compact = [
        {
            "id": p.get("id") or p.get("title"),
            "title": p.get("title"),
            "description": p.get("description"),
            "difficulty": p.get("difficulty"),
            "tech_stack": p.get("recommended_tech_stack") or p.get("tech_stack") or [],
            "matched_skills": p.get("matched_skills") or [],
            "base_why": p.get("why") or "",
        }
        for p in projects
    ]

    prompt = f"""You help developers choose coding projects.

User skills: {", ".join(skills) or "none listed"}
Learning goals: {learning_goals or "none listed"}

For each project below, write a personalized 2-3 sentence "why it fits" explanation.
Be specific about how their skills and goals connect to the project. Do not invent skills they do not have.

Projects JSON:
{json.dumps(compact, indent=2)}

Respond with ONLY valid JSON:
{{"explanations":[{{"id":"...","why":"..."}}]}}
"""

    try:
        message = _client().messages.create(
            model=MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        payload = _extract_json(text)
        by_id = {
            item["id"]: item["why"]
            for item in payload.get("explanations", [])
            if item.get("id") and item.get("why")
        }
        updated = []
        for project in projects:
            pid = project.get("id") or project.get("title")
            clone = {**project}
            if pid in by_id:
                clone["why"] = by_id[pid]
                clone["why_source"] = "anthropic"
            updated.append(clone)
        return updated
    except Exception as exc:  # noqa: BLE001 — optional enrichment must not break requests
        print(f"Anthropic enrich_why failed: {exc}")
        return projects


def generate_custom_project(skills: list[str], learning_goals: str = "") -> dict | None:
    """Invent one tailored project when catalog matches are weak."""
    if not anthropic_enabled():
        return None

    prompt = f"""Invent ONE coding project for this developer.

Skills: {", ".join(skills) or "general programming"}
Learning goals: {learning_goals or "grow as a developer and build portfolio pieces"}

Constraints:
- Practical for a portfolio or interview conversation
- Difficulty one of: beginner, intermediate, advanced
- Prefer building on existing skills while stretching toward the goals
- Include a crisp description and short milestone outline

Respond with ONLY valid JSON:
{{
  "id": "custom-kebab-id",
  "title": "...",
  "difficulty": "beginner|intermediate|advanced",
  "track": "backend|frontend|ml|devops",
  "time_estimate": "e.g. 1-2 weekends",
  "description": "...",
  "tech_stack": ["..."],
  "tags": ["lowercase","skills"],
  "learning_focus": "short phrase",
  "milestones": ["step 1", "step 2", "step 3"],
  "why": "2-3 sentences on why this fits"
}}
"""

    try:
        message = _client().messages.create(
            model=MODEL,
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        data = _extract_json(text)
        stack = data.get("tech_stack") or data.get("tags") or []
        tags = [str(t).lower() for t in (data.get("tags") or [])]
        stack_l = [str(t).lower() for t in stack]
        skill_set = {s.lower() for s in skills}
        return {
            "id": data.get("id") or "custom-generated",
            "title": data.get("title") or "Custom Generated Project",
            "difficulty": data.get("difficulty") or "intermediate",
            "track": data.get("track") or "",
            "time_estimate": data.get("time_estimate") or "",
            "description": data.get("description") or "",
            "tech_stack": stack,
            "tags": tags,
            "learning_focus": data.get("learning_focus") or "",
            "milestones": data.get("milestones") or [],
            "matched_skills": sorted(skill_set.intersection(set(stack_l + tags))),
            "score": 0.0,
            "why": data.get("why") or "Custom project generated from your skills and goals.",
            "recommended_tech_stack": stack,
            "custom": True,
            "why_source": "anthropic",
            "source": "generated",
        }
    except Exception as exc:  # noqa: BLE001
        print(f"Anthropic generate_custom_project failed: {exc}")
        return None
