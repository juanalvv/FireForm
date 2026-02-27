from sqlmodel import SQLModel
from api.db.database import engine
from api.db import models

def init_db():
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    init_db()