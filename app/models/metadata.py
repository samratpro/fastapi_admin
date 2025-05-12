from sqlalchemy import Column, String, Integer
from app.db.base_class import Base

class Metadata(Base):
    __tablename__ = "metadata"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)