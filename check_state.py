
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(os.getcwd())))

from Tools.state_store import SQLiteStateStore

store = SQLiteStateStore(Path("State/operator_state.db"))
workos_summary = store.get_state("workos_summary")
calendar_summary = store.get_state("calendar_summary")
daily_plan = store.get_state("daily_plan")

print("--- WORKOS SUMMARY ---")
print(workos_summary)
print("\n--- CALENDAR SUMMARY ---")
print(calendar_summary)
print("\n--- DAILY PLAN ---")
print(daily_plan)
