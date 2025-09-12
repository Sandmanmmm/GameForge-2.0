"""
User management system for GameForge API
Handles user registration, authentication, and role management
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel, EmailStr
import secrets
import hashlib

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: secrets.token_urlsafe(16))
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    roles = Column(Text, default="user")  # JSON string
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: secrets.token_urlsafe(16))
    user_id = Column(String, nullable=False)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    scopes = Column(Text, default="[]")  # JSON string
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    expires_at = Column(DateTime)

class UserManager:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def create_user(self, username: str, email: str, password: str, roles: List[str] = None) -> str:
        """Create a new user"""
        if roles is None:
            roles = ["user"]

        db = self.SessionLocal()
        try:
            # Check if user exists
            existing = db.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()

            if existing:
                raise ValueError("User already exists")

            # Create new user
            from auth_middleware import get_password_hash
            user = User(
                username=username,
                email=email,
                password_hash=get_password_hash(password),
                roles=json.dumps(roles)
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            return user.id

        finally:
            db.close()

    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user login"""
        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()

            if not user or not user.is_active:
                return None

            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.utcnow():
                return None

            # Verify password
            from auth_middleware import verify_password
            if not verify_password(password, user.password_hash):
                # Increment login attempts
                user.login_attempts += 1
                if user.login_attempts >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=15)
                db.commit()
                return None

            # Reset login attempts on successful login
            user.login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.utcnow()
            db.commit()

            return {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "roles": json.loads(user.roles),
                "is_verified": user.is_verified
            }

        finally:
            db.close()

    def create_api_key(self, user_id: str, name: str, scopes: List[str], expires_days: int = 365) -> str:
        """Create API key for user"""
        db = self.SessionLocal()
        try:
            # Generate API key
            api_key = f"gf_{secrets.token_urlsafe(32)}"
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()

            # Create API key record
            api_key_record = APIKey(
                user_id=user_id,
                name=name,
                key_hash=key_hash,
                scopes=json.dumps(scopes),
                expires_at=datetime.utcnow() + timedelta(days=expires_days)
            )

            db.add(api_key_record)
            db.commit()

            return api_key

        finally:
            db.close()

# Usage example
user_manager = UserManager("sqlite:///gameforge_users.db")
