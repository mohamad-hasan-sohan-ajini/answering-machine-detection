from flask_login import UserMixin
from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

from database import Base


class Status(Base):
    __tablename__ = "status"

    id = Column(Integer, primary_key=True)
    status = Column(String(32), nullable=False)

    # relationship back to keywords
    keywords = relationship("Keyword", back_populates="status")

    def as_dict(self):
        return {"id": self.id, "status": self.status}


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True)
    word = Column(String(256), nullable=False)
    date = Column(Date, nullable=False)
    status_id = Column(Integer, ForeignKey("status.id"), nullable=False)

    # relationship object
    status = relationship("Status", back_populates="keywords")

    def as_dict(self):
        return {
            "id": self.id,
            "word": self.word,
            "date": self.date.isoformat(),
            "status_id": self.status_id,
        }


class User(Base, UserMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # -------- Password Utilities --------
    def set_password(self, password):
        """Hashes the plain-text password and stores it."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifies a given password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    # -------- Optional Helper Methods --------
    def __repr__(self):
        return f"<User(user_name={self.user_name})>"

    def as_dict(self):
        return {
            "id": self.id,
            "user_name": self.user_name,
            "password_hash": self.password_hash,
        }
