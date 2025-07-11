# Boot‑Camp IAM Agent — Synthetic Data Pack

This repository helps you **simulate enterprise access‑permission data** so you can build and demo the AI‑agent described in the boot‑camp use case:

> *“Ingest access‑permission data across the organization; assess & report to managers the risk of those permissions; and recommend which entitlements need individual review.”*

Generate two type of output:
1. **Raw data** — `Generate_data.py` writes 5 CSVs to `./output/`.
2. **Risk features** — `risk_feature_generator.py` turns those CSVs into `risk_features.csv`.

---

## 📂 Project Structure

```text
├── Generate_data.py           # one‑click data generator
├── iam-dataset-main/          # open‑source AWS IAM catalogue (external)**
├── output/                    # fresh CSVs land here each run
└── risk_feature_generator.py  # (optional) builds risk_features.csv
```
> **NOTE**
> 
> The script expects `iam-dataset-main/aws/iam_definition.json`. 
> If you clone the whole *iam‑dataset* repo elsewhere, update `IAM_FILE` at the top of `Generate_data.py`.
>
> Data has been sourced from [https://github.com/iann0036/iam-dataset](https://github.com/iann0036/iam-dataset).

---

## 🛠️ Prerequisites

* `Python 3.9+`
* `pandas`, `numpy` (installed automatically with `pip install -r requirements.txt` or manually)

---

## 🚀 Quick Start

```bash
# 1. Create & activate a virtual environment (optional)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install deps
pip install -r requirements.txt

# 3. Generate synthetic data
python Generate_data.py      # CSVs will appear in ./output

# 4. (Optional) Build the risk feature table
python risk_feature_generator.py  # creates output/risk_features.csv
```

### ⚙️ Config Constants (edit in **Generate_data.py**)
| Name | Default | Meaning |
|------|---------|---------|
| `IAM_FILE` | `iam-dataset-main/aws/iam_definition.json` | Path to permission catalogue JSON |
| `OUTPUT_DIR` | `./output` | Folder is wiped & recreated on every run |
| `EVENT_WINDOW_DAYS` | `30` | Change to 90, 180, etc. for longer history |
| `N_EMP` | `250` | Number of synthetic employees |


# 1. Create & activate a virtual environment (optional)
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

# 2. Install deps
```bash
pip install pandas numpy
```
# 3. Run the generator

```bash
python Generate\_data.py
```

Successful run prints:

```
Done.  Generated:
• employees.csv
• permissions.csv
• role\_permission\_baseline.csv
• permission\_assignments.csv
• auth\_events.csv

(all files saved in ./output)
```

---

## 📑 Output Files & Use‑Case Mapping
| CSV | Columns (examples) | Purpose | Use‑case attribute satisfied             |
|-----|--------------------|---------|------------------------------------------|
| **employees.csv** | `emp_no`, `manager_emp_no`, `role_title` | Org chart & roles | manager⇢directs; role alignment          |
| **permissions.csv** | `Action`, `service_name`, `access_level`, `highSensitivity` | Canonical permission catalogue | Permission sensitivity & service context |
| **role_permission_baseline.csv** | `role_title`, `Action` | Golden entitlements per role | relevance to role; peer baseline         |
| **permission_assignments.csv** | `emp_no`, `role_title`, `Action` | Actual entitlements | raw ingestion feed                       |
| **auth_events.csv** | `timestamp`, `emp_no`, `permission` | Usage history | frequency / dormant access               |
| **risk_features.csv** | `off_baseline`, `peer_outlier`, `dormant`, `high_sensitivity`, `risk_score` | Final feature set | manager‑report inputs                    |


### Feature Engineering Cheatsheet

| Feature              | SQL / pandas hint                                                                                                                                |
| -------------------- |--------------------------------------------------------------------------------------------------------------------------------------------------|
| **Off‑baseline**     | `LEFT JOIN permission_assignments ON role_permission_baseline` → `WHERE baseline.Action IS NULL`                                                 |
| **Peer‑outlier**     | `% peers who also hold the Action` **÷** `total peers` < **0.20** (permission is held by fewer than 20% of employees with the same `role_title`) |
| **Dormant**          | `MAX(timestamp) < NOW() - INTERVAL '90 days'`                                                                                                    |
| **High sensitivity** | `permissions.highSensitivity = TRUE`                                                                                                             |

Combine these into a numeric **risk\_score** and produce per‑manager reports:

* **Low‑risk** = common, baseline, recently used, low sensitivity.
* **High‑risk** = any high‑sensitivity **OR** off‑baseline **OR** dormant **OR** peer‑outlier.

---

## 🔗 External Data Licence

`iam_definition.json` comes from the [iam‑dataset](https://github.com/iann0036/iam-dataset) project (MIT License).

All synthetic data generated by `Generate_data.py` is **CC‑Zero** — use it for any purpose.

---

## ✨ Next Steps

1. For extra realism, rerun the generator with a larger `N_EMP` or longer event window.

Happy camping! 🎉
