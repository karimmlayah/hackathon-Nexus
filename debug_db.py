from database import init_db, SessionLocal
from models import User
import os

# Ensure DB is fresh
if os.path.exists("finfit.db"):
    # We won't delete it here, just try to use it.
    # If it fails, we know it's schema mismatch.
    pass
else:
    print("DB file not found, creating...")
    init_db()

db = SessionLocal()

try:
    print("Attempting to create user...")
    user = User(
        name="Debug User",
        email="debug@example.com",
        phone="55555555",
        role="user"
    )
    user.set_password("pass")
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"User created: {user.id}, Role: {user.role}")
    if user.role == "user":
        print("SUCCESS")
    else:
        print("Role mismatch")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"FAILED: {e}")
finally:
    db.close()
