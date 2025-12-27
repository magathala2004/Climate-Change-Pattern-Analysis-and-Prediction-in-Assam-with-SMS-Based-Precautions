

from flask import Flask, render_template, request, jsonify
import sqlite3
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


app = Flask(__name__)


# Base folder that contains: forecasts/rainfall, forecasts/humidity, forecasts/temp
FORECAST_BASE_DIR = os.path.join(os.path.dirname(__file__), "forecasts")

DB_PATH = "climate_users.db"

# Email config (YOUR real values here)
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "assamclimatealerts@gmail.com"         
SMTP_PASS = "atyl maqf gmyi gojm"                   

PRODUCT_LINKS = {
    "rain": (
        "Raincoat: https://www.amazon.in/s?k=raincoat\n"
        "Umbrella: https://www.flipkart.com/search?q=umbrella\n"
        "Gumboots: https://www.amazon.in/s?k=gumboots\n"
        "Tarpaulin / farm cover: https://www.amazon.in/s?k=tarpaulin"
    ),
    "heat": (
        "ORS / electrolyte: https://www.apollopharmacy.in/search?kw=ORS\n"
        "Cooling scarf / cap: https://www.amazon.in/s?k=cooling+scarf\n"
        "Sunglasses / sun glasses: https://www.amazon.in/s?k=sunglasses"
    ),
    "medicine": (
        "Paracetamol: https://www.medplusmart.com/search?keyword=paracetamol\n"
        "Cough syrup: https://www.apollopharmacy.in/search?kw=cough\n"
        "First aid kit: https://www.amazon.in/s?k=first+aid+kit"
    ),
    # NEW: cold-weather shopping links
    "cold": (
        "Sweaters: https://www.amazon.in/s?k=sweater+men+women\n"
        "Winter Jackets: https://www.flipkart.com/search?q=winter+jackets\n"
        "Mufflers / Scarves: https://www.amazon.in/s?k=muffler+scarf\n"
        "Hand Gloves: https://www.amazon.in/s?k=winter+gloves"
    ),
}

