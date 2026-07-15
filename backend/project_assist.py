"""Helpers for interview tips, README drafts, and weekly plans."""

from __future__ import annotations

from anthropic_client import _client, _extract_json, anthropic_enabled, MODEL


def _project_blurb(project: dict) -> str:
    stack = project.get("recommended_tech_stack") or project.get("tech_stack") or []
    return (
        f"Title: {project.get('title')}\n"
        f"Difficulty: {project.get('difficulty')}\n"
        f"Track: {project.get('track')}\n"
        f"Time: {project.get('time_estimate')}\n"
        f"Stack: {', '.join(stack)}\n"
        f"Description: {project.get('description')}\n"
        f"Why: {project.get('why')}\n"
        f"Gaps: {', '.join(project.get('skill_gaps') or [])}"
    )


def interview_talking_points(project: dict, skills: list[str] | None = None) -> dict:
    """Return interview talking points (Claude when available, else heuristic)."""
    skills = skills or []
    if anthropic_enabled():
        try:
            prompt = f"""Write interview talking points for this portfolio project.

User skills: {', '.join(skills) or 'general'}
Project:
{_project_blurb(project)}

Respond ONLY with JSON:
{{"talking_points":["...","...","..."],"common_questions":["...","..."]}}
"""
            message = _client().messages.create(
                model=MODEL,
                max_tokens=700,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(
                block.text for block in message.content if getattr(block, "type", "") == "text"
            )
            data = _extract_json(text)
            return {
                "talking_points": data.get("talking_points") or [],
                "common_questions": data.get("common_questions") or [],
                "source": "anthropic",
            }
        except Exception as exc:  # noqa: BLE001
            print(f"interview_talking_points failed: {exc}")

    title = project.get("title") or "this project"
    gaps = project.get("skill_gaps") or []
    points = [
        f"I chose {title} because it maps to my goals and existing strengths.",
        f"The core stack is {', '.join(project.get('recommended_tech_stack') or project.get('tech_stack') or [])}.",
        "I can walk through tradeoffs, testing, and what I would improve next.",
    ]
    if gaps:
        points.append(f"I'm deliberately leveling up on: {', '.join(gaps[:4])}.")
    return {
        "talking_points": points,
        "common_questions": [
            f"Why did you build {title}?",
            "What was the hardest technical challenge?",
            "How would you scale or extend this?",
        ],
        "source": "heuristic",
    }


def readme_starter(project: dict, skills: list[str] | None = None) -> dict:
    """Generate a README markdown draft."""
    skills = skills or []
    title = project.get("title") or "Project"
    stack = project.get("recommended_tech_stack") or project.get("tech_stack") or []
    milestones = project.get("milestones") or []
    if anthropic_enabled():
        try:
            prompt = f"""Write a polished GitHub README markdown for this project.

Skills: {', '.join(skills) or 'general'}
Project:
{_project_blurb(project)}

Respond ONLY with JSON: {{"readme_markdown":"...full markdown..."}}
"""
            message = _client().messages.create(
                model=MODEL,
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(
                block.text for block in message.content if getattr(block, "type", "") == "text"
            )
            data = _extract_json(text)
            md = data.get("readme_markdown") or ""
            if md:
                return {"readme_markdown": md, "source": "anthropic"}
        except Exception as exc:  # noqa: BLE001
            print(f"readme_starter failed: {exc}")

    ms = "\n".join(f"- [ ] {m}" for m in milestones) or "- [ ] Ship MVP"
    md = f"""# {title}

{project.get('description') or ''}

## Why this project
{project.get('why') or ''}

## Tech stack
{chr(10).join(f'- {s}' for s in stack) or '- TBD'}

## Getting started
1. Clone the repo
2. Install dependencies
3. Run the app locally
4. Follow the milestones below

## Milestones
{ms}

## Stretch ideas
- Add tests and CI
- Deploy a demo link
- Write a short architecture note
"""
    return {"readme_markdown": md, "source": "heuristic"}


def weekly_plan(project: dict, skills: list[str] | None = None) -> dict:
    """Turn a project into a 7-day plan."""
    skills = skills or []
    milestones = list(project.get("milestones") or [])
    while len(milestones) < 4:
        milestones.append("Polish docs and demos")

    if anthropic_enabled():
        try:
            prompt = f"""Create a practical 7-day build plan for this project.

Skills: {', '.join(skills) or 'general'}
Project:
{_project_blurb(project)}

Respond ONLY with JSON:
{{"days":[{{"day":1,"focus":"...","tasks":["..."]}}]}}
"""
            message = _client().messages.create(
                model=MODEL,
                max_tokens=900,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(
                block.text for block in message.content if getattr(block, "type", "") == "text"
            )
            data = _extract_json(text)
            days = data.get("days") or []
            if days:
                return {"days": days, "source": "anthropic"}
        except Exception as exc:  # noqa: BLE001
            print(f"weekly_plan failed: {exc}")

    plan = [
        {"day": 1, "focus": "Setup", "tasks": ["Create repo", "Scaffold project", milestones[0]]},
        {"day": 2, "focus": "Core build", "tasks": [milestones[1], "Commit working MVP slice"]},
        {"day": 3, "focus": "Deepen feature", "tasks": ["Expand main flow", "Handle edge cases"]},
        {"day": 4, "focus": "Hardening", "tasks": [milestones[2], "Add basic tests"]},
        {"day": 5, "focus": "Polish", "tasks": ["Improve UX/docs", "Fix bugs"]},
        {"day": 6, "focus": "Ship", "tasks": [milestones[3], "Deploy or record demo"]},
        {"day": 7, "focus": "Reflect", "tasks": ["Write README", "List interview talking points"]},
    ]
    return {"days": plan, "source": "heuristic"}
