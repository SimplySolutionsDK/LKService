"""
Short-lived pending session used to bridge the OAuth callback and the
select-company redirect.  When the Danløn demo (or a firewall) prevents
the automatic redirect back to /danlon/success, the frontend can read
the select-company URL and/or let the user complete the token exchange
manually.
"""
from sqlalchemy import Column, String, DateTime, Integer, Text
from datetime import datetime
from app.database import Base


class DanlonPendingSession(Base):
    __tablename__ = "danlon_pending_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)

    # The URL we built for step 6 – frontend can open this if redirect failed
    select_company_url = Column(Text, nullable=False)

    # Temp tokens from step 4 (not yet company-scoped)
    temp_access_token = Column(Text, nullable=False)
    temp_refresh_token = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # Default TTL: 15 minutes
    expires_at = Column(DateTime, nullable=False)
