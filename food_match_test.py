import pandas as pd
from rapidfuzz import process, fuzz

foods = pd.read_csv("foods_master.csv")
food_units = pd.read_csv("food_units.csv")

search_term = "fair life ff"

search_choices = {}

for _, row in foods.iterrows():

    canonical_name = row["food_name"]

    # Add the official food name
    search_choices[canonical_name] = canonical_name

    # Add all aliases
    aliases = str(row["aliases"]).split("|")

    for alias in aliases:
        search_choices[alias.strip()] = canonical_name


match = process.extractOne(
    search_term,
    search_choices.keys(),
    scorer=fuzz.WRatio
)

matched_text = match[0]
confidence = match[1]

canonical_food = search_choices[matched_text]

print("You typed:", search_term)
print("Matched:", canonical_food)
print("Matched using:", matched_text)
print("Confidence:", confidence)

matched_row = foods[
    foods["food_name"] == canonical_food
].iloc[0]

print("\nFULL MATCH:")
print(matched_row)

amount_eaten = 1.5

multiplier = amount_eaten / matched_row["basis_amount"]

calories = matched_row["calories"] * multiplier
protein = matched_row["protein_g"] * multiplier

print("\nCALCULATED NUTRITION:")
print("Amount:", amount_eaten, matched_row["basis_unit"])
print("Calories:", calories)
print("Protein:", protein)
print("\nUNIT DATA:")
print(food_units)

amount_in_grams = 360

basis_unit = matched_row["basis_unit"]

unit_row = food_units[
    (food_units["food_name"] == canonical_food)
    & (food_units["unit_name"] == basis_unit)
].iloc[0]

basis_grams = matched_row["basis_amount"] * unit_row["grams_per_unit"]

calories_per_gram = matched_row["calories"] / basis_grams
protein_per_gram = matched_row["protein_g"] / basis_grams

calories_from_grams = amount_in_grams * calories_per_gram
protein_from_grams = amount_in_grams * protein_per_gram

print("\nCALCULATED FROM GRAMS:")
print("Amount:", amount_in_grams, "g")
print("Calories:", calories_from_grams)
print("Protein:", protein_from_grams)

def convert_to_grams(food_name, amount, unit):
    unit = unit.lower().strip()

    # Universal weight units
    if unit in ["g", "gram", "grams"]:
        return amount

    if unit in ["oz", "ounce", "ounces"]:
        return amount * 28.3495

    if unit in ["lb", "lbs", "pound", "pounds"]:
        return amount * 453.592

    # Food-specific units
    matching_units = food_units[
        food_units["food_name"] == food_name
    ]

    for _, row in matching_units.iterrows():
        aliases = str(row["unit_aliases"]).split("|")

        if unit == row["unit_name"] or unit in aliases:
            return amount * row["grams_per_unit"]

    return None

test_grams = convert_to_grams(
    "Fairlife Fat Free Milk",
    1.5,
    "cups"
)

print("\nFUNCTION TEST:")
print(test_grams, "g")

def calculate_food(search_term, amount, unit):

    # 1. Find the closest food name / alias
    match = process.extractOne(
        search_term,
        search_choices.keys(),
        scorer=fuzz.WRatio
    )

    matched_text = match[0]
    confidence = match[1]
    canonical_food = search_choices[matched_text]

    # 2. Get that food's nutrition row
    matched_row = foods[
        foods["food_name"] == canonical_food
    ].iloc[0]

    # 3. Convert the entered amount into grams
    grams_eaten = convert_to_grams(
        canonical_food,
        amount,
        unit
    )

    if grams_eaten is None:
        return "Unit not recognized."

    # 4. Figure out how many grams the nutrition basis represents
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

    # 5. Scale the nutrition
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

result = calculate_food(
    "fair life ff",
    1.5,
    "cups"
)

print("\nCOMPLETE FOOD CALCULATION:")
print(result)

chicken_result = calculate_food(
    "chikn breast",
    6,
    "oz"
)

print("\nCHICKEN TEST:")
print(chicken_result)


import re

def parse_food_input(user_input):

    pattern = r"^\s*(\d*\.?\d+)\s*([a-zA-Z]+)\s+(.+)$"

    match = re.match(pattern, user_input)

    if not match:
        return None

    amount = float(match.group(1))
    unit = match.group(2)
    food_name = match.group(3)

    return amount, unit, food_name


parsed = parse_food_input("6 oz chikn breast")

print("\nPARSED INPUT:")
print(parsed)

user_input = "6 oz chikn breast"

parsed = parse_food_input(user_input)

if parsed:
    amount, unit, food_name = parsed

    result = calculate_food(
        food_name,
        amount,
        unit
    )

    print("\nONE-LINE FOOD ENTRY:")
    print(result)
else:
    print("Could not understand the food entry.")