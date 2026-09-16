import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FoodLogAppTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        os.environ.pop("FOOD_LOG_STORAGE", None)
        self.original_directory = Path.cwd()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(os.chdir, self.original_directory)
        for filename in ("foods_master.csv", "food_units.csv"):
            shutil.copyfile(PROJECT_ROOT / filename, Path(self.directory.name) / filename)
        os.chdir(self.directory.name)
        self.app = AppTest.from_file(str(PROJECT_ROOT / "food_log_app.py")).run()
        self.assertFalse(self.app.exception)

    def click(self, label):
        next(button for button in self.app.button if button.label == label).click().run()
        self.assertFalse(self.app.exception)

    def calculate_chicken(self):
        self.app.text_input(key="quick_entry").set_value("100 g chicken breast")
        self.click("Calculate Food")
        self.assertEqual(self.app.number_input(key="calories").value, 165.0)

    def test_amount_updates_display_and_saved_nutrition(self):
        self.calculate_chicken()
        self.app.number_input(key="amount").set_value(200.0).run()
        self.assertEqual(self.app.number_input(key="calories").value, 330.0)
        self.assertEqual(self.app.number_input(key="protein").value, 62.0)
        self.assertTrue(self.app.number_input(key="calories").disabled)
        self.assertTrue(self.app.text_input(key="food").disabled)
        self.click("Add Food")
        saved = self.app.session_state["demo_food_log"].iloc[0]
        self.assertEqual(saved["amount"], 200.0)
        self.assertEqual(saved["calories"], 330.0)
        self.assertEqual(saved["protein_g"], 62.0)
        self.assertEqual(self.app.metric[0].value, "330")
        self.assertEqual(self.app.metric[1].value, "62.0 g")
        self.assertFalse(Path("food_log.csv").exists())

    def test_unit_updates_display_and_saved_nutrition(self):
        self.calculate_chicken()
        self.app.number_input(key="amount").set_value(1.0)
        self.app.text_input(key="unit").set_value("oz").run()
        self.assertEqual(self.app.number_input(key="calories").value, 46.8)
        self.assertEqual(self.app.number_input(key="protein").value, 8.8)
        self.click("Add Food")
        saved = self.app.session_state["demo_food_log"].iloc[0]
        self.assertEqual(saved["unit"], "oz")
        self.assertEqual(saved["calories"], 46.8)

    def test_unsupported_unit_blocks_save_and_recovers(self):
        self.calculate_chicken()
        self.app.text_input(key="unit").set_value("bucket").run()
        self.assertTrue(self.app.error)
        self.assertTrue(next(b for b in self.app.button if b.label == "Add Food").disabled)
        self.assertEqual(self.app.number_input(key="calories").value, 0.0)
        self.assertFalse(Path("food_log.csv").exists())
        self.app.text_input(key="unit").set_value("g").run()
        self.assertFalse(self.app.error)
        self.assertEqual(self.app.number_input(key="calories").value, 165.0)
        self.assertFalse(next(b for b in self.app.button if b.label == "Add Food").disabled)

    def test_manual_entry_still_saves_entered_values(self):
        self.app.text_input(key="food").set_value("Homemade snack")
        self.app.text_input(key="unit").set_value("serving")
        self.app.number_input(key="calories").set_value(123.0)
        self.app.number_input(key="protein").set_value(7.0)
        self.click("Add Food")
        saved = self.app.session_state["demo_food_log"].iloc[0]
        self.assertEqual(saved["food"], "Homemade snack")
        self.assertEqual(saved["calories"], 123.0)
        self.assertEqual(saved["protein_g"], 7.0)

    def test_returning_from_manual_mode_restores_confirmed_food(self):
        self.calculate_chicken()
        self.app.checkbox(key="manual_nutrition").check().run()
        self.app.text_input(key="food").set_value("My snack")
        self.app.number_input(key="amount").set_value(200.0)
        self.app.number_input(key="calories").set_value(999.0).run()
        self.app.checkbox(key="manual_nutrition").uncheck().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.text_input(key="food").value, "Chicken Breast Cooked")
        self.assertEqual(self.app.number_input(key="calories").value, 330.0)

    def test_demo_ignores_existing_csv_and_never_overwrites_it(self):
        csv_file = Path("food_log.csv")
        # This intentionally isn't a food-log schema: any read would fail later.
        original_contents = b"private_local_data\nnever_show_this\n"
        csv_file.write_bytes(original_contents)
        self.app = AppTest.from_file(str(PROJECT_ROOT / "food_log_app.py")).run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.session_state["demo_food_log"].empty)
        self.calculate_chicken()
        self.click("Add Food")
        self.click("Load example meal")
        self.click("Reset demo")
        self.assertEqual(csv_file.read_bytes(), original_contents)

    def test_demo_logs_are_isolated_between_sessions(self):
        self.click("Load example meal")
        first_session = self.app
        first_log = first_session.session_state["demo_food_log"].copy(deep=True)
        self.app = AppTest.from_file(str(PROJECT_ROOT / "food_log_app.py")).run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.session_state["demo_food_log"].empty)
        self.calculate_chicken()
        self.click("Add Food")
        self.assertEqual(len(self.app.session_state["demo_food_log"]), 1)
        first_session.run()
        pd.testing.assert_frame_equal(first_session.session_state["demo_food_log"], first_log)
        self.assertFalse(Path("food_log.csv").exists())

    def test_example_meal_uses_calculated_values_and_replaces_existing_log(self):
        from food_engine import calculate_food

        self.calculate_chicken()
        self.click("Add Food")
        self.click("Load example meal")
        sample = self.app.session_state["demo_food_log"].copy(deep=True)
        self.assertEqual(len(sample), 3)
        for row in sample.to_dict("records"):
            result = calculate_food(row["food"], row["amount"], row["unit"])
            self.assertEqual(row["calories"], result["calories"])
            self.assertEqual(row["protein_g"], result["protein_g"])
        self.assertEqual(self.app.metric[0].value, "385")
        self.assertEqual(self.app.metric[1].value, "38.8 g")
        self.click("Load example meal")
        repeated_sample = self.app.session_state["demo_food_log"]
        pd.testing.assert_frame_equal(
            sample.drop(columns="timestamp"), repeated_sample.drop(columns="timestamp")
        )
        self.assertFalse(Path("food_log.csv").exists())

    def test_reset_clears_log_and_all_entry_state(self):
        self.calculate_chicken()
        self.click("Add Food")
        self.app.checkbox(key="manual_nutrition").check().run()
        self.app.text_input(key="food").set_value("My snack")
        self.app.text_input(key="unit").set_value("serving")
        self.app.number_input(key="amount").set_value(4.0)
        self.app.number_input(key="calories").set_value(999.0)
        self.app.number_input(key="protein").set_value(9.0)
        self.app.text_input(key="quick_entry").set_value("100 g chik brst")
        self.click("Calculate Food")
        self.assertIn("suggested_food", self.app.session_state)
        self.assertIn("calculated_food", self.app.session_state)
        self.click("Reset demo")
        self.assertTrue(self.app.session_state["demo_food_log"].empty)
        self.assertNotIn("suggested_food", self.app.session_state)
        self.assertNotIn("calculated_food", self.app.session_state)
        self.assertTrue(self.app.checkbox(key="manual_nutrition").value)
        self.assertTrue(self.app.checkbox(key="manual_nutrition").disabled)
        for key in ("quick_entry", "food", "unit"):
            self.assertEqual(self.app.text_input(key=key).value, "")
        self.assertEqual(self.app.number_input(key="amount").value, 1.0)
        for key in ("calories", "protein"):
            self.assertEqual(self.app.number_input(key=key).value, 0.0)
        self.assertEqual(self.app.metric[0].value, "0")
        self.assertEqual(self.app.metric[1].value, "0.0 g")

    def test_failed_quick_entry_discards_previous_suggestion(self):
        for bad_entry in ("not a valid entry", "1 cup chicken breast"):
            with self.subTest(entry=bad_entry):
                self.app.text_input(key="quick_entry").set_value("100 g chik brst")
                self.click("Calculate Food")
                self.assertIn("suggested_food", self.app.session_state)
                self.app.text_input(key="quick_entry").set_value(bad_entry)
                self.click("Calculate Food")
                self.assertTrue(self.app.error)
                self.assertNotIn("suggested_food", self.app.session_state)
                self.assertNotIn("Use Suggested Match", [b.label for b in self.app.button])

    def test_explicit_csv_mode_persists_across_sessions(self):
        os.environ["FOOD_LOG_STORAGE"] = "csv"
        self.app = AppTest.from_file(str(PROJECT_ROOT / "food_log_app.py")).run()
        self.assertFalse(self.app.exception)
        self.assertNotIn("Reset demo", [b.label for b in self.app.button])
        self.assertNotIn("Load example meal", [b.label for b in self.app.button])
        self.calculate_chicken()
        self.app.number_input(key="amount").set_value(200.0).run()
        self.click("Add Food")
        saved = pd.read_csv("food_log.csv")
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved.iloc[0]["calories"], 330.0)
        self.assertEqual(saved.iloc[0]["protein_g"], 62.0)
        self.app = AppTest.from_file(str(PROJECT_ROOT / "food_log_app.py")).run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.metric[0].value, "330")
        self.calculate_chicken()
        self.click("Add Food")
        self.assertEqual(len(pd.read_csv("food_log.csv")), 2)
        self.assertEqual(self.app.metric[0].value, "495")


if __name__ == "__main__":
    unittest.main()
