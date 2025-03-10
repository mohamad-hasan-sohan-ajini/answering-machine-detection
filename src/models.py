from sqlalchemy import Column, Date, Float, Integer, String, Time

from database import Base


class CallRecord(Base):
    __tablename__ = "AMDRecords"
    row_number = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(String(40))
    call_date = Column(Date)
    call_time = Column(Time)
    result = Column(String(80))
    dialed_number = Column(String(20))
    call_duration = Column(Float)

    def __init__(
        self,
        call_id,
        call_date,
        call_time,
        result,
        dialed_number,
        call_duration,
    ):
        self.call_id = call_id
        self.call_date = call_date
        self.call_time = call_time
        self.result = result
        self.dialed_number = dialed_number
        self.call_duration = call_duration
