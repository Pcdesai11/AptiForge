import requests

url = "http://127.0.0.1:5000/recommend_projects"
skills = ['python', 'flask', 'git', 'docker']

response = requests.post(url, json={'skills': skills})

print("Status Code:", response.status_code)
print("Recommended Projects:")
for p in response.json().get("projects", []):
    print("-", p["title"])