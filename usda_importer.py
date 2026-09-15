from pathlib import Path
import re
import pandas as pd


# --------------------------------------------------
# CONFIG
# --------------------------------------------------

SR_FOLDER = Path("usda_sr_legacy")
FOUNDATION_FOLDER = Path("usda_data")

OUTPUT_SELECTED = Path("usda_selected_foods_v2.csv")
OUTPUT_REVIEW = Path("usda_review_needed.csv")
OUTPUT_APP = Path("usda_app_foods_v2.csv")
OUTPUT_MASTER = Path("foods_master_v2.csv")

NUTRIENT_IDS = {
    1008: "calories",
    1003: "protein_g",
    1005: "carbs_g",
    1004: "fat_g",
    1079: "fiber_g",
}

COOKED_MARKERS = [
    "cooked",
    "roasted",
    "grilled",
    "broiled",
    "boiled",
    "braised",
    "steamed",
    "baked",
    "dry heat",
    "pan-broiled",
    "pan-browned",
    "sauteed",
]


# --------------------------------------------------
# TEXT HELPERS
# --------------------------------------------------

def norm(text):
    text = str(text).lower()
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def has_term(text, term):
    """Whole-word / whole-phrase check."""
    text = norm(text)
    term = norm(term)
    pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
    return re.search(pattern, text) is not None


def has_any(text, terms):
    return any(has_term(text, term) for term in terms)


def starts_with_any(text, prefixes):
    text = norm(text)
    return any(text.startswith(norm(prefix)) for prefix in prefixes)


# --------------------------------------------------
# LOAD USDA DATA
# --------------------------------------------------

def load_usda_dataset(folder, source_name):
    food_file = folder / "food.csv"
    nutrient_file = folder / "food_nutrient.csv"
    category_file = folder / "food_category.csv"

    if not food_file.exists() or not nutrient_file.exists():
        print(f"Skipping {source_name}: required files not found in {folder}")
        return pd.DataFrame()

    food = pd.read_csv(food_file)
    food_nutrient = pd.read_csv(
        nutrient_file,
        low_memory=False
    )

    wanted = food_nutrient[
        food_nutrient["nutrient_id"].isin(NUTRIENT_IDS)
    ]

    nutrition_wide = wanted.pivot_table(
        index="fdc_id",
        columns="nutrient_id",
        values="amount",
        aggfunc="first",
    ).reset_index()

    nutrition_wide = nutrition_wide.rename(columns=NUTRIENT_IDS)

    result = food.merge(
        nutrition_wide,
        on="fdc_id",
        how="left",
    )

    result["source_dataset"] = source_name

    # Add readable category names when the dataset includes categories.
    if category_file.exists() and "food_category_id" in result.columns:
        categories = pd.read_csv(category_file)[["id", "description"]].rename(
            columns={"description": "category"}
        )
        result = result.merge(
            categories,
            left_on="food_category_id",
            right_on="id",
            how="left",
        )
    else:
        result["category"] = ""

    result["description"] = result["description"].astype(str)
    result["category"] = result["category"].fillna("").astype(str)

    return result


frames = [
    load_usda_dataset(SR_FOLDER, "USDA SR Legacy"),
    load_usda_dataset(FOUNDATION_FOLDER, "USDA Foundation"),
]

frames = [frame for frame in frames if not frame.empty]

if not frames:
    raise FileNotFoundError(
        "No USDA datasets could be loaded. Check usda_sr_legacy/ and usda_data/."
    )

all_foods = pd.concat(frames, ignore_index=True)
all_foods = all_foods.dropna(subset=["calories", "protein_g"]).copy()

print("USDA foods available:", len(all_foods))


# --------------------------------------------------
# TARGET DEFINITION HELPERS
# --------------------------------------------------

TARGETS = []


def add_target(
    name,
    required,
    categories,
    state="generic",
    starts=None,
    preferred=None,
    forbidden=None,
    aliases=None,
):
    TARGETS.append(
        {
            "food_name": name,
            "required": required,
            "categories": categories,
            "state": state,
            "starts": starts or [],
            "preferred": preferred or [],
            "forbidden": forbidden or [],
            "aliases": aliases or [],
        }
    )


