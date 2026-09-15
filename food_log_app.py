import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from food_engine import parse_food_input, calculate_food

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

st.subheader("Quick Food Entry")

quick_entry = st.text_input(
    "Enter food",
    placeholder="Example: 6 oz chikn breast"
)

if st.button("Calculate Food"):

    parsed = parse_food_input(quick_entry)

    if parsed:
        parsed_amount, parsed_unit, food_name = parsed

        result = calculate_food(
            food_name,
            parsed_amount,
            parsed_unit
        )

        if result:

            st.session_state["food"] = result["food"]
            st.session_state["amount"] = parsed_amount
            st.session_state["unit"] = parsed_unit
            st.session_state["calories"] = result["calories"]
            st.session_state["protein"] = result["protein_g"]

            st.rerun()

        else:
            st.error("I recognized the food, but couldn't understand the unit.")

    else:
        st.error("I couldn't understand that entry.")

with st.form("food_form"):

    food = st.text_input("Food", key="food")

    amount = st.number_input(
    "Amount",
    min_value=0.0,
    value=1.0,
    step=1.0,
    key="amount"
)

    unit = st.text_input(
    "Unit",
    placeholder="g, cup, serving, etc.",
    key="unit"
)

    calories = st.number_input(
    "Calories",
    min_value=0.0,
    step=10.0,
    key="calories"
)

    protein = st.number_input(
    "Protein (g)",
    min_value=0.0,
    step=1.0,
    key="protein"
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
