import json
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from minio import Minio
from sqlalchemy import func

from config import ObjectStorage
from database import db_session
from models import AMDRecord


################
# select data #
################
st.title("📅 Select a date range")

today = date.today()
default_to = today
default_fr = today - timedelta(days=7)

st.subheader("Choose the interval")
col1, col2 = st.columns(2)
with col1:
    from_date = st.date_input(
        "From",
        value=default_fr,
        max_value=today,
        key="from",
    )

with col2:
    to_date = st.date_input(
        "To",
        value=default_to,
        min_value=from_date,
        max_value=today,
        key="to",
    )

if from_date > to_date:
    st.error("⛔ **'From'** must be on/before **'To'**.")
else:
    st.success(f"Selected range: **{from_date} → {to_date}**")


#########################
# fetch data from DB/OS #
#########################
calls = (
    db_session.query(AMDRecord)
    .filter(AMDRecord.call_date >= from_date)
    .filter(AMDRecord.call_date <= to_date)
    # .filter(func.length(AMDRecord.dialed_number) > 6)
    .all()
)

client = Minio(
    ObjectStorage.minio_url,
    access_key=ObjectStorage.minio_access_key,
    secret_key=ObjectStorage.minio_secret_key,
    secure=False,
)

metadata_list = []
for call in calls:
    call_id = call.call_id
    # fetch metadata
    metadata = client.get_object(
        ObjectStorage.minio_metadata_bucket_name,
        call_id + ".json",
    )
    metadata = json.loads(metadata.read())
    metadata_list.append(metadata)

st.write(
    f"Fetched {len(metadata_list)} records from {ObjectStorage.minio_metadata_bucket_name}."
)
# Display the DataFrame in the Streamlit app
df = pd.DataFrame(metadata_list)
st.dataframe(df)