def add_pair(
    base_name,
    required,
    categories,
    starts,
    preferred=None,
    forbidden=None,
    aliases=None,
):
    aliases = aliases or []

    add_target(
        f"{base_name} Raw",
        required=required,
        categories=categories,
        state="raw",
        starts=starts,
        preferred=preferred,
        forbidden=forbidden,
        aliases=[f"{base_name.lower()} raw", f"raw {base_name.lower()}"] + aliases,
    )

    add_target(
        f"{base_name} Cooked",
        required=required,
        categories=categories,
        state="cooked",
        starts=starts,
        preferred=preferred,
        forbidden=forbidden,
        aliases=[f"{base_name.lower()} cooked", f"cooked {base_name.lower()}"] + aliases,
    )


preferred_fdc_ids = {
    "Cheddar Cheese": 173414,
    "Brown Rice Cooked": 168875,
    "Apple Raw": 167793,
    "Tomato Raw": 170457,
    "Tomato Cooked": 170050,
}

POULTRY = ["Poultry Products"]
BEEF = ["Beef Products"]
PORK = ["Pork Products"]
SEAFOOD = ["Finfish and Shellfish Products"]
DAIRY = ["Dairy and Egg Products"]
GRAINS = ["Cereal Grains and Pasta", "Breakfast Cereals"]
BAKED = ["Baked Products"]
LEGUMES = ["Legumes and Legume Products"]
VEGETABLES = ["Vegetables and Vegetable Products"]
FRUITS = ["Fruits and Fruit Juices"]
NUTS = ["Nut and Seed Products"]

MEAT_FORBIDDEN = [
    "breaded",
    "batter",
    "fried",
    "rotisserie",
    "barbecue",
    "bbq",
    "canned",
    "pre-basted",
    "with added solution",
    "luncheon",
    "deli",
]

# Poultry
for base, required, starts in [
    ("Chicken Breast", [["chicken"], ["breast"]], ["chicken"]),
    ("Chicken Thigh", [["chicken"], ["thigh", "thighs"]], ["chicken"]),
    ("Chicken Drumstick", [["chicken"], ["drumstick", "drumsticks"]], ["chicken"]),
    ("Chicken Wing", [["chicken"], ["wing", "wings"]], ["chicken"]),
    ("Turkey Breast", [["turkey"], ["breast"]], ["turkey"]),
]:
    add_pair(
        base,
        required,
        POULTRY,
        starts,
        preferred=["meat only", "skinless", "boneless"],
        forbidden=MEAT_FORBIDDEN + ["meat and skin"],
    )

add_pair(
    "Ground Turkey 93/7",
    [["turkey"], ["ground"], ["93%"]],
    POULTRY,
    ["turkey"],
    preferred=["93% lean", "7% fat"],
    forbidden=MEAT_FORBIDDEN,
    aliases=["93/7 ground turkey", "ground turkey 93/7"],
)

# Beef
add_pair(
    "Ground Beef 95/5",
    [["beef"], ["ground"], ["95%"]],
    BEEF,
    ["beef"],
    preferred=["95% lean", "5% fat"],
    forbidden=MEAT_FORBIDDEN,
    aliases=["95/5 ground beef", "ground beef 95/5"],
)

for base, required, preferred in [
    ("Beef Top Sirloin", [["beef"], ["sirloin"]], ["top sirloin", "steak", "all grades"]),
    ("Beef Tenderloin", [["beef"], ["tenderloin"]], ["steak", "all grades"]),
    ("Beef Ribeye", [["beef"], ["ribeye"]], ["steak", "all grades"]),
    ("Beef Chuck", [["beef"], ["chuck"]], ["roast", "all grades"]),
    ("Beef Round", [["beef"], ["round"]], ["top round", "all grades"]),
    ("Beef Brisket", [["beef"], ["brisket"]], ["flat half", "all grades"]),
]:
    add_pair(
        base,
        required,
        BEEF,
        ["beef"],
        preferred=preferred,
        forbidden=MEAT_FORBIDDEN + ["ground"],
    )

