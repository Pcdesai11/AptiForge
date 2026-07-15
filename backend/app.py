"""AptiForge Flask API + web UI."""

from __future__ import annotations

import os
import traceback

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from github_parser import analyze_github_profile
from project_recommender import (
    build_roadmap,
    export_roadmap_markdown,
    recommend_projects,
)
from resume_parser import extract_skills, read_resume_bytes
from anthropic_client import anthropic_enabled
from semantic_search import pinecone_enabled

load_dotenv()

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

app = Flask(__name__)
CORS(app)


def parse_top_k(raw, default: int = 5) -> tuple[int, tuple | None]:
    """Parse top_k into an int in [1, 20]. Returns (value, error_response)."""
    if raw is None or raw == "":
        return default, None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default, (jsonify({"error": "top_k must be an integer"}), 400)
    if value < 1 or value > 20:
        return default, (jsonify({"error": "top_k must be between 1 and 20"}), 400)
    return value, None


def _parse_use_ai(raw) -> bool:
    if raw is None:
        return True
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


@app.route("/", methods=["GET"])
def home():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(index_path):
        return send_from_directory(FRONTEND_DIR, "index.html")
    return jsonify(_api_payload())


def _api_payload() -> dict:
    return {
        "name": "AptiForge API",
        "status": "ok",
        "ai": {
            "anthropic": anthropic_enabled(),
            "pinecone": pinecone_enabled(),
        },
        "endpoints": [
            "GET /sample_resume",
            "POST /upload_resume",
            "POST /analyze_resume",
            "POST /analyze_github",
            "POST /recommend_projects",
            "POST /export_roadmap",
            "GET /api",
        ],
    }


@app.route("/api", methods=["GET"])
def api_info():
    return jsonify(_api_payload())


@app.route("/sample_resume", methods=["GET"])
def sample_resume():
    """Serve the bundled sample resume for one-click demos."""
    sample_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "resume_sample.txt")
    )
    if not os.path.isfile(sample_path):
        return jsonify({"error": "Sample resume not found"}), 404
    return send_from_directory(
        os.path.dirname(sample_path),
        os.path.basename(sample_path),
        mimetype="text/plain",
        as_attachment=False,
        download_name="resume_sample.txt",
    )


@app.route("/upload_resume", methods=["POST"])
def upload_resume():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    try:
        resume_text = read_resume_bytes(file.filename, file.read())
        skills = extract_skills(resume_text)
        return jsonify({"skills": skills, "chars_read": len(resume_text)})
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Failed to parse resume"}), 500


@app.route("/analyze_resume", methods=["POST"])
def analyze_resume():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    learning_goals = request.form.get("learning_goals", "")
    github_username = request.form.get("github_username", "").strip()
    top_k, top_k_error = parse_top_k(request.form.get("top_k", 5))
    if top_k_error:
        return top_k_error
    use_ai = _parse_use_ai(request.form.get("use_ai", "true"))

    try:
        resume_text = read_resume_bytes(file.filename, file.read())
        skills = set(extract_skills(resume_text))

        github = None
        if github_username:
            github = analyze_github_profile(github_username)
            if not github.get("error"):
                skills.update(github.get("skills", []))

        skills_list = sorted(skills)
        projects = recommend_projects(
            skills_list,
            learning_goals=learning_goals,
            top_k=top_k,
            use_ai=use_ai,
        )

        return jsonify(
            {
                "skills": skills_list,
                "learning_goals": learning_goals,
                "github": github,
                "recommended_projects": projects,
                "ai": {
                    "requested": use_ai,
                    "anthropic": anthropic_enabled(),
                    "pinecone": pinecone_enabled(),
                },
            }
        )
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500


@app.route("/analyze_github", methods=["POST"])
def analyze_github():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username") or request.form.get("username", "")
    result = analyze_github_profile(username)
    if result.get("error"):
        return jsonify(result), 400
    return jsonify(result)


@app.route("/recommend_projects", methods=["POST"])
def recommend_projects_route():
    payload = request.get_json(silent=True) or {}
    skills = payload.get("skills", [])
    learning_goals = payload.get("learning_goals", "")
    top_k, top_k_error = parse_top_k(payload.get("top_k", 5))
    if top_k_error:
        return top_k_error
    use_ai = _parse_use_ai(payload.get("use_ai", True))

    projects = recommend_projects(
        skills,
        learning_goals=learning_goals,
        top_k=top_k,
        use_ai=use_ai,
    )
    return jsonify(
        {
            "projects": projects,
            "count": len(projects),
            "ai": {
                "requested": use_ai,
                "anthropic": anthropic_enabled(),
                "pinecone": pinecone_enabled(),
            },
        }
    )


@app.route("/export_roadmap", methods=["POST"])
def export_roadmap():
    payload = request.get_json(silent=True) or {}
    projects = payload.get("projects", [])
    title = payload.get("title", "My AptiForge Roadmap")
    fmt = (payload.get("format") or "json").lower()

    if not projects:
        return jsonify({"error": "No projects provided"}), 400

    roadmap = build_roadmap(projects, title=title)
    if fmt == "markdown":
        return jsonify({"format": "markdown", "content": export_roadmap_markdown(roadmap)})
    return jsonify({"format": "json", "roadmap": roadmap})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
