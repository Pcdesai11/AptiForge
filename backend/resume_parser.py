import re

TECH_KEYWORDS={"python", "java", "c++", "html", "css", "javascript", "react", "node.js",
    "flask", "django", "sql", "mysql", "mongodb", "aws", "azure", "docker",
    "kubernetes", "git", "github", "tensorflow", "pytorch", "pandas", "numpy",
    "ci/cd", "rest", "api", "graphql", "machine learning", "deep learning"}

def clean_text(text):

    text = re.sub(r'\W+', ' ', text)
    return text.strip().lower()

def extract_skills(text):
    text=clean_text(text)
    found=set()

    for keyword in TECH_KEYWORDS:
        if keyword in text:
            found.add(keyword)

    return sorted(found)