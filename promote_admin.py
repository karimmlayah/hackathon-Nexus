from database import SessionLocal
from models import User
import sys

def promote_to_admin(email):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User with email {email} not found.")
            return

        user.role = "admin"
        db.commit()
        db.refresh(user)
        print(f"User {user.email} promoted to ADMIN successfully.")
        print(f"Current Role: {user.role}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python promote_admin.py <email>")
        sys.exit(1)
    
    email = sys.argv[1]
    promote_to_admin(email)