# Pork
for base, required, preferred in [
    ("Pork Loin", [["pork"], ["loin"]], ["loin, whole"]),
    ("Pork Chop", [["pork"], ["chop", "chops"]], ["center loin", "chops"]),
    ("Pork Tenderloin", [["pork"], ["tenderloin"]], ["tenderloin"]),
    ("Pork Shoulder", [["pork"], ["shoulder"]], ["shoulder, whole", "boston butt"]),
]:
    add_pair(
        base,
        required,
        PORK,
        ["pork"],
        preferred=preferred,
        forbidden=MEAT_FORBIDDEN + ["composite"],
    )

# Seafood
for base, required, starts, preferred in [
    ("Salmon", [["salmon"]], ["fish, salmon"], ["atlantic", "wild"]),
    ("Tilapia", [["tilapia"]], ["fish, tilapia"], []),
    ("Tuna", [["tuna"]], ["fish, tuna"], ["yellowfin", "fresh"]),
    ("Shrimp", [["shrimp"]], ["crustaceans, shrimp"], ["mixed species"]),
    ("Cod", [["cod"]], ["fish, cod"], ["atlantic"]),
]:
    add_pair(
        base,
        required,
        SEAFOOD,
        starts,
        preferred=preferred,
        forbidden=["breaded", "fried", "canned", "smoked", "imitation", "oil"],
    )

# Eggs / dairy
add_target(
    "Egg Whole Raw",
    required=[["egg"], ["whole"]],
    categories=DAIRY,
    state="raw",
    starts=["egg"],
    forbidden=["dried", "powder", "substitute", "white", "yolk"],
    aliases=["whole egg raw", "raw whole egg", "raw egg"],
)

add_target(
    "Egg Whole Cooked",
    required=[["egg"], ["whole"]],
    categories=DAIRY,
    state="cooked",
    starts=["egg"],
    preferred=["hard-boiled", "poached"],
    forbidden=["dried", "powder", "substitute", "white", "yolk"],
    aliases=["whole egg cooked", "cooked whole egg", "cooked egg"],
)

add_target(
    "Greek Yogurt Plain Nonfat",
    required=[["yogurt"], ["greek"], ["plain"], ["nonfat"]],
    categories=DAIRY,
    starts=["yogurt"],
    aliases=["greek yogurt", "nonfat greek yogurt", "fat free greek yogurt", "plain greek yogurt"],
)

add_target(
    "Greek Yogurt Plain Lowfat",
    required=[["yogurt"], ["greek"], ["plain"], ["lowfat", "low fat"]],
    categories=DAIRY,
    starts=["yogurt"],
    aliases=["lowfat greek yogurt", "low fat greek yogurt"],
)

add_target(
    "Cottage Cheese 1%",
    required=[["cheese"], ["cottage"], ["1%"]],
    categories=DAIRY,
    starts=["cheese, cottage"],
    preferred=["lowfat", "1% milkfat"],
    aliases=["1% cottage cheese", "cottage cheese 1%"],
)

add_target(
    "Cottage Cheese 2%",
    required=[["cheese"], ["cottage"], ["2%"]],
    categories=DAIRY,
    starts=["cheese, cottage"],
    preferred=["lowfat", "2% milkfat"],
    aliases=["2% cottage cheese", "cottage cheese 2%"],
)

add_target(
    "Cheddar Cheese",
    required=[["cheese"], ["cheddar"]],
    categories=DAIRY,
    starts=["cheese, cheddar"],
    forbidden=["imitation", "process", "spread", "reduced fat", "nonfat", "fat free", "snack"],
    aliases=["cheddar", "cheddar cheese"],
)

