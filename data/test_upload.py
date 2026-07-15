"""Manual smoke test for POST /upload_resume."""

import os
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
url = "http://127.0.0.1:5000/upload_resume"
file_path = os.path.join(ROOT, "resume_sample.txt")

with open(file_path, "rb") as f:
    response = requests.post(url, files={"file": f})

print("Status Code:", response.status_code)
print("Response JSON:", response.json())
