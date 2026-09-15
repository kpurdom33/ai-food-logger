import pandas as pd
from pathlib import Path


# --------------------------------------------------
# FILES
# --------------------------------------------------

SELECTED_FILE = Path("usda_selected_foods_v2.csv")

SR_PORTIONS = Path(
    "usda_sr_legacy/food_portion.csv"
)

FOUNDATION_PORTIONS = Path(
    "usda_data/food_portion.csv"
)

EXISTING_UNITS = Path("food_units.csv")

OUTPUT_FILE = Path("food_units_v2.csv")


# --------------------------------------------------
# LOAD SELECTED FOODS
# --------------------------------------------------

foods = pd.read_csv(
    SELECTED_FILE
)


# --------------------------------------------------
# LOAD USDA PORTION TABLES
# --------------------------------------------------

portion_frames = []

for path in [
    SR_PORTIONS,
    FOUNDATION_PORTIONS
]:

    if path.exists():

        frame = pd.read_csv(
            path,
            low_memory=False
        )

        portion_frames.append(
            frame
        )


portions = pd.concat(
    portion_frames,
    ignore_index=True
)


# --------------------------------------------------
# MATCH OUR FOODS TO THEIR USDA PORTIONS
# --------------------------------------------------

food_portions = foods[
    ["food_name", "fdc_id"]
].merge(
    portions,
    on="fdc_id",
    how="inner"
)


# --------------------------------------------------
# CLEAN USDA UNIT NAMES
# --------------------------------------------------

def clean_unit_name(row):

    modifier = row.get(
        "modifier"
    )

    description = row.get(
        "portion_description"
    )

    if pd.notna(modifier):
        unit = str(modifier)

    elif pd.notna(description):
        unit = str(description)

    else:
        return None

    unit = unit.lower().strip()

    return unit


food_portions["unit_name"] = (
    food_portions.apply(
        clean_unit_name,
        axis=1
    )
)


# --------------------------------------------------
# CALCULATE GRAMS PER ONE UNIT
# --------------------------------------------------

food_portions = food_portions[
    food_portions["amount"].notna()
    & food_portions["gram_weight"].notna()
    & food_portions["unit_name"].notna()
].copy()


food_portions["grams_per_unit"] = (
    food_portions["gram_weight"]
    / food_portions["amount"]
)


# --------------------------------------------------
# CREATE FRIENDLY UNIT ALIASES
# --------------------------------------------------

def build_unit_aliases(unit):

    aliases = [unit]

    if unit == "tbsp":
        aliases += [
            "tablespoon",
            "tablespoons"
        ]

    elif unit == "tsp":
        aliases += [
            "teaspoon",
            "teaspoons"
        ]

    elif unit == "cup":
        aliases += [
            "cups"
        ]

    elif unit.startswith("slice"):
        aliases += [
            "slice",
            "slices"
        ]

    elif unit == "large":
        aliases += [
            "large"
        ]

    elif unit.startswith("medium"):
        aliases += [
            "medium"
        ]

    elif unit == "tortilla":
        aliases += [
            "tortilla",
            "tortillas"
        ]

    elif unit == "oz":
        aliases += [
            "ounce",
            "ounces"
        ]

    return "|".join(
        dict.fromkeys(aliases)
    )


food_portions["unit_aliases"] = (
    food_portions[
        "unit_name"
    ].apply(
        build_unit_aliases
    )
)


# --------------------------------------------------
# APP FORMAT
# --------------------------------------------------

generated_units = food_portions[
    [
        "food_name",
        "unit_name",
        "unit_aliases",
        "grams_per_unit"
    ]
].copy()


generated_units[
    "grams_per_unit"
] = generated_units[
    "grams_per_unit"
].round(2)


# --------------------------------------------------
# PRESERVE EXISTING CUSTOM UNITS
# --------------------------------------------------

if EXISTING_UNITS.exists():

    existing = pd.read_csv(
        EXISTING_UNITS
    )

else:

    existing = pd.DataFrame(
        columns=[
            "food_name",
            "unit_name",
            "unit_aliases",
            "grams_per_unit"
        ]
    )


combined = pd.concat(
    [
        existing,
        generated_units
    ],
    ignore_index=True
)


combined = combined.drop_duplicates(
    subset=[
        "food_name",
        "unit_name"
    ],
    keep="first"
)


combined.to_csv(
    OUTPUT_FILE,
    index=False
)


print(
    "USDA portion units generated:",
    len(generated_units)
)

print(
    "Existing custom units preserved:",
    len(existing)
)

print(
    "Total units:",
    len(combined)
)

print(
    "Created:",
    OUTPUT_FILE
)