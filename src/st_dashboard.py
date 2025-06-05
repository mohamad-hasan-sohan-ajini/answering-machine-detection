import json
from datetime import date, timedelta

import matplotlib.pyplot as plt
import numpy as np
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
# st.data_editor(df)
total_calls = len(metadata_list)

st.success(
    f"Selected range: **{from_date} → {to_date}**\n\nFetched {total_calls} records from {ObjectStorage.minio_metadata_bucket_name}."
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
ax.pie(
    result_counts,
    labels=result_counts.index,
    autopct="%1.1f%%",
    startangle=90,
    colors=["#DEFACE", "#FACADE"],
)
ax.axis("equal")
st.pyplot(fig)

# call duration
st.write("### Call Duration Histogram")
fig_hist, ax_hist = plt.subplots(figsize=(12, 8))
duration = [min(i, Algorithm.max_call_duration) for i in df["duration"]]
ax_hist.hist(
    duration,
    bins=range(0, int(Algorithm.max_call_duration)),
    color="#BEEFED",
    edgecolor="black",
)
ax_hist.set_title("Call Duration Histogram")
ax_hist.set_xlabel("Duration (seconds)")
ax_hist.set_ylabel("Frequency")
st.pyplot(fig_hist)

# number of segments in each call
st.write("### Segments/Call Histogram")
fig_hist, ax_hist = plt.subplots(figsize=(12, 8))
number_of_segments = [len(i) for i in df["sad_result"]]
ax_hist.hist(
    number_of_segments,
    bins=np.arange(-0.5, max(number_of_segments) + 1.5),
    color="#BADDAD",
    edgecolor="black",
)
ax_hist.set_title("Number of Segments Histogram")
ax_hist.set_xlabel("Number of Segments")
ax_hist.set_ylabel("Frequency")
st.pyplot(fig_hist)

# AMD reason: ASR vs KWS
st.write("### AMD Reason")
fig_hist, ax_hist = plt.subplots(figsize=(10, 6))
detected_by_kws = sum([1 for i in df["kws_result"] if i])
detected_by_asr = total_calls - detected_by_kws
fig, ax = plt.subplots(figsize=(6, 6))
ax.pie(
    [detected_by_asr, detected_by_kws],
    labels=["ASR", "KWS"],
    autopct="%1.1f%%",
    startangle=90,
    colors=["#ABACAB", "#DEAFED"],
)
ax.axis("equal")
st.pyplot(fig)

# early detection
st.write("### Early detection")
early_percent = (
    sum([1 for i in df["reason"] if pd.notna(i) and "early" in i]) * 100 / total_calls
)
regular_percent = 100 - early_percent
bar_height = 0.1
fig, ax = plt.subplots(figsize=(6, 1))
ax.barh(
    0,
    early_percent,
    color="#F1B7B4",
    edgecolor="none",
    label="early",
    height=bar_height,
)
ax.barh(
    0,
    regular_percent,
    left=early_percent,
    color="#BAD00D",
    edgecolor="none",
    label="regular",
    height=bar_height,
)
ax.text(
    early_percent / 2,
    0,
    f"early\n{early_percent:.1f} %",
    ha="center",
    va="center",
)
ax.text(
    early_percent + regular_percent / 2,
    0,
    f"regular\n{regular_percent:.1f} %",
    ha="center",
    va="center",
)
ax.set_xlim(0, 100)
ax.set_xticks([])
ax.set_yticks([])
st.pyplot(fig)
