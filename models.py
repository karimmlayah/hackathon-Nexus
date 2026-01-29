"""Database models for FinFit application"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from passlib.context import CryptContext

Base = declarative_base()

# Password hashing using pbkdf2_sha256 (no external binary dependencies)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String(20), default="user", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password: str):
        """Hash and set password using Argon2"""
        self.hashed_password = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash using Argon2"""
        return pwd_context.verify(password, self.hashed_password)
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"
