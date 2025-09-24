from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

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
