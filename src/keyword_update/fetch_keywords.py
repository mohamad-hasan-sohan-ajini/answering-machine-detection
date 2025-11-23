# coding: utf-8
import json
import logging
import sys
from argparse import ArgumentParser
from datetime import datetime, timedelta
from pathlib import Path

import requests

file_path = Path(__file__).resolve()
parent_dir = file_path.parent.parent
sys.path.insert(0, str(parent_dir))

from config import KeywordAPIAccess, ObjectStorage
from minio import Minio

import llm_keyword_extraction
from database import db_session
from models import AMDRecord

logger = logging.getLogger(__name__)
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {KeywordAPIAccess.token}",
}


def get_calls_from_past_week(db_session):
    # Calculate date range
    today = datetime.now().date()
    one_week_ago = today - timedelta(days=7)

    # Query database for records within this date range
    past_week_calls = (
        db_session.query(AMDRecord)
        .filter(AMDRecord.call_date >= one_week_ago)
        .filter(AMDRecord.call_date <= today)
        # .filter(func.length(AMDRecord.dialed_number) > 6)
        .all()
    )

    return past_week_calls


def main(url):
    calls = get_calls_from_past_week(db_session)

    client = Minio(
        ObjectStorage.minio_url,
        access_key=ObjectStorage.minio_access_key,
        secret_key=ObjectStorage.minio_secret_key,
        secure=False,
    )

    transcripts = []
    for call in calls:
        call_id = call.call_id
        # fetch metadata
        try:
            metadata = client.get_object(
                ObjectStorage.minio_metadata_bucket_name,
                call_id + ".json",
            )
        except Exception as e:
            logger.error(f"Error {e}")
            continue
        metadata_ = json.loads(metadata.read())
        transcript = metadata_.get("asr_result", "").strip()
        if len(transcript) >= 5:
            transcripts.append(transcript)

    if not transcripts:
        logger.warning("No transcript found")
        return -1

    keywords = llm_keyword_extraction.extract(transcripts)

    for p in range(0, len(keywords), 32):
        data = {
            f"keywords{i}": key
            for i, key in enumerate(keywords[p : p + 32])
            if len(key) > 5
        }
        if not data:
            continue
        response = requests.post(
            url, headers=headers, data=json.dumps(data), verify=False
        )
        if response.status_code == 200:
            response = response.json()
            logger.info(response)
        else:
            logger.error(response.text)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--domain", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=str, default="8000")
    args = parser.parse_args()
    if args.port == "443":
        url = f"https://{args.domain}:{args.port}/api/add_pending_keywords"
    else:
        url = f"http://{args.domain}:{args.port}/api/add_pending_keywords"
    main(url)
    logger.warning("Exit normal")
