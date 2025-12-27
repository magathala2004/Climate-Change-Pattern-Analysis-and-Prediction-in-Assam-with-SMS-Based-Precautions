import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "climate_users.db")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS forecast_daily")
cur.execute("DROP INDEX IF EXISTS idx_forecast_key")

conn.commit()
conn.close()

print("Deleted forecast_daily table and its index successfully.")
