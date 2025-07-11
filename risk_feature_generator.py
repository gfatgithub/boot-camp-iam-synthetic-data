"""
risk_feature_generator.py
======================
Builds a per‑employee‑per‑permission **feature table** for the boot‑camp IAM
agent demo and saves it as `output/risk_features.csv`.

Features included
-----------------
* **off_baseline**     – permission is *not* in the role’s golden baseline
* **peer_outlier**     – held by fewer than 20% of peers with the same role
* **dormant**          – unused for ≥ 90 days (or never used)
* **high_sensitivity** – flag inherited from the permission catalogue
* **risk_score**       – simple additive score (0‑4) for demonstration

Edit the constants in the **CONFIG** section to adjust thresholds or paths.
"""

# ────────────────────────────────────────────────────────────────
# Imports
# ────────────────────────────────────────────────────────────────
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# ────────────────────────────────────────────────────────────────
# 1) CONFIG
# ────────────────────────────────────────────────────────────────
DATA_DIR        = Path("./output")          # where Generate_data.py wrote the CSVs
OUT_FILE        = DATA_DIR / "risk_features.csv"

PEER_THRESHOLD  = 0.20                       # < 20% peers ⇒ peer_outlier = 1
DORMANT_DAYS    = 90                         # unused ≥ 90 days ⇒ dormant = 1

# ────────────────────────────────────────────────────────────────
# 2) LOAD INPUT DATA
# ────────────────────────────────────────────────────────────────
employees              = pd.read_csv(DATA_DIR / "employees.csv")
permissions            = pd.read_csv(DATA_DIR / "permissions.csv")
role_baseline          = pd.read_csv(DATA_DIR / "role_permission_baseline.csv")
permission_assignments = pd.read_csv(DATA_DIR / "permission_assignments.csv")
auth_events            = pd.read_csv(
    DATA_DIR / "auth_events.csv", parse_dates=["timestamp"]
)

print(
    "Loaded:",
    len(employees), "employees  |",
    len(permission_assignments), "assignments  |",
    len(auth_events), "events",
)

# ────────────────────────────────────────────────────────────────
# 3) FEATURE – off_baseline (0 / 1)
# ────────────────────────────────────────────────────────────────
baseline_lookup = (
    role_baseline
    .assign(is_baseline=1)
    .set_index(["role_title", "Action"])["is_baseline"]
)

assign = permission_assignments.copy()
assign["off_baseline"] = assign.apply(
    lambda r: 0 if baseline_lookup.get((r["role_title"], r["Action"]), 0) == 1 else 1,
    axis=1,
)

# ────────────────────────────────────────────────────────────────
# 4) FEATURE – peer_outlier (0 / 1)
# ────────────────────────────────────────────────────────────────
peer_counts = (
    assign.groupby(["role_title", "Action"])["emp_no"].nunique().rename("peer_holders")
)
role_sizes = (
    employees.groupby("role_title")["emp_no"].nunique().rename("role_size")
)

assign = assign.join(peer_counts, on=["role_title", "Action"])
assign = assign.join(role_sizes, on="role_title")
assign["peer_pct"]      = assign["peer_holders"] / assign["role_size"]
assign["peer_outlier"] = (assign["peer_pct"] < PEER_THRESHOLD).astype(int)

# ────────────────────────────────────────────────────────────────
# 5) FEATURE – dormant (0 / 1)
# ────────────────────────────────────────────────────────────────
if not auth_events.empty:
    last_used = (
        auth_events
        .groupby(["emp_no", "permission"])["timestamp"]
        .max()
        .rename("last_used")
    )
    assign = assign.join(last_used, on=["emp_no", "Action"], how="left")
    cutoff  = datetime.now() - timedelta(days=DORMANT_DAYS)
    assign["dormant"] = (
        assign["last_used"].isna() | (assign["last_used"] < cutoff)
    ).astype(int)
else:
    # no events at all ⇒ mark everything dormant
    assign["dormant"] = 1

# ────────────────────────────────────────────────────────────────
# 6) FEATURE – high_sensitivity (0 / 1)
# ────────────────────────────────────────────────────────────────
high_sens_lookup = (
    permissions.drop_duplicates("Action")
    .set_index("Action")["highSensitivity"]
    .fillna(False)
)
assign["high_sensitivity"] = assign["Action"].map(high_sens_lookup).astype(int)

# ────────────────────────────────────────────────────────────────
# 7) AGGREGATE – risk_score (0‑4)
# ────────────────────────────────────────────────────────────────
assign["risk_score"] = (
    assign["off_baseline"]
    + assign["peer_outlier"]
    + assign["dormant"]
    + assign["high_sensitivity"]
)

# ────────────────────────────────────────────────────────────────
# 8) SAVE OUTPUT
# ────────────────────────────────────────────────────────────────
feature_cols = [
    "emp_no",
    "role_title",
    "Action",
    "off_baseline",
    "peer_outlier",
    "dormant",
    "high_sensitivity",
    "risk_score",
]

assign[feature_cols].to_csv(OUT_FILE, index=False)
print("Saved:", OUT_FILE)
