import json
from datetime import date, timedelta

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from minio import Minio
from sqlalchemy import func

from config import Algorithm, ObjectStorage
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
df = pd.DataFrame(metadata_list)
st.data_editor(df)
st.write(
    f"Fetched {len(metadata_list)} records from {ObjectStorage.minio_metadata_bucket_name}."
)

# AMD vs non-AMD
st.write("### Call Count: AMD VS non-AMD")
result_counts = df["result"].value_counts()
st.dataframe(
    result_counts.to_frame()
    .reset_index()
    .rename(columns={"index": "Result", "result": "Count"})
)
fig, ax = plt.subplots(figsize=(6, 6))
ax.pie(result_counts, labels=result_counts.index, autopct="%1.1f%%", startangle=90)
ax.axis("equal")
st.pyplot(fig)

# call duration
BINS = 5
st.write("### Call Duration Histogram")
fig_hist, ax_hist = plt.subplots(figsize=(10, 6))
duration = [min(i, Algorithm.max_call_duration) for i in df["duration"]]
ax_hist.hist(duration, bins=BINS, color="red", edgecolor="black")
ax_hist.set_title("Call Duration Histogram")
ax_hist.set_xlabel("Duration (seconds)")
ax_hist.set_ylabel("Frequency")
st.pyplot(fig_hist)

# number of segments in each call
BINS = 5
st.write("### Segments/Call Histogram")
fig_hist, ax_hist = plt.subplots(figsize=(10, 6))
number_of_segments = [len(i) for i in df["sad_result"]]
ax_hist.hist(number_of_segments, bins=BINS, color="skyblue", edgecolor="black")
ax_hist.set_title("Number of Segments Histogram")
ax_hist.set_xlabel("Number of Segments")
ax_hist.set_ylabel("Frequency")
st.pyplot(fig_hist)
