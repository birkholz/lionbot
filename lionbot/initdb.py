import os

from sqlalchemy import create_engine

from lionbot.data import Base

database_uri = os.getenv("DATABASE_URL")  # or other relevant config var
if database_uri and database_uri.startswith("postgres://"):
    database_uri = database_uri.replace("postgres://", "postgresql://", 1)
engine = create_engine(database_uri)
Base.metadata.create_all(engine)