add_target(
    "Mozzarella Whole Milk",
    required=[["cheese"], ["mozzarella"], ["whole milk"]],
    categories=DAIRY,
    starts=["cheese, mozzarella"],
    forbidden=["substitute", "nonfat"],
    aliases=["whole milk mozzarella", "mozzarella cheese"],
)

for name, required, aliases in [
    ("Whole Milk", [["milk"], ["whole"]], ["whole milk"]),
    ("Milk 2%", [["milk"], ["2%"]], ["2% milk", "two percent milk"]),
    ("Milk 1%", [["milk"], ["1%"]], ["1% milk", "one percent milk"]),
    ("Fat Free Milk", [["milk"], ["nonfat", "skim"]], ["fat free milk", "skim milk", "nonfat milk"]),
]:
    add_target(
        name,
        required=required,
        categories=DAIRY,
        starts=["milk"],
        forbidden=["buttermilk", "chocolate", "dry", "powder", "condensed", "evaporated"],
        aliases=aliases,
    )

# Grains / starches
add_target(
    "White Rice Cooked",
    required=[["rice"], ["white"], ["cooked"]],
    categories=GRAINS,
    starts=["rice"],
    preferred=["long-grain", "regular"],
    forbidden=["fried rice", "pudding", "flour", "mix"],
    aliases=["white rice", "cooked white rice", "rice white"],
)

add_target(
    "Brown Rice Cooked",
    required=[["rice"], ["brown"], ["cooked"]],
    categories=GRAINS,
    starts=["rice"],
    forbidden=["cakes", "cracker", "sausage", "flour"],
    aliases=["brown rice", "cooked brown rice"],
)

add_target(
    "Oats Dry",
    required=[["oats"]],
    categories=GRAINS,
    state="generic",
    starts=["oats"],
    forbidden=["cereal", "bar", "honey", "flavored"],
    aliases=["oats", "dry oats", "rolled oats"],
)

add_target(
    "Oatmeal Cooked",
    required=[["oats"], ["cooked", "prepared"]],
    categories=GRAINS,
    starts=["cereals, oats"],
    preferred=["prepared with water", "unenriched"],
    forbidden=["cinnamon", "flavored", "sugar"],
    aliases=["oatmeal", "cooked oats"],
)

add_target(
    "Pasta Cooked",
    required=[["pasta"], ["cooked"]],
    categories=GRAINS,
    starts=["pasta"],
    preferred=["unenriched", "without added salt"],
    forbidden=["gluten-free", "whole-wheat", "mix", "entree"],
    aliases=[
        "pasta",
        "cooked pasta",
        "spaghetti",
        "cooked spaghetti"
        ],
)



add_target(
    "White Bread",
    required=[["bread"], ["white"]],
    categories=BAKED,
    starts=["bread"],
    forbidden=["gluten-free", "sweet", "garlic", "pound cake"],
    aliases=["white bread"],
)

add_target(
    "Whole Wheat Bread",
    required=[["bread"], ["whole wheat", "whole-wheat"]],
    categories=BAKED,
    starts=["bread"],
    forbidden=["gluten-free", "sweet"],
    aliases=["whole wheat bread", "whole-wheat bread"],
)

add_target(
    "Corn Tortilla",
    required=[["tortilla", "tortillas"], ["corn"]],
    categories=BAKED,
    starts=["tortilla", "tortillas"],
    forbidden=["chips", "shell", "flour"],
    aliases=["corn tortilla", "corn tortillas"],
)

add_target(
    "Flour Tortilla",
    required=[["tortilla", "tortillas"], ["flour"]],
    categories=BAKED,
    starts=["tortilla", "tortillas"],
    forbidden=["chips", "corn"],
    aliases=["flour tortilla", "flour tortillas"],
)

add_pair(
    "Potato",
    [["potato", "potatoes"]],
    VEGETABLES,
    ["potato", "potatoes"],
    preferred=["flesh and skin"],
    forbidden=["sweet potato", "hash brown", "french fried", "chips", "puffs"],
)

add_pair(
    "Sweet Potato",
    [["sweet potato", "sweet potatoes"]],
    VEGETABLES,
    ["sweet potato", "sweet potatoes"],
    forbidden=["french fried", "puffs", "leaves"],
)

