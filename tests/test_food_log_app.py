import os
from pathlib import Path
import shutil
import tempfile
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FoodLogAppTests(unittest.TestCase):
    def setUp(self):
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
        self.app.text_input[0].set_value("100 g chicken breast")
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
        saved = pd.read_csv("food_log.csv").iloc[0]
        self.assertEqual(saved["amount"], 200.0)
        self.assertEqual(saved["calories"], 330.0)
        self.assertEqual(saved["protein_g"], 62.0)

    def test_unit_updates_display_and_saved_nutrition(self):
        self.calculate_chicken()
        self.app.number_input(key="amount").set_value(1.0)
        self.app.text_input(key="unit").set_value("oz").run()
        self.assertEqual(self.app.number_input(key="calories").value, 46.8)
        self.assertEqual(self.app.number_input(key="protein").value, 8.8)
        self.click("Add Food")
        saved = pd.read_csv("food_log.csv").iloc[0]
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
        saved = pd.read_csv("food_log.csv").iloc[0]
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


if __name__ == "__main__":
    unittest.main()
