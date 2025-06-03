import requests

url = "http://127.0.0.1:5000/upload_resume"
file_path = r"C:\Users\priya\OneDrive - Seattle University\Desktop\AptiForge\AptiForge\resume_sample.txt"

with open(file_path, "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)

print("Status Code:", response.status_code)
print("Response JSON:", response.json())
