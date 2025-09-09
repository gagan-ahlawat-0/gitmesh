from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from .base import Base

class SearchCache(Base):
    __tablename__ = 'search_cache'

    id = Column(Integer, primary_key=True)
    query = Column(String, index=True, unique=True, nullable=False)
    results = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
