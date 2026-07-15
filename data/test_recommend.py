"""Manual smoke test for POST /recommend_projects."""

import requests

url = "http://127.0.0.1:5000/recommend_projects"
payload = {
    "skills": ["python", "flask", "git", "docker"],
    "learning_goals": "I want to learn backend APIs and CI/CD",
    "top_k": 3,
}

response = requests.post(url, json=payload)

print("Status Code:", response.status_code)
print("Recommended Projects:")
for p in response.json().get("projects", []):
    print("-", p["title"], "|", p.get("why"))
