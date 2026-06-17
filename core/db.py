import os
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pathlib import Path

# Base model
Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(String(50), primary_key=True)
    status = Column(String(20), nullable=False)  # PENDING, RUNNING, COMPLETED, FAILED
    original_query = Column(Text, nullable=False)
    final_answer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    attempts = relationship(
        "Attempt", back_populates="job", cascade="all, delete-orphan"
    )


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(
        String(50), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False
    )
    attempt_number = Column(Integer, nullable=False)
    query_text = Column(Text, nullable=False)
    faithfulness_score = Column(Float, nullable=True)
    relevance_score = Column(Float, nullable=True)
    generated_answer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="attempts")


# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Local fallback to SQLite
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "rag_jobs.db"
    DATABASE_URL = f"sqlite:///{db_path}"

# SQLAlchemy Setup
# SQLite requires different arguments for connect_args (check_same_thread)
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
