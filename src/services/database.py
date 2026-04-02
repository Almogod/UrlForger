from sqlalchemy import create_engine, Column, String, Text, DateTime, Float, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from src.config import config

Base = declarative_base()

class DBTask(Base):
    __tablename__ = "tasks"
    
    task_id = Column(String, primary_key=True, index=True)
    domain = Column(String, index=True)
    status = Column(String, default="pending")
    state = Column(String, default="running")
    error = Column(Text, nullable=True)
    results_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DBAuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = Column(String, index=True)
    action = Column(String)
    resource = Column(String)
    details = Column(Text)

# Engine setup
engine = create_engine(
    config.DATABASE_URL, connect_args={"check_same_thread": False} # Needed for SQLite
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
