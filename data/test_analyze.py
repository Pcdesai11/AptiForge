"""Manual smoke test for POST /analyze_resume."""

import os
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
url = "http://127.0.0.1:5000/analyze_resume"
file_path = os.path.join(ROOT, "resume_sample.txt")

with open(file_path, "rb") as f:
    response = requests.post(
        url,
        files={"file": f},
        data={"learning_goals": "I want to get better at Docker and APIs", "top_k": "3"},
    )

print("Status Code:", response.status_code)
print("Raw Response Text:")
print(response.text)
data = response.json()

print("\nExtracted Skills:")
print(data.get("skills"))

print("\nRecommended Projects:")
for proj in data.get("recommended_projects", []):
    print("-", proj["title"], "|", proj.get("why"))