add_target(
    "Quinoa Cooked",
    required=[["quinoa"], ["cooked"]],
    categories=GRAINS,
    starts=["quinoa"],
    aliases=["quinoa", "cooked quinoa"],
)

# Legumes
for name, required, aliases in [
    ("Black Beans Cooked", [["beans"], ["black"], ["cooked"]], ["black beans", "cooked black beans"]),
    ("Pinto Beans Cooked", [["beans"], ["pinto"], ["cooked"]], ["pinto beans", "cooked pinto beans"]),
    ("Kidney Beans Cooked", [["beans"], ["kidney"], ["cooked"]], ["kidney beans", "cooked kidney beans"]),
    ("Chickpeas Cooked", [["chickpeas"], ["cooked"]], ["chickpeas", "garbanzo beans"]),
    ("Lentils Cooked", [["lentils"], ["cooked"]], ["lentils", "cooked lentils"]),
]:
    starts = ["beans"] if "Beans" in name else ["chickpeas"] if "Chickpeas" in name else ["lentils"]
    add_target(
        name,
        required=required,
        categories=LEGUMES,
        state="cooked",
        starts=starts,
        preferred=["mature seeds", "boiled", "without salt"],
        forbidden=["sprouted", "canned", "liquid"],
        aliases=aliases,
    )

# Fruits
fruit_specs = [
    ("Banana Raw", [["banana", "bananas"]], ["banana", "bananas"], ["banana"]),
    ("Apple Raw", [["apple", "apples"]], ["apple", "apples"], ["apple"]),
    ("Orange Raw", [["orange", "oranges"]], ["orange", "oranges"], ["orange"]),
    ("Strawberry Raw", [["strawberry", "strawberries"]], ["strawberry", "strawberries"], ["strawberry"]),
    ("Blueberry Raw", [["blueberry", "blueberries"]], ["blueberry", "blueberries"], ["blueberry"]),
    ("Mango Raw", [["mango", "mangos", "mangoes"]], ["mango", "mangos", "mangoes"], ["mango"]),
    ("Grapes Raw", [["grape", "grapes"]], ["grape", "grapes"], ["grapes"]),
    ("Pineapple Raw", [["pineapple"]], ["pineapple"], ["pineapple"]),
    ("Avocado Raw", [["avocado", "avocados"]], ["avocado", "avocados"], ["avocado"]),
]

for name, required, starts, aliases in fruit_specs:
    add_target(
        name,
        required=required,
        categories=FRUITS,
        state="raw",
        starts=starts,
        preferred=["all varieties", "all commercial varieties"],
        forbidden=["juice", "dried", "canned", "syrup", "smoothie", "pie", "yogurt", "oil", "peel", "nectar", "sauce"],
        aliases=aliases + [f"raw {aliases[0]}"],
    )

# Vegetables
for base, required, starts in [
    ("Broccoli", [["broccoli"]], ["broccoli"]),
    ("Asparagus", [["asparagus"]], ["asparagus"]),
    ("Spinach", [["spinach"]], ["spinach"]),
    ("Carrot", [["carrot", "carrots"]], ["carrot", "carrots"]),
    ("Onion", [["onion", "onions"]], ["onion", "onions"]),
    ("Tomato", [["tomato", "tomatoes"]], ["tomato", "tomatoes"]),
    ("Sweet Pepper", [["pepper", "peppers"], ["sweet"]], ["pepper", "peppers"]),
]:
    add_pair(
        base,
        required,
        VEGETABLES,
        starts,
        forbidden=["soup", "sauce", "juice", "chips", "frozen", "canned", "dehydrated", "pickled"],
    )

add_target(
    "Green Beans Cooked",
    required=[["beans"], ["green"], ["cooked"]],
    categories=VEGETABLES,
    state="cooked",
    starts=["beans"],
    preferred=["snap", "boiled", "without salt"],
    forbidden=["soybeans", "mixed", "canned", "frozen"],
    aliases=["green beans", "cooked green beans"],
)