# -------------------------------
# DB SETUP
# -------------------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) Users table (already there)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        district TEXT NOT NULL,
        rain_threshold REAL DEFAULT 70,
        tmax_threshold REAL DEFAULT 35,
        humidity_threshold REAL DEFAULT 80
    )
    """)

    # 2) Historical daily climate data (2014–2025)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS historical_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        district TEXT NOT NULL,
        date DATE NOT NULL,
        tmax_c REAL,
        tmin_c REAL,
        rain_mm REAL,
        humidity_morning REAL,
        humidity_evening REAL,
        humidity_avg REAL
    )
    """)

    # Speed up queries: one row per (district, date)
    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_hist_district_date
    ON historical_daily(district, date)
    """)

    
    conn.commit()
    conn.close()


init_db()

# -------------------------------
# HELPERS
# -------------------------------







def load_forecast_for_district(district_name: str) -> pd.DataFrame | None:
    """
    Reads 7-day forecast for one district by merging rainfall, humidity and temp CSVs.
    Returns a DataFrame with at least:
      date, pred_rain_mm, rain_possibility_percent,
      pred_humidity_avg_pct, pred_tmax_c, pred_tmin_c
    or None if any file is missing.
    """
    safe_name = district_name.replace(" ", "_").replace("/", "_")

    rain_path = os.path.join(FORECAST_BASE_DIR, "rainfall", f"{safe_name}_next7.csv")
    hum_path  = os.path.join(FORECAST_BASE_DIR, "humidity", f"{safe_name}_next7_humidity.csv")
    temp_path = os.path.join(FORECAST_BASE_DIR, "temp",     f"{safe_name}_next7_temp.csv")

    if not (os.path.exists(rain_path) and os.path.exists(hum_path) and os.path.exists(temp_path)):
        print(f"[ALERT] Missing forecast file(s) for {district_name}")
        return None

    df_rain = pd.read_csv(rain_path)
    df_hum  = pd.read_csv(hum_path)
    df_temp = pd.read_csv(temp_path)

    # normalise date column
    for df in (df_rain, df_hum, df_temp):
        df["date"] = pd.to_datetime(df["date"])

    df = df_rain.merge(df_hum, on=["district", "date"], how="inner") \
                .merge(df_temp, on=["district", "date"], how="inner")

    # Rename to consistent column names if needed
    if "pred_rain_mm" not in df.columns and "rain_mm" in df.columns:
        df = df.rename(columns={"rain_mm": "pred_rain_mm"})
    if "rain_possibility_percent" not in df.columns and "rain_chance_percent" in df.columns:
        df = df.rename(columns={"rain_chance_percent": "rain_possibility_percent"})
    if "pred_humidity_avg_pct" not in df.columns and "humidity_avg_pct" in df.columns:
        df = df.rename(columns={"humidity_avg_pct": "pred_humidity_avg_pct"})
    if "pred_tmax_c" not in df.columns and "tmax_c" in df.columns:
        df = df.rename(columns={"tmax_c": "pred_tmax_c"})
    if "pred_tmin_c" not in df.columns and "tmin_c" in df.columns:
        df = df.rename(columns={"tmin_c": "pred_tmin_c"})

    return df


def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def send_sms(identifier: str, text: str):
    """
    Placeholder SMS sender.
    For now it just prints to console. 'identifier' can be phone or email for demo.
    Later, replace with real SMS API (Twilio, etc.).
    """
    print("===================================")
    print(f"[SMS to {identifier}]")
    print(text)
    print("===================================")


def compute_forecast_stats(df: pd.DataFrame, user_row) -> dict:
    """Compute derived values used for alerts."""
    rain_probs = df["rain_possibility_percent"].astype(float)
    rain_mm    = df["pred_rain_mm"].astype(float)
    tmax_vals  = df["pred_tmax_c"].astype(float)
    tmin_vals  = df["pred_tmin_c"].astype(float)
    hum_avg    = df["pred_humidity_avg_pct"].astype(float)

    max_rain_prob = float(rain_probs.max())
    max_rain_mm   = float(rain_mm.max())
    max_tmax      = float(tmax_vals.max())
    min_tmin      = float(tmin_vals.min())
    avg_humidity  = float(hum_avg.mean())

    # dates where rain prob crosses user threshold
    extreme_rain_dates = df.loc[
        rain_probs >= float(user_row["rain_threshold"]),
        "date"
    ].dt.strftime("%d %b").tolist()

    return {
        "max_rain_prob": max_rain_prob,
        "max_rain_mm": max_rain_mm,
        "max_tmax": max_tmax,
        "min_tmin": min_tmin,
        "avg_humidity": avg_humidity,
        "extreme_rain_dates": extreme_rain_dates,
    }


def build_7day_block(df: pd.DataFrame) -> str:
    """
    Build a 7-day multiline text with:
    DD Mon: 80% rain, 35.2mm, Tmax 32°, Tmin 24°, Hum 88%
    """
    df_sorted = df.sort_values("date").head(7)
    lines = []
    for _, r in df_sorted.iterrows():
        d = r["date"]
        if not isinstance(d, datetime):
            d = pd.to_datetime(d)
        d_str = d.strftime("%d %b")
        rain_prob = float(r.get("rain_possibility_percent", 0.0))
        rain_mm   = float(r.get("pred_rain_mm", 0.0))
        tmax      = float(r.get("pred_tmax_c", 0.0))
        tmin      = float(r.get("pred_tmin_c", 0.0))
        hum_avg   = float(r.get("pred_humidity_avg_pct", 0.0))

        line = (
            f"{d_str}: "
            f"{rain_prob:.0f}% rain, "
            f"{rain_mm:.1f}mm, "
            f"Tmax {tmax:.0f}°, "
            f"Tmin {tmin:.0f}°, "
            f"Hum {hum_avg:.0f}%"
        )
        lines.append(line)

    return "\n".join(lines)


def build_alert_email(user_row, stats: dict) -> tuple[str, str, bool]:
    """
    Returns (subject, body, should_send).
    should_send=False -> no extreme conditions, skip email.
    """
    district = user_row["district"]
    max_rain_prob = stats["max_rain_prob"]
    max_rain_mm   = stats["max_rain_mm"]
    max_tmax      = stats["max_tmax"]
    min_tmin      = stats["min_tmin"]
    avg_humidity  = stats["avg_humidity"]
    dates_str = ", ".join(stats["extreme_rain_dates"]) or "next 7 days"

    rain_extreme = max_rain_prob >= float(user_row["rain_threshold"])
    heat_extreme = max_tmax      >= float(user_row["tmax_threshold"])
    hum_extreme  = avg_humidity  >= float(user_row["humidity_threshold"])
    # NEW: very cold condition if minimum Tmin <= 10°C
    cold_extreme = min_tmin <= 10.0

    # Nothing crossed → no alert
    if not (rain_extreme or heat_extreme or hum_extreme or cold_extreme):
        return "", "", False

    # Combined extreme (rain + heat/humidity)
    if rain_extreme and (heat_extreme or hum_extreme):
        subject = f"[Climate Alert] Extreme rain & heat expected in {district}"
        body = f"""Dear user,

This is an automated climate alert for {district}.

Our 7-day forecast shows both heavy rain and high temperature:

• Maximum rain chance: {max_rain_prob:.1f}% (up to {max_rain_mm:.1f} mm)
• Maximum temperature (Tmax): {max_tmax:.1f}°C
• Average humidity: {avg_humidity:.1f}%

