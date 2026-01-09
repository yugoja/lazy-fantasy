from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Configure engine based on database type
# SQLite needs check_same_thread=False, PostgreSQL doesn't
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL or other databases
    engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
