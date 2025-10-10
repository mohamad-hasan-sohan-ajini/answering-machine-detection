import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

file_path = Path(__file__).resolve()
parent_dir = file_path.parent

DB_PATH = os.environ.get("KEYWORDS_DB", f"sqlite:///{str(parent_dir)}/keywords.db")

engine = create_engine(DB_PATH)
db_session = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
)
Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    import models

    Base.metadata.create_all(bind=engine)