Precautions:
• Plan farm work around the intense rain hours.
• Protect seeds, fertilizer and tools from water-logging.
• Move livestock to safer / higher areas during heavy rain days.
• Avoid direct sun in peak hours (11 AM – 3 PM).
• Drink plenty of water / ORS and avoid very oily food.
• Keep basic first-aid and medicines as advised by a doctor.

Useful items (you may use local shops or online platforms):
{PRODUCT_LINKS['rain']}

Heat & health related items:
{PRODUCT_LINKS['heat']}
{PRODUCT_LINKS['medicine']}

Stay safe,
Assam Climate Predictor
"""
        return subject, body, True

    # Only heavy rain
    if rain_extreme:
        subject = f"[Climate Alert] Heavy rain expected in {district}"
        body = f"""Dear user,

This is an automated climate alert for {district}.

High rainfall is expected on: {dates_str}
Maximum rain chance: {max_rain_prob:.1f}%
Estimated rainfall up to: {max_rain_mm:.1f} mm.

Precautions:
• Avoid low-lying and river-bank areas during heavy showers.
• Farmers: move livestock, seed and equipment to higher ground.
• Store grains and fertilizer in dry, covered places.
• Keep drinking water, dry food, torch and power bank ready.
• Do not cross flooded roads or fast-moving water.

Useful rain protection items:
{PRODUCT_LINKS['rain']}

