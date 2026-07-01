import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

db_url = os.environ.get("DATABASE_URL", "sqlite:///autoscan.db")
if db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
