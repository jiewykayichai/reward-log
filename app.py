"""
Reward & Punishment Log
A small Streamlit app that stores its data in Google Sheets.
"""
import random
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import gspread
import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------------
# SETTINGS - edit these freely
# ------------------------------------------------------------------
TZ = ZoneInfo("Asia/Bangkok")
PRESET_AMOUNTS = [25, 50, 100]
REWARD_TYPES = ["Chinese", "Read Book", "Capcut", "Excel", "Others"]
PUNISH_TYPES = ["Youtube Slop", "Instagram Binging", "Netflix", "Pulling hair", "Others"]
REWARD_EMOJIS = ["😇", "🤑", "💵", "💰", "💹"]
PUNISH_EMOJIS = ["🥲", "😢", "😭", "💸", "📉"]
QUOTA_EMOJIS = ["👏", "🙌", "🥳", "🎉", "🎊", "🍾"]

HEADERS = ["id", "datetime", "category", "amount", "type", "comment"]
SIGN = {"Reward": 1, "Punishment": -1, "Use Quota": -1}

st.set_page_config(page_title="Reward Log", page_icon="💰", layout="centered")

# ------------------------------------------------------------------
# STYLING (layout, coloured buttons, bottom bar, confetti animation)
# ------------------------------------------------------------------
CSS = """
<style>
#MainMenu, footer, [data-testid="stHeader"], [data-testid="stToolbar"] {visibility: hidden;}
.block-container {padding-top: 1.5rem; padding-bottom: 7rem; max-width: 700px;}
/* keep columns side by side on phones */
[data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; gap: 0.5rem !important;}
[data-testid="stColumn"], [data-testid="column"] {min-width: 0 !important; flex: 1 1 0 !important; width: auto !important;}
/* quota card */
.quota-box {text-align: center; padding: 2rem 1rem; border-radius: 20px; color: white; margin-bottom: 1rem;
  background: linear-gradient(135deg, #1f8a70, #00b894); box-shadow: 0 6px 18px rgba(0,0,0,.12);}
.quota-box.negative {background: linear-gradient(135deg, #c0392b, #e17055);}
.quota-box .label {font-size: 1rem; opacity: .9;}
.quota-box .value {font-size: 3rem; font-weight: 800; line-height: 1.2;}
/* coloured action buttons */
div[class*="st-key-"][class*="punish"] button {background: #e74c3c; border: none;}
div[class*="st-key-"][class*="quota"] button {background: #0984e3; border: none;}
div[class*="st-key-"][class*="reward"] button {background: #00b894; border: none;}
div[class*="st-key-"][class*="punish"] button p,
div[class*="st-key-"][class*="quota"] button p,
div[class*="st-key-"][class*="reward"] button p {color: white !important; font-weight: 600;}
/* bottom navigation bar */
.st-key-bottomnav {position: fixed; bottom: 0; left: 0; right: 0; z-index: 1000;
  background: rgba(255,255,255,.97); border-top: 1px solid #ddd;
  padding: .5rem 1rem calc(.5rem + env(safe-area-inset-bottom));}
/* emoji confetti */
.confetti {position: fixed; left: 50%; bottom: -60px; z-index: 99999; pointer-events: none; opacity: 0;
  animation-name: emoji-pop; animation-timing-function: ease-out; animation-fill-mode: forwards;}
@keyframes emoji-pop {
  0%   {opacity: 1; transform: translate(-50%, 0) scale(.3) rotate(0deg);}
  40%  {opacity: 1; transform: translate(calc(-50% + var(--x)), var(--y)) scale(1.1) rotate(var(--r));}
  100% {opacity: 0; transform: translate(calc(-50% + var(--x) * 1.4), 15vh) scale(.9) rotate(calc(var(--r) * 2));}
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def show_confetti(emojis, n=45):
    pieces = []
    for _ in range(n):
        x = random.randint(-45, 45)
        y = random.randint(-95, -45)
        r = random.randint(-360, 360)
        size = random.randint(26, 48)
        delay = random.uniform(0, 0.6)
        dur = random.uniform(2.2, 3.6)
        pieces.append(
            f'<span class="confetti" style="--x:{x}vw;--y:{y}vh;--r:{r}deg;font-size:{size}px;'
            f'animation-duration:{dur:.2f}s;animation-delay:{delay:.2f}s">{random.choice(emojis)}</span>'
        )
    st.markdown("<div>" + "".join(pieces) + "</div>", unsafe_allow_html=True)


def fmt(x):
    x = float(x)
    return f"{'-' if x < 0 else ''}฿{abs(x):,.0f}"


# ------------------------------------------------------------------
# GOOGLE SHEETS
# ------------------------------------------------------------------
@st.cache_resource
def get_worksheet():
    gc = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
    ws = gc.open_by_url(st.secrets["sheet_url"]).sheet1
    if ws.row_values(1) != HEADERS:
        ws.update(range_name="A1:F1", values=[HEADERS])
    return ws


@st.cache_data(ttl=60)
def load_logs():
    df = pd.DataFrame(get_worksheet().get_all_records(), columns=HEADERS)
    df["id"] = df["id"].astype(str)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["comment"] = df["comment"].fillna("").astype(str)
    df["type"] = df["type"].astype(str)
    df["dt"] = pd.to_datetime(df["datetime"], errors="coerce")
    return df


def add_log(category, dt, amount, typ, comment):
    row = ["L" + uuid.uuid4().hex[:10], dt.strftime("%Y-%m-%d %H:%M"), category, int(amount), typ, comment]
    get_worksheet().append_row(row, value_input_option="RAW")
    load_logs.clear()


def update_log(log_id, category, dt, amount, typ, comment):
    ws = get_worksheet()
    cell = ws.find(log_id, in_column=1)
    if cell:
        ws.update(range_name=f"A{cell.row}:F{cell.row}",
                  values=[[log_id, dt.strftime("%Y-%m-%d %H:%M"), category, int(amount), typ, comment]])
    load_logs.clear()


def delete_log(log_id):
    ws = get_worksheet()
    cell = ws.find(log_id, in_column=1)
    if cell:
        ws.delete_rows(cell.row)
    load_logs.clear()


def current_quota(df):
    if df.empty:
        return 0.0
    return float((df["amount"] * df["category"].map(SIGN).fillna(0)).sum())


# ------------------------------------------------------------------
# NAVIGATION HELPERS
# ------------------------------------------------------------------
def go(page):
    st.session_state.page = page


def open_form(kind):
    now = datetime.now(TZ)
    st.session_state.f_date = now.date()
    st.session_state.f_time = now.time().replace(second=0, microsecond=0)
    st.session_state.f_amount = 0
    st.session_state.f_type = (REWARD_TYPES if kind == "Reward" else PUNISH_TYPES)[0]
    st.session_state.f_comment = ""
    st.session_state.page = kind


def set_amount(value):
    st.session_state.f_amount = value


def set_log_view(category):
    st.session_state.log_view = category


# ------------------------------------------------------------------
# PASSWORD (optional - only active if app_password is in secrets)
# ------------------------------------------------------------------
def check_password():
    pw = st.secrets.get("app_password")
    if not pw or st.session_state.get("authed"):
        return True
    st.markdown("### 🔒 Enter password")
    entered = st.text_input("Password", type="password")
    if st.button("Unlock", type="primary"):
        if entered == pw:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("Wrong password")
    return False


# ------------------------------------------------------------------
# PAGES
# ------------------------------------------------------------------
@st.dialog("💳 Use Quota")
def use_quota_dialog(quota):
    st.write(f"Available: **{fmt(quota)}**")
    amount = st.number_input("How much do you want to use? (฿)", min_value=0, step=5, value=0)
    comment = st.text_area("What is it for?", placeholder="e.g. Bubble tea with friends")
    if amount > quota:
        st.warning("That's more than your quota. Your balance will go negative.")
    if st.button("Use it! 🎉", type="primary", use_container_width=True):
        if amount <= 0:
            st.warning("Please enter an amount above 0.")
        else:
            add_log("Use Quota", datetime.now(TZ), amount, "Use Quota", comment.strip())
            st.session_state.celebrate = QUOTA_EMOJIS
            st.rerun()


def render_home():
    df = load_logs()
    quota = current_quota(df)
    cls = "quota-box negative" if quota < 0 else "quota-box"
    st.markdown(f'<div class="{cls}"><div class="label">Quota left</div>'
                f'<div class="value">{fmt(quota)}</div></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.button("Punishment", key="homepunish", on_click=open_form, args=("Punishment",), use_container_width=True)
    if c2.button("Use Quota", key="homequota", use_container_width=True):
        use_quota_dialog(quota)
    c3.button("Reward", key="homereward", on_click=open_form, args=("Reward",), use_container_width=True)


def render_entry_form(kind):
    is_reward = kind == "Reward"
    st.button("← Back", key="back", on_click=go, args=("home",))
    st.header("🏆 Log a Reward" if is_reward else "⚠️ Log a Punishment")

    st.subheader("1. Date & time")
    c1, c2 = st.columns(2)
    c1.date_input("Date", key="f_date", format="DD/MM/YYYY")
    c2.time_input("Time", key="f_time", step=60)

    st.subheader("2. Amount")
    cols = st.columns(len(PRESET_AMOUNTS))
    for col, val in zip(cols, PRESET_AMOUNTS):
        col.button(f"฿{val}", key=f"preset{val}", on_click=set_amount, args=(val,), use_container_width=True)
    st.number_input("Or type an amount (฿)", min_value=0, step=5, key="f_amount")
    st.caption("➕ This will be **added to** your quota." if is_reward
               else "➖ This will be **deducted from** your quota.")

    st.subheader("3. What did you do?")
    st.radio("Type", REWARD_TYPES if is_reward else PUNISH_TYPES, key="f_type",
             horizontal=True, label_visibility="collapsed")

    st.subheader("4. Comments")
    st.text_area("Details", key="f_comment", label_visibility="collapsed",
                 placeholder="Describe what you did in more detail...")

    if st.button("Submit", key="submitentry", type="primary", use_container_width=True):
        if st.session_state.f_amount <= 0:
            st.warning("Please choose or type an amount above 0.")
        else:
            dt = datetime.combine(st.session_state.f_date, st.session_state.f_time)
            with st.spinner("Saving..."):
                add_log(kind, dt, st.session_state.f_amount, st.session_state.f_type,
                        st.session_state.f_comment.strip())
            st.session_state.celebrate = REWARD_EMOJIS if is_reward else PUNISH_EMOJIS
            st.session_state.page = "home"
            st.rerun()


def render_pie(df, category, title):
    st.markdown(f"**{title}**")
    sub = df[df["category"] == category]
    if sub.empty:
        st.info("No data yet")
        return
    counts = sub["type"].value_counts().reset_index()
    counts.columns = ["type", "count"]
    fig = px.pie(counts, names="type", values="count", hole=0.35)
    fig.update_traces(textinfo="percent+label", textposition="inside")
    fig.update_layout(showlegend=False, margin=dict(t=5, b=5, l=5, r=5), height=260)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"pie{category}")
    top = counts.iloc[0]
    st.caption(f"Most common: **{top['type']}** ({top['count']}×)")


def render_log_list(df, category):
    sub = df[df["category"] == category].sort_values("dt", ascending=False, na_position="last")
    st.markdown(f"#### {category} logs ({len(sub)})")
    if sub.empty:
        st.info("Nothing logged yet.")
        return
    if len(sub) > 20 and not st.toggle("Show all", key=f"all{category}"):
        sub = sub.head(20)

    options = REWARD_TYPES if category == "Reward" else PUNISH_TYPES
    for _, r in sub.iterrows():
        lid = r["id"]
        name = r["comment"][:30] if (category == "Use Quota" and r["comment"]) else r["type"]
        label = f"{r['datetime']} · {name} · {fmt(r['amount'])}"
        with st.expander(label):
            dt = r["dt"] if not pd.isna(r["dt"]) else datetime.now(TZ)
            with st.form(key=f"form{lid}"):
                c1, c2 = st.columns(2)
                d = c1.date_input("Date", value=dt.date(), key=f"ed{lid}", format="DD/MM/YYYY")
                t = c2.time_input("Time", value=dt.time(), key=f"et{lid}", step=60)
                amt = st.number_input("Amount (฿)", min_value=0, step=5, value=int(r["amount"]), key=f"ea{lid}")
                if category == "Use Quota":
                    typ = "Use Quota"
                else:
                    idx = options.index(r["type"]) if r["type"] in options else len(options) - 1
                    typ = st.selectbox("Type", options, index=idx, key=f"ey{lid}")
                com = st.text_area("Comment", value=r["comment"], key=f"ec{lid}")
                confirm = st.checkbox("Tick to confirm delete", key=f"ex{lid}")
                b1, b2 = st.columns(2)
                save = b1.form_submit_button("💾 Save", type="primary", use_container_width=True)
                delete = b2.form_submit_button("🗑️ Delete", use_container_width=True)

            if save:
                if amt <= 0:
                    st.warning("Amount must be above 0.")
                else:
                    update_log(lid, category, datetime.combine(d, t), amt, typ, com.strip())
                    st.session_state.flash = "Saved ✅"
                    st.rerun()
            if delete:
                if confirm:
                    delete_log(lid)
                    st.session_state.flash = "Deleted 🗑️"
                    st.rerun()
                else:
                    st.warning("Tick 'confirm delete' first.")


def render_analytics():
    df = load_logs()
    st.header("📊 Analytics")

    k1, k2, k3 = st.columns(3)
    k1.metric("Rewards", fmt(df.loc[df["category"] == "Reward", "amount"].sum()))
    k2.metric("Punishments", fmt(df.loc[df["category"] == "Punishment", "amount"].sum()))
    k3.metric("Used", fmt(df.loc[df["category"] == "Use Quota", "amount"].sum()))

    p1, p2 = st.columns(2)
    with p1:
        render_pie(df, "Punishment", "⚠️ Punishments")
    with p2:
        render_pie(df, "Reward", "🏆 Rewards")

    st.divider()
    st.markdown("#### Past logs")
    c1, c2, c3 = st.columns(3)
    c1.button("Punishment", key="logpunish", on_click=set_log_view, args=("Punishment",), use_container_width=True)
    c2.button("Use Quota", key="logquota", on_click=set_log_view, args=("Use Quota",), use_container_width=True)
    c3.button("Reward", key="logreward", on_click=set_log_view, args=("Reward",), use_container_width=True)

    if st.session_state.log_view:
        render_log_list(df, st.session_state.log_view)
    else:
        st.caption("Tap a button above to see, edit or delete past logs.")


def render_bottom_nav():
    page = st.session_state.page
    with st.container(key="bottomnav"):
        c1, c2 = st.columns(2)
        c1.button("Home", key="navhome", icon=":material/home:", on_click=go, args=("home",),
                  type="primary" if page != "analytics" else "secondary", use_container_width=True)
        c2.button("Analytics", key="navanalytics", icon=":material/analytics:", on_click=go,
                  args=("analytics",), type="primary" if page == "analytics" else "secondary",
                  use_container_width=True)


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
try:
    secrets_ok = "gcp_service_account" in st.secrets and "sheet_url" in st.secrets
except Exception:
    secrets_ok = False
if not secrets_ok:
    st.error("Secrets are missing. Add `sheet_url` and `[gcp_service_account]` in the app's Secrets settings.")
    st.stop()

if not check_password():
    st.stop()

st.session_state.setdefault("page", "home")
st.session_state.setdefault("log_view", None)

if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"))

page = st.session_state.page
if page == "home":
    render_home()
elif page in ("Reward", "Punishment"):
    render_entry_form(page)
elif page == "analytics":
    render_analytics()

if "celebrate" in st.session_state:
    show_confetti(st.session_state.pop("celebrate"))

render_bottom_nav()
