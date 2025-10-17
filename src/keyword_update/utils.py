from datetime import datetime

from sqlalchemy import update

from database import db_session, init_db
from models import Keyword, Status

init_db()

# STATUS
CONFIRMED_STATUS = 1
PENDING_STATUS = 2
DELETED_STATUS = 3

MIN_KEYWORD_LENGTH = 5


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


def get_deleted_words():
    deleted_keywords = [
        k.word
        for k in db_session.query(Keyword)
        .join(Status)
        .filter(Status.status == "deleted")
        .all()
    ]
    return sorted(deleted_keywords)



def get_all_keywords():
    return sorted(get_confirmed_words() + get_pending_words())


def sync_keywords_with_form(form):
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
                .values(status_id=PENDING_STATUS, date=date)
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


def recycle_keywords_to_pending(form):
    deleted_at_form = set([k for (k, v) in form.items()])
    date = datetime.now().date()
    for word in deleted_at_form:
        word = word.strip().upper()
        existing_keyword = (
            db_session.query(Keyword).filter(Keyword.word == word).one_or_none()
        )
        # update
        print("recovering", word)
        db_session.execute(
            update(Keyword)
            .where(Keyword.word == word)
            .values(status_id=PENDING_STATUS, date=date)
        )

    db_session.commit()



def add_keywords(form, status="confirmed"):
    new_cnt = 0
    red_cnt = 0
    status_code = CONFIRMED_STATUS if status == "confirmed" else PENDING_STATUS
    for word in form.values():
        if len(word) <= MIN_KEYWORD_LENGTH:
            continue
        word = word.strip().upper()
        existing_keyword = (
            db_session.query(Keyword).filter(Keyword.word == word).one_or_none()
        )
        if existing_keyword is not None:
            print(f"Keyword '{word}' already exists, skipping.")
            red_cnt += 1
            continue
        new_keyword = Keyword(
            word=word,
            date=datetime.now().date(),
            status_id=status_code,
        )
        db_session.add(new_keyword)
        new_cnt += 1
    db_session.commit()
    return f"Added {new_cnt} , Skipped {red_cnt}"


def remove_from_db(form):
    date = datetime.now().date()
    for word in form.values():
        word = word.strip().upper()
        existing_keyword = (
            db_session.query(Keyword).filter(Keyword.word == word).one_or_none()
        )
        if existing_keyword is None:
            print(f"Keyword '{word}' does not exist, skipping.")
            continue
        # update
        print("deleting", word)
        db_session.execute(
            update(Keyword)
            .where(Keyword.word == word)
            .values(status_id=DELETED_STATUS, date=date)
        )

    db_session.commit()

