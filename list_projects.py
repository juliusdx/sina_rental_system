from app import create_app
from models import Project

app = create_app()

with app.app_context():
    projects = Project.query.all()
    print("Projects found:")
    for p in projects:
        print(f"- {p.name}")
