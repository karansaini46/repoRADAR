from autoscan.shared.db.database import engine
from autoscan.shared.db.models import Base

Base.metadata.create_all(bind=engine)
print("Database initialized")
