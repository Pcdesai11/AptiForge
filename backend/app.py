import traceback
from flask import Flask, request, jsonify
from project_recommender import recommend_projects
from resume_parser import extract_skills

app = Flask(__name__)

# ✅ Optional: Add a simple GET homepage route
@app.route('/', methods=['GET'])
def home():
    return "Welcome to AptiForge API"

# ✅ The main analyze route
@app.route('/analyze_resume', methods=['POST'])
def analyze_resume():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    resume_text = file.read().decode("utf-8")

    try:
        print("📄 Resume Loaded:")
        print(resume_text[:200])  # print first 200 chars for debug

        skills = extract_skills(resume_text)
        print("✅ Skills Extracted:", skills)

        projects = recommend_projects(skills)
        print("✅ Projects Recommended:", [p["title"] for p in projects])

        return jsonify({
            'skills': skills,
            'recommended_projects': projects
        })
    except Exception as e:
        print("❌ Exception occurred:")
        traceback.print_exc()  # <- This shows full error trace
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file = request.files['file']  
    resume_text = file.read().decode('utf-8')
    skills = extract_skills(resume_text)

    return jsonify({"skills": skills})

if __name__ == '__main__':
    app.run(debug=True)
