from datetime import date, timedelta

import streamlit as st


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
