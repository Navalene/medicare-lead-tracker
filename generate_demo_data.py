"""Create demo_leads.csv with fictional contacts for the portfolio demo.

No real people are used. Phone numbers are in the 555-0100 to 555-0199
range, which is reserved for fictional use.

Birthdates are generated relative to today, so the alerts and birthday
sections always have something to show.

Usage:
    python generate_demo_data.py
"""

import calendar
import csv
import os
import random
from datetime import date, timedelta

FIRST_NAMES = [
    "Avery", "Dolores", "Harold", "Gloria", "Walter", "Irene", "Ramon",
    "Yolanda", "Clarence", "Bernice", "Leon", "Marisol", "Theodore", "Hazel",
    "Ernesto", "Lorraine", "Vernon", "Ophelia", "Rosalind", "Desmond",
]
LAST_NAMES = [
    "Hartley", "Okafor", "Brennan", "Quintero", "Lindqvist", "Abernathy",
    "Delacroix", "Fairbanks", "Valdivia", "Ashworth", "Pemberton", "Castellanos",
    "Whitlock", "Nakamura", "Oduya", "Marchetti", "Holloway", "Serrano",
]
AREA_CODES = ["212", "347", "646", "718", "917", "929"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "demo_leads.csv")


def safe_date(year, month, day):
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def born_to_turn_65_in(days, today):
    """Birthdate for someone who turns 65 `days` from today."""
    target = today + timedelta(days=days)
    return safe_date(target.year - 65, target.month, target.day)


def fake_phone(rng):
    return f"{rng.choice(AREA_CODES)}-555-01{rng.randint(0, 99):02d}"


def build_rows(today, rng, total=40):
    rows = []
    names = rng.sample([f"{f} {l}" for f in FIRST_NAMES for l in LAST_NAMES], total)

    for i, name in enumerate(names):
        if i < 6:      # turning 65 within the 90-day alert window
            birthdate, status = born_to_turn_65_in(rng.randint(0, 90), today), "Lead"
        elif i < 14:   # turning 65 later this year
            birthdate, status = born_to_turn_65_in(rng.randint(91, 365), today), "Lead"
        elif i == 14:  # a client with a birthday today
            birthdate, status = safe_date(today.year - 72, today.month, today.day), "Client"
        else:          # everyone else: ages 55 to 85
            age_days = rng.randint(55 * 365, 85 * 365)
            birthdate = today - timedelta(days=age_days)
            status = "Client" if rng.random() < 0.55 else "Lead"

        rows.append({
            "Name": name,
            "Phone": fake_phone(rng),
            "Birthdate": birthdate.isoformat(),
            "Status": status,
        })

    rng.shuffle(rows)
    return rows


def main():
    rows = build_rows(date.today(), random.Random(42))
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Name", "Phone", "Birthdate", "Status"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} fictional contacts to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
