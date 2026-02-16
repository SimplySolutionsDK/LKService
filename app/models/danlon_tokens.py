"""
Database models for Danløn OAuth tokens.
"""
from sqlalchemy import Column, String, DateTime, Integer, Text
from datetime import datetime
from app.database import Base


class DanlonToken(Base):
    """
    Stores Danløn OAuth tokens for users.
    
    Tokens are stored per user and company combination.
    Access tokens expire after 5 minutes, refresh tokens are long-lived.
    """
    __tablename__ = "danlon_tokens"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # User and company identification
    user_id = Column(String(255), nullable=False, index=True)
    company_id = Column(String(255), nullable=False, index=True)
    
    # OAuth tokens
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    
    # Token metadata
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional: Store company name for display
    company_name = Column(String(500), nullable=True)
    
    def __repr__(self):
        return f"<DanlonToken(user_id='{self.user_id}', company_id='{self.company_id}')>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        return datetime.utcnow() >= self.expires_at
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "company_name": self.company_name,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_expired": self.is_expired
        }