add_target(
    "Corn Cooked",
    required=[["corn"], ["cooked"]],
    categories=VEGETABLES,
    state="cooked",
    starts=["corn"],
    forbidden=["snack", "chips", "popcorn", "tortilla", "meal"],
    aliases=["corn", "cooked corn"],
)

# Nuts / seeds
add_target(
    "Peanut Butter",
    required=[["peanut butter"]],
    categories=LEGUMES,
    starts=["peanut butter"],
    preferred=["smooth", "without salt"],
    forbidden=["reduced fat", "cookie", "bar", "cereal"],
    aliases=["peanut butter", "pb"],
)

add_target(
    "Almonds",
    required=[["almond", "almonds"]],
    categories=NUTS,
    starts=["nuts, almonds"],
    preferred=["nuts, almonds"],
    forbidden=["honey roasted", "oil roasted", "dry roasted", "blanched"],
    aliases=["almond", "almonds"],
)

add_target(
    "Peanuts",
    required=[["peanut", "peanuts"]],
    categories=LEGUMES,
    starts=["peanuts", "nuts, peanuts"],
    preferred=["all types", "raw"],
    forbidden=["mixed nuts", "oil roasted", "dry roasted", "honey roasted"],
    aliases=["peanut", "peanuts"],
)

add_target(
    "Walnuts",
    required=[["walnut", "walnuts"]],
    categories=NUTS,
    starts=["nuts, walnuts"],
    preferred=["english"],
    forbidden=["glazed", "roasted", "cereal"],
    aliases=["walnut", "walnuts"],
)

add_target(
    "Chia Seeds",
    required=[["chia"], ["seed", "seeds"]],
    categories=NUTS,
    starts=["seeds, chia"],
    aliases=["chia", "chia seed", "chia seeds"],
)


# --------------------------------------------------
# STRICT FILTER + RANKING
# --------------------------------------------------

def candidate_matches(row, spec):
    desc = norm(row["description"])
    category = norm(row.get("category", ""))

    if spec["categories"]:
        allowed = {norm(value) for value in spec["categories"]}
        if category not in allowed:
            return False

    if spec["starts"] and not starts_with_any(desc, spec["starts"]):
        return False

    # Each inner list is a synonym group; at least one synonym in every group is required.
    for synonym_group in spec["required"]:
        if not has_any(desc, synonym_group):
            return False

    for bad in spec["forbidden"]:
        if has_term(desc, bad):
            return False

    state = spec["state"]

    if state == "raw":
        if not has_term(desc, "raw"):
            return False

    elif state == "cooked":
        if has_term(desc, "raw"):
            return False
        if not any(has_term(desc, marker) for marker in COOKED_MARKERS):
            return False

    return True


def score_candidate(row, spec):
    desc = norm(row["description"])
    score = 100.0

    # Prefer simple, generic descriptions.
    score -= len(desc) * 0.08

    for phrase in spec["preferred"]:
        if has_term(desc, phrase):
            score += 12

    # SR Legacy tends to have the generic foods we want for this project.
    if row["source_dataset"] == "USDA SR Legacy":
        score += 4

    # Reward descriptions that start directly with the first requested concept.
    if spec["starts"] and starts_with_any(desc, spec["starts"]):
        score += 8

    return round(score, 2)


def select_best(spec):

    # Use a manually preferred USDA record when we have one
    preferred_id = preferred_fdc_ids.get(
        spec["food_name"]
    )

    if preferred_id is not None:

        preferred_match = all_foods[
            all_foods["fdc_id"] == preferred_id
        ]

        if not preferred_match.empty:

            best = preferred_match.iloc[0].copy()

            best["selection_score"] = 999.0

            return best, ""


    # Otherwise use the normal strict matching system
    mask = all_foods.apply(
        lambda row: candidate_matches(row, spec),
        axis=1
    )

    candidates = all_foods[mask].copy()

    if candidates.empty:
        return None, "No candidate passed strict filters"

    candidates["selection_score"] = candidates.apply(
        lambda row: score_candidate(row, spec),
        axis=1
    )

    candidates = candidates.sort_values(
        ["selection_score", "source_dataset"],
        ascending=[False, True],
    )

    best = candidates.iloc[0]

    return best, ""

