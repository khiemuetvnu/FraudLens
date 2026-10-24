import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Base class for SQLAlchemy ORM models
Base = declarative_base()

DEFAULT_PG_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:ronaldo123@localhost:5432/postgres"
)

# In production, READONLY points to replica via PgBouncer. In local dev, falls back to Primary.
DEFAULT_PG_READONLY_URL = os.getenv(
    "DATABASE_READONLY_URL",
    DEFAULT_PG_URL
)

# 1. Write Engine (Primary Master via PgBouncer)
write_engine = create_engine(
    DEFAULT_PG_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
WriteSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=write_engine)

# 2. ReadOnly Engine (ReadOnly Replica via PgBouncer)
read_engine = create_engine(
    DEFAULT_PG_READONLY_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
ReadOnlySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=read_engine)
