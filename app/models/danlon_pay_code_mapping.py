"""
Stores the mapping from time-registration categories to Danløn pay-part codes.

Three categories are tracked:
  normal   – regular working hours          (demo default: T1)
  overtime – all overtime categories        (demo default: T2)
  callout  – callout / udrykning payment    (demo default: T3)
"""
from sqlalchemy import Column, String, DateTime, Integer
from datetime import datetime
from app.database import Base


class DanlonPayCodeMapping(Base):
    __tablename__ = "danlon_pay_code_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    company_id = Column(String(255), nullable=False, index=True)

    # Pay-part codes chosen by the user (stored as the code string, e.g. "T1")
    normal_code = Column(String(50), nullable=False, default="T1")
    overtime_code = Column(String(50), nullable=False, default="T2")
    callout_code = Column(String(50), nullable=False, default="T3")

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
