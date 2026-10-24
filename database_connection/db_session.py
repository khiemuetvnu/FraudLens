"""
FraudLens - Database Connection & Session Management
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DEFAULT_PG_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+psycopg://postgres:ronaldo123@localhost:5432/postgres"
)

engine = create_engine(
    DEFAULT_PG_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency helper để mở và đóng session DB trong FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
