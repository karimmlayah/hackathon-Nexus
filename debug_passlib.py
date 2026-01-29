try:
    from passlib.context import CryptContext
    print("Passlib imported successfully")
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    hash = pwd_context.hash("test")
    print(f"Hash created: {hash}")
except Exception as e:
    print(f"Error: {e}")
