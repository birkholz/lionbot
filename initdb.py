import os

from sqlalchemy import create_engine

from data import Base

engine = create_engine(os.environ.get('DATABASE_URL'))
Base.metadata.create_all(engine)