# --------------------------------------------------
# BUILD SELECTED + REVIEW FILES
# --------------------------------------------------

selected_rows = []
review_rows = []

for spec in TARGETS:
    best, reason = select_best(spec)

    if best is None:
        review_rows.append(
            {
                "food_name": spec["food_name"],
                "reason": reason,
                "required": str(spec["required"]),
                "categories": "|".join(spec["categories"]),
                "state": spec["state"],
            }
        )
        print(f"REVIEW: {spec['food_name']} - {reason}")
        continue

    selected_rows.append(
        {
            "food_name": spec["food_name"],
            "aliases": "|".join(dict.fromkeys([a.strip().lower() for a in spec["aliases"] if a.strip()])),
            "fdc_id": int(best["fdc_id"]),
            "usda_description": best["description"],
            "category": best.get("category", ""),
            "basis_amount": 100,
            "basis_unit": "g",
            "calories": best["calories"],
            "protein_g": best["protein_g"],
            "carbs_g": best.get("carbs_g"),
            "fat_g": best.get("fat_g"),
            "fiber_g": best.get("fiber_g"),
            "source": f"{best['source_dataset']} FDC {int(best['fdc_id'])}",
            "verified": True,
            "selection_score": best["selection_score"],
        }
    )

selected = pd.DataFrame(selected_rows)
review = pd.DataFrame(review_rows)

selected.to_csv(OUTPUT_SELECTED, index=False)
review.to_csv(OUTPUT_REVIEW, index=False)

print()
print("Strictly selected USDA foods:", len(selected))
print("Foods needing review:", len(review))
print("Created:", OUTPUT_SELECTED)
print("Created:", OUTPUT_REVIEW)


# --------------------------------------------------
# APP-READY USDA FILE
# --------------------------------------------------

APP_COLUMNS = [
    "food_name",
    "aliases",
    "basis_amount",
    "basis_unit",
    "calories",
    "protein_g",
    "carbs_g",
    "fat_g",
    "fiber_g",
    "source",
    "verified",
]

app_foods = selected[APP_COLUMNS].copy()
app_foods.to_csv(OUTPUT_APP, index=False)


# --------------------------------------------------
# MERGE ONLY TRUE CUSTOM FOODS
# --------------------------------------------------

def load_custom_foods():
    # Prefer the original backup if it exists.
    candidates = [
        Path("foods_master_backup.csv"),
        Path("foods_master.csv"),
    ]

    for path in candidates:
        if not path.exists():
            continue

        df = pd.read_csv(path)

        if "source" not in df.columns:
            continue

        # This deliberately strips out previously auto-generated USDA rows.
        custom = df[
            ~df["source"].astype(str).str.contains("USDA", case=False, na=False)
        ].copy()

        if not custom.empty:
            print(f"Custom foods loaded from {path}: {len(custom)}")
            return custom[APP_COLUMNS]

    return pd.DataFrame(columns=APP_COLUMNS)


custom_foods = load_custom_foods()

# Custom rows win when names collide.
custom_names = set(custom_foods["food_name"].astype(str))
new_usda = app_foods[
    ~app_foods["food_name"].astype(str).isin(custom_names)
].copy()

master_v2 = pd.concat(
    [custom_foods, new_usda],
    ignore_index=True,
)

master_v2.to_csv(OUTPUT_MASTER, index=False)

print("USDA app foods:", len(app_foods))
print("Custom foods preserved:", len(custom_foods))
print("Final v2 master foods:", len(master_v2))
print("Created:", OUTPUT_APP)
print("Created:", OUTPUT_MASTER)

if not review.empty:
    print()
    print("IMPORTANT: Review usda_review_needed.csv before replacing foods_master.csv.")
