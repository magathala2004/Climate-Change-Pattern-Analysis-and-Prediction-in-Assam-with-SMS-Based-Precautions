import sqlite3
import pandas as pd

DB_PATH = "climate_users.db"
CSV_PATH = r"E:\climate_app_mp\data\assam_daily_all_years_date_fixed.csv"
 # adjust path if needed

conn = sqlite3.connect(DB_PATH)

# Read CSV
df = pd.read_csv(CSV_PATH)
df["date"] = pd.to_datetime(df["date"], dayfirst=True)

# Keep only necessary columns
cols = [
    "district", "date",
    "tmax_c", "tmin_c", "rain_mm",
    "humidity_morning", "humidity_evening", "humidity_avg"
]
df = df[cols]

# Drop duplicates just in case (same district+date)
df = df.drop_duplicates(subset=["district", "date"])

# Insert into DB
df.to_sql("historical_daily", conn, if_exists="append", index=False)

conn.close()
print("Imported", len(df), "rows into historical_daily")
