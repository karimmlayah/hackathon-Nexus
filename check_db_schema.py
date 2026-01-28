from sqlalchemy import create_engine, inspect
DATABASE_URL = "sqlite:///./finfit_users.db"
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)
columns = inspector.get_columns('users')
print("Columns in 'users' table:")
for col in columns:
    print(f"- {col['name']} ({col['type']})")
