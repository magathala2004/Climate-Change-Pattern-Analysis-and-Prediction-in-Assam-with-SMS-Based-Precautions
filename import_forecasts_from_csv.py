import os
import sqlite3
from datetime import datetime

import pandas as pd

# ---- paths ----
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "climate_users.db")
FORECAST_BASE = os.path.join(BASE_DIR, "forecasts")

RAIN_DIR = os.path.join(FORECAST_BASE, "rainfall")
HUM_DIR  = os.path.join(FORECAST_BASE, "humidity")
TEMP_DIR = os.path.join(FORECAST_BASE, "temp")


# -------------------------------------------------
# 1) Create tables if they don't exist
# -------------------------------------------------
def init_tables(conn):
    cur = conn.cursor()

    # a) rainfall_forecast
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS rainfall_forecast (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            district TEXT NOT NULL,
            date TEXT NOT NULL,                -- YYYY-MM-DD
            pred_rain_norm REAL,
            pred_rain_mm REAL,
            rain_possibility_percent REAL,
            model_type TEXT NOT NULL,          -- e.g. 'rain_lstm_7day'
            horizon INTEGER NOT NULL,          -- 7
            created_at TEXT NOT NULL           -- ISO timestamp (UTC)
        )
        """
    )

    # b) humidity_forecast
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS humidity_forecast (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            district TEXT NOT NULL,
            date TEXT NOT NULL,                -- YYYY-MM-DD
            pred_humidity_morning_norm REAL,
            pred_humidity_evening_norm REAL,
            pred_humidity_avg_norm REAL,
            pred_humidity_morning_pct REAL,
            pred_humidity_evening_pct REAL,
            pred_humidity_avg_pct REAL,
            model_type TEXT NOT NULL,          -- 'humidity_lstm_7day'
            horizon INTEGER NOT NULL,          -- 7
            created_at TEXT NOT NULL
        )
        """
    )

    # c) temp_forecast
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS temp_forecast (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            district TEXT NOT NULL,
            date TEXT NOT NULL,                -- YYYY-MM-DD
            pred_tmax_c REAL,
            pred_tmin_c REAL,
            model_type TEXT NOT NULL,          -- 'temp_lstm_7day'
            horizon INTEGER NOT NULL,          -- 7
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()


# -------------------------------------------------
# Helper: import one CSV folder into one table
# -------------------------------------------------
def import_rainfall(conn):
    if not os.path.isdir(RAIN_DIR):
        print(f"[RAIN] Folder not found: {RAIN_DIR}")
        return

    cur = conn.cursor()
    created_ts = datetime.utcnow().isoformat(timespec="seconds")

    files = [f for f in os.listdir(RAIN_DIR) if f.endswith(".csv")]
    if not files:
        print("[RAIN] No CSV files found.")
        return

    for fname in files:
        path = os.path.join(RAIN_DIR, fname)
        df = pd.read_csv(path)

        if "date" not in df.columns:
            print(f"[RAIN] Skipping {fname}: date column missing")
            continue

        # normalise date format
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        # detect district from data (preferred) or filename
        if "district" in df.columns and not df["district"].isna().all():
            district = str(df["district"].iloc[0])
        else:
            district = fname.replace("_next7.csv", "").replace("_", " ")

        print(f"[RAIN] Importing {fname} for district '{district}'")

        # avoid duplicates for that district & model
        cur.execute(
            "DELETE FROM rainfall_forecast WHERE district = ? AND model_type = ?",
            (district, "rain_lstm_7day"),
        )

        for _, r in df.iterrows():
            cur.execute(
                """
                INSERT INTO rainfall_forecast (
                    district, date,
                    pred_rain_norm, pred_rain_mm, rain_possibility_percent,
                    model_type, horizon, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    district,
                    r["date"],
                    float(r.get("pred_rain_norm", 0.0)),
                    float(r.get("pred_rain_mm", 0.0)),
                    float(r.get("rain_possibility_percent", 0.0)),
                    "rain_lstm_7day",
                    7,
                    created_ts,
                ),
            )

    conn.commit()
    print("[RAIN] Done.")


def import_humidity(conn):
    if not os.path.isdir(HUM_DIR):
        print(f"[HUM] Folder not found: {HUM_DIR}")
        return

    cur = conn.cursor()
    created_ts = datetime.utcnow().isoformat(timespec="seconds")

    files = [f for f in os.listdir(HUM_DIR) if f.endswith(".csv")]
    if not files:
        print("[HUM] No CSV files found.")
        return

    for fname in files:
        path = os.path.join(HUM_DIR, fname)
        df = pd.read_csv(path)

        if "date" not in df.columns:
            print(f"[HUM] Skipping {fname}: date column missing")
            continue

        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        if "district" in df.columns and not df["district"].isna().all():
            district = str(df["district"].iloc[0])
        else:
            district = fname.replace("_next7_humidity.csv", "").replace("_", " ")

        print(f"[HUM] Importing {fname} for district '{district}'")

        cur.execute(
            "DELETE FROM humidity_forecast WHERE district = ? AND model_type = ?",
            (district, "humidity_lstm_7day"),
        )

        for _, r in df.iterrows():
            cur.execute(
                """
                INSERT INTO humidity_forecast (
                    district, date,
                    pred_humidity_morning_norm,
                    pred_humidity_evening_norm,
                    pred_humidity_avg_norm,
                    pred_humidity_morning_pct,
                    pred_humidity_evening_pct,
                    pred_humidity_avg_pct,
                    model_type, horizon, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    district,
                    r["date"],
                    float(r.get("pred_humidity_morning_norm", 0.0)),
                    float(r.get("pred_humidity_evening_norm", 0.0)),
                    float(r.get("pred_humidity_avg_norm", 0.0)),
                    float(r.get("pred_humidity_morning_pct", 0.0)),
                    float(r.get("pred_humidity_evening_pct", 0.0)),
                    float(r.get("pred_humidity_avg_pct", 0.0)),
                    "humidity_lstm_7day",
                    7,
                    created_ts,
                ),
            )

    conn.commit()
    print("[HUM] Done.")


def import_temp(conn):
    if not os.path.isdir(TEMP_DIR):
        print(f"[TEMP] Folder not found: {TEMP_DIR}")
        return

    cur = conn.cursor()
    created_ts = datetime.utcnow().isoformat(timespec="seconds")

    files = [f for f in os.listdir(TEMP_DIR) if f.endswith(".csv")]
    if not files:
        print("[TEMP] No CSV files found.")
        return

    for fname in files:
        path = os.path.join(TEMP_DIR, fname)
        df = pd.read_csv(path)

        if "date" not in df.columns:
            print(f"[TEMP] Skipping {fname}: date column missing")
            continue

        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        if "district" in df.columns and not df["district"].isna().all():
            district = str(df["district"].iloc[0])
        else:
            district = fname.replace("_next7_temp.csv", "").replace("_", " ")

        print(f"[TEMP] Importing {fname} for district '{district}'")

        cur.execute(
            "DELETE FROM temp_forecast WHERE district = ? AND model_type = ?",
            (district, "temp_lstm_7day"),
        )

        for _, r in df.iterrows():
            cur.execute(
                """
                INSERT INTO temp_forecast (
                    district, date,
                    pred_tmax_c, pred_tmin_c,
                    model_type, horizon, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    district,
                    r["date"],
                    float(r.get("pred_tmax_c", 0.0)),
                    float(r.get("pred_tmin_c", 0.0)),
                    "temp_lstm_7day",
                    7,
                    created_ts,
                ),
            )

    conn.commit()
    print("[TEMP] Done.")


# -------------------------------------------------
# MAIN
# -------------------------------------------------
if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    init_tables(conn)

    import_rainfall(conn)
    import_humidity(conn)
    import_temp(conn)

    conn.close()
    print("All forecast CSVs imported into climate_users.db.")
