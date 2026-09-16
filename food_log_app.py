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

def use_calculated_food(result, amount, unit):
    st.session_state["calculated_food"] = result["food"]
    st.session_state["manual_nutrition"] = False
    st.session_state["food"] = result["food"]
    st.session_state["amount"] = amount
    st.session_state["unit"] = unit
    st.session_state["calories"] = result["calories"]
    st.session_state["protein"] = result["protein_g"]

df = load_food_log()

st.title("Kirby's Food Log")

st.subheader("Quick Food Entry")

with st.form("quick_food_form"):

    quick_entry = st.text_input(
        "Enter food",
        placeholder="Example: 6 oz chikn breast"
    )

    calculate_submitted = st.form_submit_button("Calculate Food")

if calculate_submitted:

    parsed = parse_food_input(quick_entry)

    if parsed:
        parsed_amount, parsed_unit, food_name = parsed

        result = calculate_food(
            food_name,
            parsed_amount,
            parsed_unit
        )

        if result:

            confidence = result["confidence"]

            if confidence >= 90:

                use_calculated_food(result, parsed_amount, parsed_unit)

                st.session_state.pop("suggested_food", None)

                st.rerun()

            elif confidence >= 70:

                st.session_state["suggested_food"] = {
                    "result": result,
                    "amount": parsed_amount,
                    "unit": parsed_unit
                }

            else:

                st.session_state.pop("suggested_food", None)

                st.warning(
                    f"No confident match found. "
                    f"Closest match was {result['food']} "
                    f"({confidence:.0f}% confidence)."
                )

        else:
            st.error("I recognized the food, but couldn't understand the unit.")

    else:
        st.error("I couldn't understand that entry.")

if "suggested_food" in st.session_state:

    suggestion = st.session_state["suggested_food"]
    result = suggestion["result"]

    st.info(
        f"Did you mean {result['food']}? "
        f"({result['confidence']:.0f}% confidence)"
    )

    if st.button("Use Suggested Match"):

        use_calculated_food(result, suggestion["amount"], suggestion["unit"])

        del st.session_state["suggested_food"]

        st.rerun()

st.session_state.setdefault("manual_nutrition", True)
manual_nutrition = st.checkbox(
    "Enter nutrition manually",
    key="manual_nutrition",
    disabled="calculated_food" not in st.session_state,
)

if not manual_nutrition:
    # Keep the confirmed identity attached to its nutrition data.
    st.session_state["food"] = st.session_state["calculated_food"]
    st.caption("Nutrition updates with your portion. Use Quick Food Entry to change foods.")

food = st.text_input("Food", key="food", disabled=not manual_nutrition)

st.session_state.setdefault("amount", 1.0)
amount = st.number_input(
    "Amount",
    min_value=0.0,
    step=1.0,
    key="amount"
)

unit = st.text_input(
    "Unit",
    placeholder="g, cup, serving, etc.",
    key="unit"
)

can_save = True
if not manual_nutrition:
    result = calculate_food(food, amount, unit)
    if result is None:
        can_save = False
        st.session_state["calories"] = 0.0
        st.session_state["protein"] = 0.0
        st.error("That unit isn't supported for this food. Choose a supported unit, such as g or oz.")
    else:
        st.session_state["calories"] = result["calories"]
        st.session_state["protein"] = result["protein_g"]

calories = st.number_input(
    "Calories",
    min_value=0.0,
    step=10.0,
    key="calories",
    disabled=not manual_nutrition,
)

protein = st.number_input(
    "Protein (g)",
    min_value=0.0,
    step=1.0,
    key="protein",
    disabled=not manual_nutrition,
)

submitted = st.button("Add Food", disabled=not can_save)

if submitted and can_save:

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
