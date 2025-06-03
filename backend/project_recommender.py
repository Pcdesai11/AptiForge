import json


def load_projects(path="data/project_ideas.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def recommend_projects(user_skills, top_k=3):
    projects = load_projects()
    scored_projects = []

    for project in projects:
        
        match_score = len(set(project["tags"]).intersection(set(user_skills)))
        if match_score > 0:
            scored_projects.append((match_score, project))

    
    scored_projects.sort(reverse=True, key=lambda x: x[0])
    
   
    return [proj for _, proj in scored_projects[:top_k]]
