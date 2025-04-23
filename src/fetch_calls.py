# coding: utf-8
import json
from datetime import datetime, timedelta

from minio import Minio
from sqlalchemy import func

from config import ObjectStorage
from database import db_session
from models import AMDRecord


def get_calls_from_past_week(db_session):
    # Calculate date range
    today = datetime.now().date()
    one_week_ago = today - timedelta(days=7)

    # Query database for records within this date range
    past_week_calls = (
        db_session.query(AMDRecord)
        .filter(AMDRecord.call_date >= one_week_ago)
        .filter(AMDRecord.call_date <= today)
        .filter(func.length(AMDRecord.dialed_number) > 6)
        .all()
    )

    return past_week_calls


calls = get_calls_from_past_week(db_session)

client = Minio(
    ObjectStorage.minio_url,
    access_key=ObjectStorage.minio_access_key,
    secret_key=ObjectStorage.minio_secret_key,
    secure=False,
)

for call in calls:
    call_id = call.call_id
    # fetch metadata
    metadate = client.get_object(
        ObjectStorage.minio_metadata_bucket_name, call_id + ".json"
    )
    with open(f"objects/{call_id}.json", "w") as f:
        json.dump(json.loads(metadate.read()), f, indent=4)
    # fetch wav file
    wav = client.get_object(ObjectStorage.minio_wav_bucket_name, call_id + ".wav")
    with open(f"objects/{call_id}.wav", "wb") as f:
        f.write(wav.read())
