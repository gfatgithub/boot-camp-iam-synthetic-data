"""
Generate_data.py
======================
Boot-camp synthetic data generator – IAM risk-report use case
"""

# ────────────────────────────────────────────────────────────────
# Imports
# ────────────────────────────────────────────────────────────────
import os
import random
import datetime as dt

import numpy as np
import pandas as pd

# ────────────────────────────────────────────────────────────────
# 1) CONFIG
# ────────────────────────────────────────────────────────────────
IAM_FILE   = r"iam-dataset-main/aws/iam_definition.json"
OUTPUT_DIR = "./output"

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- CLEAN existing CSVs so we start fresh each run ---
for fname in os.listdir(OUTPUT_DIR):
    if fname.endswith(".csv"):
        os.remove(os.path.join(OUTPUT_DIR, fname))

# ────────────────────────────────────────────────────────────────
# 2) READ & NORMALISE AWS permission catalogue
# ────────────────────────────────────────────────────────────────
perm_raw = pd.read_json(IAM_FILE)

# • every row currently holds a list of privilege dicts → explode them
perm_long = perm_raw.explode("privileges", ignore_index=True)

# • flatten JSON fields we care about
perm_long["Action"]        = perm_long["privileges"].apply(lambda p: p["privilege"])
perm_long["access_level"]  = perm_long["privileges"].apply(lambda p: p["access_level"])

# • very naïve high-sensitivity flag: privileged or permissions-management actions
perm_long["highSensitivity"] = perm_long["access_level"].isin(
    ["Permissions management", "Privileged"]
)

# • drop the original nested column (optional housekeeping)
perm_long = perm_long.drop(columns=["privileges"])

# • use up to 500 random actions (or fewer if file is small)
sampled = perm_long.sample(min(len(perm_long), 500), replace=False).reset_index(drop=True)

# ────────────────────────────────────────────────────────────────
# 3) EMPLOYEE / ORG-CHART TABLE
# ────────────────────────────────────────────────────────────────
N_EMP = 250
role_titles = ["Developer", "DBA", "Security_Analyst", "Finance_Clerk"]

employees = pd.DataFrame({
    "emp_no": range(1, N_EMP + 1),
    # first 10 % become top-level managers → everyone else randomly reports to one of them
    "manager_emp_no": np.select(
        [np.arange(N_EMP) < N_EMP * 0.1],
        [None],
        default=np.random.randint(1, int(N_EMP * 0.1) + 1, N_EMP)
    ),
    "role_title": np.random.choice(role_titles, N_EMP)
})
employees.to_csv(os.path.join(OUTPUT_DIR, "employees.csv"), index=False)

# ────────────────────────────────────────────────────────────────
# 4) ROLE→PERMISSION BASELINE  (10 actions per role)
# ────────────────────────────────────────────────────────────────
role_baseline_rows = []
for i, role in enumerate(role_titles):
    role_actions = sampled.iloc[i::len(role_titles)].head(10).copy()
    role_actions["role_title"] = role
    role_baseline_rows.append(role_actions)

role_baseline = pd.concat(role_baseline_rows, ignore_index=True)
role_baseline[["role_title", "Action"]].to_csv(
    os.path.join(OUTPUT_DIR, "role_permission_baseline.csv"), index=False
)

# ────────────────────────────────────────────────────────────────
# 5) ACTUAL PERMISSION ASSIGNMENTS  (inject 10 % risky outliers)
# ────────────────────────────────────────────────────────────────
assign = role_baseline.sample(frac=1.2, replace=True).reset_index(drop=True)

# pick 10 % of rows and swap their Action to a random high-sensitivity permission
off_idx = assign.sample(frac=0.10).index
high_actions = sampled.query("highSensitivity")["Action"]
assign.loc[off_idx, "Action"] = high_actions.sample(len(off_idx), replace=True).values

# join with employees so each person inherits their role’s permissions
assign = employees[["emp_no", "role_title"]].merge(
    assign[["role_title", "Action"]], on="role_title"
)
assign.to_csv(os.path.join(OUTPUT_DIR, "permission_assignments.csv"), index=False)

# ────────────────────────────────────────────────────────────────
# 6) AUTH-EVENT LOG  (30-day window, 0-50 touches per emp-perm pair)
# ────────────────────────────────────────────────────────────────
EVENT_WINDOW_DAYS = 30
ts0 = dt.datetime.now() - dt.timedelta(days=EVENT_WINDOW_DAYS)
events = []

for _, row in assign.iterrows():
    for _ in range(random.randint(0, 50)):
        events.append({
            "timestamp": ts0 + dt.timedelta(
                days=random.randint(0, EVENT_WINDOW_DAYS-1),
                seconds=random.randint(0, 86_400)
            ),
            "emp_no": row.emp_no,
            "permission": row.Action
        })

pd.DataFrame(events).to_csv(
    os.path.join(OUTPUT_DIR, "auth_events.csv"), index=False
)

# ────────────────────────────────────────────────────────────────
# 7) OPTIONAL – save the full sampled permission catalogue
# ────────────────────────────────────────────────────────────────
sampled.to_csv(os.path.join(OUTPUT_DIR, "permissions.csv"), index=False)

print("Done.  Generated:\n"
      "  • employees.csv\n"
      "  • permissions.csv\n"
      "  • role_permission_baseline.csv\n"
      "  • permission_assignments.csv\n"
      "  • auth_events.csv")
