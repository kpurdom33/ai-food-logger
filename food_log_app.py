import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_FILE = Path("food_log.csv")

COLUMNS = [
    "timestamp",
    "date",
    "food",
    "amount",
    "unit",
    "calories",
    "protein_g"
]

def load_food_log():
    if DATA_FILE.exists():
        return pd.read_csv(DATA_FILE)

    return pd.DataFrame(columns=COLUMNS)

def save_food_log(df):
    df.to_csv(DATA_FILE, index=False)

df = load_food_log()

st.title("Kirby's Food Log")

with st.form("food_form"):

    food = st.text_input("Food")

    amount = st.number_input(
        "Amount",
        min_value=0.0,
        value=1.0,
        step=1.0
    )

    unit = st.text_input(
        "Unit",
        placeholder="g, cup, serving, etc."
    )

    calories = st.number_input(
        "Calories",
        min_value=0.0,
        step=10.0
    )

    protein = st.number_input(
        "Protein (g)",
        min_value=0.0,
        step=1.0
    )

    submitted = st.form_submit_button("Add Food")

if submitted:

    now = datetime.now()

    new_food = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "food": food,
        "amount": amount,
        "unit": unit,
        "calories": calories,
        "protein_g": protein
    }

    new_row = pd.DataFrame([new_food])

    df = pd.concat(
        [df, new_row],
        ignore_index=True
    )

    save_food_log(df)

    st.success(f"Added {food}")

    st.rerun()

today = datetime.now().strftime("%Y-%m-%d")

today_df = df[df["date"] == today]

st.subheader("Today's Totals")

col1, col2 = st.columns(2)

col1.metric(
    "Calories",
    round(today_df["calories"].sum())
)

col2.metric(
    "Protein",
    f"{today_df['protein_g'].sum():.1f} g"
)

st.subheader("Today's Food")

st.dataframe(
    today_df,
    use_container_width=True,
    hide_index=True
)

st.subheader("Full Food History")

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)
