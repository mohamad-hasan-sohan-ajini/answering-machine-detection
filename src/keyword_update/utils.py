from datetime import datetime

from sqlalchemy import update

from database import db_session, init_db
from models import Keyword, Status

init_db()


def get_confirmed_words():
    confirmed_keywords = [
        k.word
        for k in db_session.query(Keyword)
        .join(Status)
        .filter(Status.status == "confirmed")
        .all()
    ]
    return sorted(confirmed_keywords)


def get_pending_words():
    pending_keywords = [
        k.word
        for k in db_session.query(Keyword)
        .join(Status)
        .filter(Status.status == "pending")
        .all()
    ]
    return sorted(pending_keywords)


def impose_form(form):
    # print(form)
    confirmed_at_db = set(get_confirmed_words())
    pending_at_db = set(get_pending_words())
    confirmed_at_form = set([k for (k, v) in form.items() if v == "confirmed"])
    pending_at_form = set([k for (k, v) in form.items() if v == "pending"])
    # print(confirmed_at_form)
    # print(pending_at_form)
    all_words = confirmed_at_db.union(pending_at_db)
    print("all words", all_words)
    # update
    date = datetime.now().date()
    for word in all_words:
        # confirmed => pending
        if word in confirmed_at_db and word not in confirmed_at_form:
            print("updating", word, "to pending")
            db_session.execute(
                update(Keyword)
                .where(Keyword.word == word)
                .values(status_id=2, date=date)
            )
        # pending => confirmed
        elif word in pending_at_db and word in pending_at_form:
            print("updating", word, "to confirmed")
            db_session.execute(
                update(Keyword)
                .where(Keyword.word == word)
                .values(status_id=1, date=date)
            )
    db_session.commit()
