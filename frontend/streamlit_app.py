"""AptiForge Streamlit UI (optional).

Prefer the built-in web UI at http://127.0.0.1:5000/ when Streamlit
wheels are unavailable on your platform.

  streamlit run frontend/streamlit_app.py
"""

from __future__ import annotations

import json
import os
import sys

import streamlit as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND = os.path.join(ROOT, "backend")
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from github_parser import analyze_github_profile  # noqa: E402
from project_recommender import (  # noqa: E402
    build_roadmap,
    export_roadmap_markdown,
    recommend_projects,
)
from resume_parser import extract_skills, read_resume_bytes  # noqa: E402

st.set_page_config(page_title="AptiForge", page_icon="🛠️", layout="wide")
st.title("AptiForge")
st.caption("Personalized coding project ideas from your resume, GitHub, and learning goals.")

with st.sidebar:
    resume_file = st.file_uploader("Upload resume (PDF, DOCX, or TXT)", type=["pdf", "docx", "txt"])
    github_username = st.text_input("GitHub username (optional)", placeholder="octocat")
    learning_goals = st.text_area("Learning goals", placeholder="I want to learn backend with Go", height=100)
    top_k = st.slider("Number of recommendations", 1, 8, 5)
    run = st.button("Generate recommendations", type="primary", use_container_width=True)

if not run:
    st.info("Upload a resume and/or add goals, then generate recommendations.")
    st.stop()

skills: list[str] = []
github = None
error = None

with st.spinner("Analyzing…"):
    if resume_file is not None:
        text = read_resume_bytes(resume_file.name, resume_file.getvalue())
        skills = extract_skills(text)
    skill_set = set(skills)
    if github_username:
        github = analyze_github_profile(github_username)
        if not github.get("error"):
            skill_set.update(github.get("skills", []))
        else:
            error = github.get("error")
    skills = sorted(skill_set)
    projects = recommend_projects(skills, learning_goals=learning_goals, top_k=top_k)

if error:
    st.warning(error)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Detected skills")
    st.write(", ".join(skills) if skills else "None detected yet.")
with col2:
    st.subheader("GitHub summary")
    st.write(github.get("strengths", "") if github and not github.get("error") else "No GitHub analysis yet.")

st.subheader("Recommended projects")
for project in projects:
    with st.expander(f"{project['title']} · {project.get('difficulty', '')}", expanded=True):
        st.write(project.get("description", ""))
        stack = project.get("recommended_tech_stack") or project.get("tech_stack") or []
        st.markdown(f"**Tech stack:** {', '.join(stack)}")
        st.markdown(f"**Why it fits:** {project.get('why', '')}")

roadmap = build_roadmap(projects)
md = export_roadmap_markdown(roadmap)
st.download_button("Download roadmap (Markdown)", data=md, file_name="aptiforge_roadmap.md", mime="text/markdown")
st.download_button(
    "Download roadmap (JSON)",
    data=json.dumps(roadmap, indent=2),
    file_name="aptiforge_roadmap.json",
    mime="application/json",
)
