from datetime import datetime

from database import db_session, init_db
from models import Keyword, Status

init_db()

# populate Status table
status_confirmed = Status(id=1, status="confirmed")
db_session.add(status_confirmed)
db_session.commit()
status_pending = Status(id=2, status="pending")
db_session.add(status_pending)
db_session.commit()
status_pending = Status(id=3, status="deleted")
db_session.add(status_pending)
db_session.commit()

# pupulate Keywords table
keywords = [
    "LEAVE YOUR NAME",
    "LEAVE A NAME",
    "LEAVE ME",
    "LEAVE US",
    "NUMBER",
    "RETURN YOUR CALL",
    "AS SOON AS POSSIBLE",
    "GET BACK TO YOU",
    "AT THE TONE",
    "A MESSAGE",
    "YOUR MESSAGE",
    "CALL YOU",
    "RIGHT NOW",
    "UNFORTUNATELY",
    "REACHED",
    "A GREAT DAY",
    "A WONDERFUL DAY",
    "VE REACHED",
    "OFFICE HOURS",
    "FROM MONDAY",
    "MONDAY TO",
    "MONDAY THROUGH",
    "BUSINESS HOURS",
    "TAKE YOUR CALL",
    "CALL BACK",
    "ANSWER YOUR",
    "UNABLE",
    "IF YOU KNOW",
    "TO CONTINUE",
    "VE DIALED",
    "PRESS ONE",
    "PRESS TWO",
    "PRESS THREE",
    "PRESS FOUR",
    "PRESS FIVE",
    "PRESS SIX",
    "PRESS SEVEN",
    "PRESS EIGHT",
    "PRESS NINE",
    "PRESS ZERO",
    "PRESS POUND",
    "PRESS STAR",
    "RECORDED",
    "AFTER THE BEEP",
    "UNAVAILABLE",
    "IS CLOSED",
    "ARE CLOSED",
    "NOW CLOSED",
    "AN EMAIL",
    "ANSWERING MACHINE",
    "NOT IN SERVICE",
    "IS LOCATED",
    "ELEVEN AM TO",
    "TEN AM TO",
    "NINE AM TO",
    "EIGHT AM TO",
    "SEVEN AM TO",
    "SEVEN THIRTY AM TO",
    "TO FIVE PM",
    "TO SIX PM",
    "TO SEVEN PM",
    "TO EIGHT PM",
    "TO NINE PM",
    'VOICEMAIL',
    'AUTOMATED',
    'PROMPT',
    'IVR',
    'MAILBOX',
    'RECORD',
    'ANSWERING SERVICE',
    'WELCOME MESSAGE'
]
for word in keywords:
    k = Keyword(word=word, date=datetime.now().date(), status_id=1)
    db_session.add(k)
db_session.commit()
