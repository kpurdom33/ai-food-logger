import pandas as pd
import re
from rapidfuzz import process, fuzz


foods = pd.read_csv("foods_master.csv")
food_units = pd.read_csv("food_units.csv")

search_choices = {}

for _, row in foods.iterrows():

    canonical_name = row["food_name"]

    search_choices[canonical_name] = canonical_name

    aliases = str(row["aliases"]).split("|")

    for alias in aliases:
        search_choices[alias.strip()] = canonical_name

def convert_to_grams(food_name, amount, unit):
    unit = unit.lower().strip()

    if unit in ["g", "gram", "grams"]:
        return amount

    if unit in ["oz", "ounce", "ounces"]:
        return amount * 28.3495

    if unit in ["lb", "lbs", "pound", "pounds"]:
        return amount * 453.592

    matching_units = food_units[
        food_units["food_name"] == food_name
    ]

    for _, row in matching_units.iterrows():
        aliases = str(row["unit_aliases"]).split("|")

        if unit == row["unit_name"] or unit in aliases:
            return amount * row["grams_per_unit"]

    return None

def calculate_food(search_term, amount, unit):

    match = process.extractOne(
        search_term,
        search_choices.keys(),
        scorer=fuzz.WRatio
    )

    matched_text = match[0]
    confidence = match[1]
    canonical_food = search_choices[matched_text]

    matched_row = foods[
        foods["food_name"] == canonical_food
    ].iloc[0]

    grams_eaten = convert_to_grams(
        canonical_food,
        amount,
        unit
    )

    if grams_eaten is None:
        return None

    if matched_row["basis_unit"] == "g":
        basis_grams = matched_row["basis_amount"]

    else:
        basis_unit_row = food_units[
            (food_units["food_name"] == canonical_food)
            & (food_units["unit_name"] == matched_row["basis_unit"])
        ].iloc[0]

        basis_grams = (
            matched_row["basis_amount"]
            * basis_unit_row["grams_per_unit"]
        )

    multiplier = grams_eaten / basis_grams

    calories = round(
        float(matched_row["calories"] * multiplier),
        1
    )

    protein = round(
        float(matched_row["protein_g"] * multiplier),
        1
    )

    grams_eaten = round(
        float(grams_eaten),
        1
    )

    return {
        "food": canonical_food,
        "confidence": confidence,
        "grams": grams_eaten,
        "calories": calories,
        "protein_g": protein
    }

def parse_food_input(user_input):

    pattern = r"^\s*(\d*\.?\d+)\s*([a-zA-Z]+)\s+(.+)$"

    match = re.match(pattern, user_input)

    if not match:
        return None

    amount = float(match.group(1))
    unit = match.group(2)
    food_name = match.group(3)

    return amount, unit, food_name

