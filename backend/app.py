from flask import Flask,request,jsonify
from project_recommender import recommend_projects
from resume_parser import extract_skills

app = Flask(__name__)
@app.route('/analyze_resume',methods=['POST'])
def home():
    return "Welcome to AptiForge API"

@app.route('/analyze_resume', methods=['POST'])
def analyze_resume():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    resume_text = file.read().decode("utf-8")
    
    # Step 1: Extract skills
    skills = extract_skills(resume_text)
    projects = recommend_projects(skills)

    return jsonify({
        'skills': skills,
        'recommended_projects': projects
    })

    
    

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
