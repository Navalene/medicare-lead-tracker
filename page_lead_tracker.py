"""Medicare Lead Tracker (portfolio demo).

A Streamlit dashboard for tracking leads approaching Medicare eligibility,
running a needs assessment, and ranking carriers by how well they fit.

All data in this version is synthetic. Run `python generate_demo_data.py`
to create demo_leads.csv before starting the app.
"""

import calendar
import os
from datetime import date

import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "demo_leads.csv")
COLUMNS = ["Name", "Phone", "Birthdate", "Status"]
STATUSES = ["Lead", "Client"]
ALERT_WINDOW_DAYS = 90

# What the client can ask for -> label shown in the app.
PRIORITIES = {
    "dental": "Dental",
    "vision": "Vision",
    "hearing": "Hearing",
    "rx": "Prescription drugs",
    "otc": "OTC / grocery allowance",
    "transportation": "Transportation",
    "low_copay": "Low specialist copays",
    "mltc": "Long-term / home care",
}

# Fictional carriers for the demo. "dsnp" = offers Dual Special Needs Plans.
CARRIERS = {
    "Northstar Health":     {"dsnp": True,  "benefits": {"dental", "otc", "transportation", "low_copay", "mltc"}},
    "Harbor Care Plans":    {"dsnp": True,  "benefits": {"vision", "hearing", "otc", "rx"}},
    "Evergreen Medicare":   {"dsnp": False, "benefits": {"dental", "vision", "rx", "low_copay"}},
    "Summit Senior Health": {"dsnp": True,  "benefits": {"hearing", "transportation", "rx", "mltc"}},
    "Bridgeway Health":     {"dsnp": False, "benefits": {"otc", "dental", "vision"}},
    "Lakeside Advantage":   {"dsnp": True,  "benefits": {"low_copay", "rx", "transportation", "dental"}},
}


# ---------- Helpers ----------

def safe_date(year, month, day):
    """Build a date, moving Feb 29 to Feb 28 in non-leap years."""
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def turning_65_date(birthdate):
    return safe_date(birthdate.year + 65, birthdate.month, birthdate.day)


def next_birthday(birthdate, today):
    bday = safe_date(today.year, birthdate.month, birthdate.day)
    if bday < today:
        bday = safe_date(today.year + 1, birthdate.month, birthdate.day)
    return bday


def format_phone(raw):
    """Return the phone as 555-555-5555, or None if it isn't 10 digits."""
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    if len(digits) != 10:
        return None
    return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"


def load_leads():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(DATA_FILE, dtype={"Phone": str})
    df = df.reindex(columns=COLUMNS)  # drops stray columns, adds missing ones
    df["Status"] = df["Status"].fillna("Lead")
    df["Phone"] = df["Phone"].fillna("")
    df["Birthdate"] = pd.to_datetime(df["Birthdate"], errors="coerce")
    return df.dropna(subset=["Name", "Birthdate"]).reset_index(drop=True)


def save_leads(df):
    out = df[COLUMNS].copy()
    out["Birthdate"] = pd.to_datetime(out["Birthdate"]).dt.strftime("%Y-%m-%d")
    out.to_csv(DATA_FILE, index=False)


