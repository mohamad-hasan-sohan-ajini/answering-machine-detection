from sqlalchemy import Column, Date, Float, Integer, Text, Time

from config import Database
from database import Base


class AMDRecord(Base):
    __tablename__ = Database.table_name
    call_id = Column(Text, primary_key=True)
    dialed_number = Column(Text)
    call_date = Column(Date)
    call_time = Column(Time)
    result = Column(Text)
    call_duration = Column(Float)
    asr_result = Column(Text)

    def __init__(
        self,
        call_id,
        dialed_number,
        call_date,
        call_time,
        result,
        call_duration,
        asr_result,
    ):
        self.call_id = call_id
        self.dialed_number = dialed_number
        self.call_date = call_date
        self.call_time = call_time
        self.result = result
        self.call_duration = call_duration
        self.asr_result = asr_result
