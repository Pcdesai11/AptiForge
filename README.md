# AptiForge

Personalized project recommender for developers.

AptiForge helps you discover coding project ideas from your **resume**, **GitHub activity**, and **learning goals**. It extracts skills, ranks a project catalog with skill overlap + TF-IDF goal similarity, and exports a roadmap.

## Features

- Upload a resume (**PDF**, **DOCX**, or **TXT**) and extract tech skills
- Analyze a public **GitHub** profile for languages and strengths
- Enter **learning goals** in plain English
- Get personalized suggestions with tech stack, difficulty, and **why it fits you**
- **Save/export** recommended projects as Markdown or JSON roadmap

## Project layout

```
AptiForge-1/
├── backend/
│   ├── app.py                 # Flask API + serves UI
│   ├── resume_parser.py       # PDF/DOCX/TXT skill extraction
│   ├── github_parser.py       # GitHub profile analysis
│   ├── project_recommender.py # Ranking + roadmap export
│   ├── requirements.txt
│   └── utils/text_cleaner.py
├── frontend/
│   ├── index.html             # Primary web UI
│   └── streamlit_app.py       # Optional Streamlit UI
├── data/
│   └── project_ideas.json     # Project catalog
└── resume_sample.txt
```

## Setup

```bash
cd backend
python -m venv ../.venv

# Windows
..\.venv\Scripts\activate

# macOS / Linux
# source ../.venv/bin/activate

pip install -r requirements.txt
copy ..\.env.example ..\.env   # optional: set GITHUB_TOKEN
```

## Run

```bash
cd backend
python app.py
```

Open **http://127.0.0.1:5000/** for the UI.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Web UI |
| GET | `/api` | API info |
| POST | `/upload_resume` | Extract skills from a resume file |
| POST | `/analyze_resume` | Skills + optional GitHub/goals + recommendations |
| POST | `/analyze_github` | JSON `{"username": "..."}` |
| POST | `/recommend_projects` | JSON skills + learning goals |
| POST | `/export_roadmap` | JSON projects → roadmap Markdown/JSON |

### Optional Streamlit UI

Requires `streamlit` (may need a separate install if wheels are unavailable on your platform):

```bash
pip install streamlit
streamlit run frontend/streamlit_app.py
```

## Quick tests (API must be running)

```bash
python data/test_upload.py
python data/test_analyze.py
python data/test_recommend.py
```

## Tech stack

- **Backend:** Flask, Flask-CORS, requests, pypdf, python-docx
- **Ranking:** skill intersection + scikit-learn TF-IDF cosine similarity
- **Frontend:** HTML/CSS/JS served by Flask (Streamlit optional)
- **Optional env:** `GITHUB_TOKEN` (see `.env.example`)

## Status

Core MVP is end-to-end: parse → recommend → export. Contributions welcome.
