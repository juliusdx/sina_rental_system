from app import app, db
from models import MyInvoisConfig

def update_tin():
    with app.app_context():
        config = MyInvoisConfig.query.first()
        if config:
            print(f"Old TIN: {config.issuer_tin}")
            config.issuer_tin = "C7850149000" # From Token Claims
            db.session.commit()
            print(f"New TIN: {config.issuer_tin}")
            print("Updated successfully.")
        else:
            print("Config not found.")

if __name__ == "__main__":
    update_tin()