Basic medicines & first-aid (always follow doctor's advice):
{PRODUCT_LINKS['medicine']}

Stay safe,
Assam Climate Predictor
"""
        return subject, body, True

    # NEW: Only cold extreme (very low Tmin)
    if cold_extreme:
        subject = f"[Climate Alert] Very cold weather expected in {district}"
        body = f"""Dear user,

This is an automated climate alert for {district}.

The next 7 days show very low night temperatures:

• Minimum temperature (Tmin): {min_tmin:.1f}°C
• Average humidity: {avg_humidity:.1f}%

Precautions:
• Use sweaters, jackets, mufflers and gloves, especially at night and early morning.
• Elderly people, children and heart patients must stay warm indoors.
• Avoid cold water; use warm drinking water where possible.
• Cattle should be given dry bedding and sheds should be protected from cold wind.

Helpful winter supplies:
{PRODUCT_LINKS['cold']}

Basic medicines & first-aid (always follow doctor's advice):
{PRODUCT_LINKS['medicine']}

Stay safe,
Assam Climate Predictor
"""
        return subject, body, True

    # Only heat/humidity extreme
    subject = f"[Climate Alert] High heat / humidity in {district}"
    body = f"""Dear user,

This is an automated climate alert for {district}.

The next 7 days are expected to be very hot and humid:

• Maximum temperature (Tmax): {max_tmax:.1f}°C
• Average humidity: {avg_humidity:.1f}%

Precautions:
• Avoid direct sunlight between 11 AM and 3 PM.
• Drink plenty of water / ORS; avoid heavy, oily food.
• Farmers & outdoor workers: work in early morning or late evening, use cap/umbrella and take frequent shade breaks.
• Children, pregnant women and elderly should stay indoors as much as possible.
• For dizziness, fainting or severe headache, contact a doctor immediately.

Helpful supplies (from local shops or online apps):
{PRODUCT_LINKS['heat']}
{PRODUCT_LINKS['medicine']}

Stay safe,
Assam Climate Predictor
"""
    return subject, body, True


def build_sms_text(user_row, df: pd.DataFrame, stats: dict) -> tuple[str, bool]:
    """
    Build a compact SMS text including 7-day forecast summary.
    Returns (sms_text, should_send).
    """
    district = user_row["district"]
    max_rain_prob = stats["max_rain_prob"]
    max_rain_mm   = stats["max_rain_mm"]
    max_tmax      = stats["max_tmax"]
    min_tmin      = stats["min_tmin"]
    avg_humidity  = stats["avg_humidity"]

    rain_extreme = max_rain_prob >= float(user_row["rain_threshold"])
    heat_extreme = max_tmax      >= float(user_row["tmax_threshold"])
    hum_extreme  = avg_humidity  >= float(user_row["humidity_threshold"])
    cold_extreme = min_tmin      <= 10.0

    # If nothing extreme, no SMS needed
    if not (rain_extreme or heat_extreme or hum_extreme or cold_extreme):
        return "", False

    # 7-day compact lines
    seven_block = build_7day_block(df)

    if rain_extreme and (heat_extreme or hum_extreme):
        sms = (
            f"[Alert {district}] Heavy rain & heat.\n"
            f"{seven_block}\n"
            "Tips: avoid flood-prone areas, protect crops/livestock, avoid sun 11–3, drink ORS/water."
        )
    elif rain_extreme:
        sms = (
            f"[Alert {district}] Heavy rain expected.\n"
            f"{seven_block}\n"
            "Tips: avoid low-lying areas, move animals/seeds to higher ground, keep dry food & torch ready."
        )
    elif cold_extreme:
        sms = (
            f"[Alert {district}] Very cold weather.\n"
            f"{seven_block}\n"
            "Tips: wear sweaters/jackets/mufflers, keep children & elders warm, protect cattle from cold winds."
        )
    else:  # only heat/humidity
        sms = (
            f"[Alert {district}] High heat/humidity.\n"
            f"{seven_block}\n"
            "Tips: avoid sun 11–3, drink water/ORS, work early morning/evening, keep children & elders indoors."
        )

    return sms, True


def send_alerts():
    """Check all registered users and send email alerts if thresholds are crossed."""
    print("[ALERT] Running send_alerts()")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT id, email, district,
               rain_threshold, tmax_threshold, humidity_threshold
        FROM users
    """)
    users = cur.fetchall()

    alerts_sent = 0

    for user in users:
        district = user["district"]
        email = user["email"]

        df = load_forecast_for_district(district)
        if df is None or df.empty:
            print(f"[ALERT] No forecast data for {district}, skipping {email}")
            continue

        stats = compute_forecast_stats(df, user)
        subject, body, should_send = build_alert_email(user, stats)

        if not should_send:
            print(f"[ALERT] No extreme event for {district} -> no mail/SMS to {email}")
            continue

        # ---- append 7-day detailed forecast block to EMAIL body ----
        daily_block = build_7day_block(df)
        body = body + "\n\n7-day detailed forecast (rain, temp, humidity):\n" + daily_block

        # ---- EMAIL ----
        try:
            send_email(email, subject, body)
            alerts_sent += 1
            print(f"[ALERT] Email sent to {email} for {district}")
        except Exception as e:
            print(f"[ALERT] Failed to send email to {email}: {e}")

        # ---- SMS (demo: using email as identifier) ----
        sms_text, sms_should_send = build_sms_text(user, df, stats)
        if sms_should_send:
            try:
                # For now we send to 'email' as identifier.
                # Later, when you add phone column, replace with user["phone"].
                send_sms(email, sms_text)
                print(f"[ALERT] SMS prepared for {email} ({district})")
            except Exception as e:
                print(f"[ALERT] Failed to send SMS for {email}: {e}")

    conn.close()
    print(f"[ALERT] Done. Total alerts sent: {alerts_sent}")


# -------------------------------
# ROUTES
# -------------------------------

@app.route("/")
def index():
    # Build district list from rainfall forecasts
    rain_dir = os.path.join(FORECAST_BASE_DIR, "rainfall")
    districts = []
    if os.path.exists(rain_dir):
        for fname in os.listdir(rain_dir):
            if fname.endswith("_next7.csv"):
                name = fname.replace("_next7.csv", "").replace("_", " ")
                districts.append(name)
    districts = sorted(districts)
    return render_template("index.html", districts=districts)


@app.route("/api/forecast")
def api_forecast():
    district = request.args.get("district")
    if not district:
        return jsonify({"error": "district is required"}), 400

    df = load_forecast_for_district(district)
    if df is None:
        return jsonify({"error": "forecast not found for district"}), 404

    records = []
    for _, row in df.iterrows():
        records.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "pred_rain_mm": float(row.get("pred_rain_mm", 0.0)),
            "rain_possibility_percent": float(row.get("rain_possibility_percent", 0.0)),
            "pred_humidity_morning_pct": float(row.get("pred_humidity_morning_pct", 0.0)),
            "pred_humidity_evening_pct": float(row.get("pred_humidity_evening_pct", 0.0)),
            "pred_humidity_avg_pct": float(row.get("pred_humidity_avg_pct", 0.0)),
            "pred_tmax_c": float(row.get("pred_tmax_c", 0.0)),
            "pred_tmin_c": float(row.get("pred_tmin_c", 0.0)),
        })

    return jsonify({
        "district": district,
        "forecast": records
    })


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json
    email = data.get("email")
    district = data.get("district")
    rain_threshold = data.get("rain_threshold", 70)
    tmax_threshold = data.get("tmax_threshold", 35)
    humidity_threshold = data.get("humidity_threshold", 80)

    if not email or not district:
        return jsonify({"error": "email and district are required"}), 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (email, district, rain_threshold, tmax_threshold, humidity_threshold) VALUES (?,?,?,?,?)",
        (email, district, float(rain_threshold), float(tmax_threshold), float(humidity_threshold))
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "registered successfully"})


# -------------------------------
# MAIN ENTRY POINT
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)
