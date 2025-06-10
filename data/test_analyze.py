import requests

url = "http://127.0.0.1:5000/analyze_resume"
file_path = r"C:\Users\priya\OneDrive - Seattle University\Desktop\AptiForge\AptiForge\resume_sample.txt"

with open(file_path, "rb") as f:
    response = requests.post(url, files={"file": f})

print("Status Code:", response.status_code)
print("Raw Response Text:") 
print(response.text)
data = response.json()

print("\nExtracted Skills:")
print(data["skills"])

print("\nRecommended Projects:")
for proj in data["recommended_projects"]:
    print("-", proj["title"])
