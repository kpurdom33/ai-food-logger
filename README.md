# Food Logger

A Streamlit app for logging meals from plain-language food entries. It matches
food names against the bundled food data, converts supported portions to grams,
and recalculates calories and protein when the portion changes.

## Run the public demo locally

From this project folder in PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run food_log_app.py
```

The default is **demo mode**. Each browser session has its own in-memory log.
The app never reads or writes `food_log.csv` in this mode. Refreshing the page,
losing the session, or restarting the server clears the demo log.

- **Reset demo** clears the session log, entry fields, and pending food matches.
- Try `100 g chicken breast`, select **Calculate Food**, adjust the amount or unit,
  and select **Add Food**. Confirm suggested matches when prompted. Unsupported
  units must be corrected before calculated entries can be saved.
- **Enter nutrition manually** lets you supply nutrition for your own foods.

For a public Streamlit deployment, leave `FOOD_LOG_STORAGE` unset. No storage
settings are exposed to visitors.

## Optional local CSV storage

To keep a personal log between app restarts, set this environment variable before
launching the app in PowerShell:

```powershell
$env:FOOD_LOG_STORAGE = "csv"
.venv\Scripts\python.exe -m streamlit run food_log_app.py
```

This explicitly enables reading and writing `food_log.csv` in the working
directory, including any existing history. CSV mode is intended for a local,
single-user app: all sessions on that server use the same file.

Stop the app, then unset the variable to return to demo mode:

```powershell
Remove-Item Env:FOOD_LOG_STORAGE -ErrorAction SilentlyContinue
.venv\Scripts\python.exe -m streamlit run food_log_app.py
```

## Verify

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests exercise session isolation, untouched local CSV files in demo mode,
example/reset actions, portion recalculation, manual entries, failed suggestions,
and explicit CSV persistence.
