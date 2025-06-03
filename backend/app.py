from flask import Flask,request,jsonify
from resume_parser import extract_skills

app = Flask(__name__)
@app.route('/')
def home():
    return "Welcome to AptiForge API"

@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file =request.files['file']  
    resume_text=file.read().decode('utf-8')
    skills=extract_skills(resume_text)

    return jsonify({"skills": skills})

if __name__ == '__main__':
    app.run(debug=True)
