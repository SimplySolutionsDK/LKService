"""
Stores the mapping from FTZ employee names to Danløn employee IDs.

Two kinds of rows:
  is_fallback=False  – explicit per-employee mapping (ftz_employee_name → danlon employee)
  is_fallback=True   – fallback row; used for any FTZ employee with no explicit mapping.
                       Only one fallback row per user/company is expected.
"""
from sqlalchemy import Column, String, DateTime, Integer, Boolean
from datetime import datetime
from app.database import Base


class DanlonEmployeeMapping(Base):
    __tablename__ = "danlon_employee_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    company_id = Column(String(255), nullable=False, index=True)

    # FTZ employee name as it appears in processed data (NULL for the fallback row)
    ftz_employee_name = Column(String(255), nullable=True)

    # Danløn employee identifiers
    danlon_employee_id = Column(String(255), nullable=False)
    danlon_employee_name = Column(String(255), nullable=False, default="")

    # True for the single fallback row (catch-all for unmatched workers)
    is_fallback = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
