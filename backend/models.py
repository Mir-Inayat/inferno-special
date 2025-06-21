from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    document_id = Column(String)
    file_path = Column(String)
    file_hash = Column(String)
    document_type = Column(String)  # Primary category
    sub_category = Column(String)
    processing_status = Column(String)  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    file_size = Column(Integer)  # in bytes
    file_format = Column(String)  # PDF, JPG, etc.
    page_count = Column(Integer)
    raw_content = Column(String)  # Processed text
    summary = Column(String)
    notes = Column(String)

class Person(Base):
    __tablename__ = 'persons'
    
    id = Column(Integer, primary_key=True)
    person_hash = Column(String)
    primary_name = Column(String)
    alternative_names = Column(String)
    date_of_birth = Column(DateTime)
    nationality = Column(String)
    gender = Column(String)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)