def rank_carriers(selected, is_dual, wanted):
    """Score each carrier by how many of the client's priorities it covers."""
    rows = []
    for name in selected:
        info = CARRIERS[name]
        if is_dual and not info["dsnp"]:
            continue  # dual-eligible clients go to D-SNP carriers only
        covered = wanted & info["benefits"]
        missing = wanted - info["benefits"]
        rows.append({
            "Carrier": name,
            "Matches": f"{len(covered)} / {len(wanted)}",
            "Score": len(covered),
            "Covers": ", ".join(PRIORITIES[k] for k in sorted(covered)) or "—",
            "Missing": ", ".join(PRIORITIES[k] for k in sorted(missing)) or "—",
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("Score", ascending=False).drop(columns="Score")


# ---------- Page ----------

st.set_page_config(page_title="Medicare Lead Tracker", page_icon="🧮", layout="wide")
st.title("🧮 Medicare Lead Tracker")
st.caption("Portfolio demo. All names, phone numbers and carriers are fictional.")

today = date.today()
leads = load_leads()
leads["Turning 65"] = [turning_65_date(d.date()) for d in leads["Birthdate"]]
leads["Days to 65"] = [(d - today).days for d in leads["Turning 65"]]

# --- Dashboard ---
in_window = leads[leads["Days to 65"].between(0, ALERT_WINDOW_DAYS)]
client_count = int((leads["Status"] == "Client").sum())
conversion = client_count / len(leads) if len(leads) else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total contacts", len(leads))
m2.metric("Clients", client_count)
m3.metric(f"Turning 65 in {ALERT_WINDOW_DAYS} days", len(in_window))
m4.metric("Lead → client rate", f"{conversion:.0%}")

upcoming = leads[leads["Days to 65"].between(0, 365)]
if not upcoming.empty:
    st.markdown("**Contacts turning 65, next 12 months**")
    by_month = upcoming["Turning 65"].map(lambda d: d.strftime("%Y-%m")).value_counts().sort_index()
    st.bar_chart(by_month, x_label="Month", y_label="Contacts")

# --- Add a contact ---
st.divider()
st.subheader("📝 Add a contact")
with st.form("lead_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    name = c1.text_input("Full name")
    phone = c2.text_input("Phone number")
    birthdate = c1.date_input(
        "Birthdate",
        value=date(today.year - 64, 1, 1),
        min_value=date(1920, 1, 1),
        max_value=today,
        format="MM/DD/YYYY",
    )
    status = c2.selectbox("Status", STATUSES)

    if st.form_submit_button("Save"):
        clean_phone = format_phone(phone)
        if not name.strip():
            st.error("Please enter a name.")
        elif clean_phone is None:
            st.error("Phone number must have 10 digits.")
        else:
            new_row = pd.DataFrame([{
                "Name": name.strip(),
                "Phone": clean_phone,
                "Birthdate": birthdate,
                "Status": status,
            }])
            save_leads(pd.concat([leads[COLUMNS], new_row], ignore_index=True))
            st.toast(f"Saved {name.strip()}")
            st.rerun()

# --- Alerts ---
st.divider()
st.subheader(f"🚨 Turning 65 in the next {ALERT_WINDOW_DAYS} days")
if in_window.empty:
    st.info("No contacts are in their enrollment window right now.")
else:
    alerts = in_window.sort_values("Days to 65")[["Name", "Phone", "Status", "Turning 65", "Days to 65"]].copy()
    alerts["Turning 65"] = alerts["Turning 65"].map(lambda d: d.strftime("%B %d, %Y"))
    st.warning("These contacts are entering their Initial Enrollment Period. Reach out first.")
    st.dataframe(alerts, hide_index=True, width="stretch")

# --- Needs assessment ---
st.divider()
st.subheader("🔍 Needs assessment & carrier match")

dual_choice = st.radio(
    "Is the prospect dual-eligible? (Medicaid / Extra Help / MSP)",
    ["No / Unknown", "Yes, full Medicaid", "Yes, partial (MSP / Extra Help only)"],
    horizontal=True,
)
is_dual = dual_choice.startswith("Yes")

st.markdown("**Client priorities**")
priority_cols = st.columns(4)
wanted = {
    key for i, (key, label) in enumerate(PRIORITIES.items())
    if priority_cols[i % 4].checkbox(label, key=f"want_{key}")
}

selected_carriers = st.multiselect(
    "Carriers available in the client's area",
    list(CARRIERS),
    default=list(CARRIERS),
)

if st.button("Match carriers"):
    if is_dual:
        st.success("**Pathway:** Dual Special Needs Plan (D-SNP). Showing D-SNP carriers only.")
    else:
        st.info("**Pathway:** $0-premium Medicare Advantage (MAPD).")

    if not wanted:
        st.caption("Tip: tick a few priorities to rank the carriers.")

    ranked = rank_carriers(selected_carriers, is_dual, wanted)
    if ranked.empty:
        st.error("No selected carriers fit this profile.")
    else:
        st.dataframe(ranked, hide_index=True, width="stretch")

    if "mltc" in wanted:
        st.warning("Home care needed: confirm the plan coordinates with a Managed Long-Term Care plan.")

# --- Client birthdays ---
st.divider()
st.subheader("🎂 Upcoming client birthdays")
clients = leads[leads["Status"] == "Client"]
if clients.empty:
    st.info("No current clients.")
else:
    rows = []
    for _, row in clients.iterrows():
        bdate = row["Birthdate"].date()
        bday = next_birthday(bdate, today)
        rows.append({
            "Name": row["Name"],
            "Phone": row["Phone"],
            "Next birthday": bday.strftime("%B %d, %Y"),
            "Turning": bday.year - bdate.year,
            "Days away": (bday - today).days,
        })
    birthdays = pd.DataFrame(rows).sort_values("Days away")

    for _, r in birthdays[birthdays["Days away"] == 0].iterrows():
        st.success(f"📞 Birthday call today: **{r['Name']}** ({r['Phone']}), turning {r['Turning']}")

    st.dataframe(birthdays, hide_index=True, width="stretch")

# --- Roster editor ---
st.divider()
st.subheader("🗂️ All contacts")
st.caption("Double-click a cell to edit. To remove someone, tick their row, press Delete, then Save changes.")

edited = st.data_editor(
    leads[COLUMNS],
    num_rows="dynamic",
    width="stretch",
    column_config={
        "Birthdate": st.column_config.DateColumn("Birthdate", format="MM/DD/YYYY"),
        "Status": st.column_config.SelectboxColumn("Status", options=STATUSES),
    },
    key="leads_editor",
)

if st.button("Save changes"):
    cleaned = edited.dropna(subset=["Name", "Birthdate"]).copy()
    cleaned["Status"] = cleaned["Status"].fillna("Lead")
    cleaned["Phone"] = cleaned["Phone"].fillna("")
    save_leads(cleaned)
    st.toast("Changes saved")
    st.rerun()
