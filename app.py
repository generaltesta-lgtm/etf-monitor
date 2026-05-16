"""ETF Monitor — Streamlit Application Entry Point."""

import os
import sys
from datetime import datetime, timezone

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import init_db
from core.scheduler import start_scheduler, get_scheduler_status
from core.utils import fmt_rome, rome_now

st.set_page_config(
    page_title="ETF Monitor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load custom CSS ──────────────────────────────────────────────────────────
css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Initialize database ─────────────────────────────────────────────────────
if "db_initialized" not in st.session_state:
    try:
        init_db()
        st.session_state.db_initialized = True
    except Exception as exc:
        st.session_state.db_initialized = False
        st.session_state.db_error = str(exc)

# ── Start background scheduler ──────────────────────────────────────────────
if "scheduler_started" not in st.session_state:
    try:
        start_scheduler()
        st.session_state.scheduler_started = True
    except Exception as exc:
        st.session_state.scheduler_started = False
        st.session_state.scheduler_error = str(exc)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("assets/stock-exchange.png", width=60)
    st.markdown("<h1 style='margin-top:-10px;'>ETF Monitor</h1>", unsafe_allow_html=True)
    st.markdown("---")

    # Connection status
    st.markdown("#### System Status")

    db_ok = st.session_state.get("db_initialized", False)
    sched_ok = st.session_state.get("scheduler_started", False)

    smtp_host = os.environ.get("SMTP_HOST", "")
    email_ok = bool(smtp_host)

    col1, col2, col3 = st.columns(3)
    col1.markdown(
        f"<div style='text-align:center;padding:8px;background:#1e293b;border-radius:8px;'>"
        f"<span style='font-size:20px;'>{'✅' if db_ok else '❌'}</span><br/><small>DB</small></div>",
        unsafe_allow_html=True,
    )
    col2.markdown(
        f"<div style='text-align:center;padding:8px;background:#1e293b;border-radius:8px;'>"
        f"<span style='font-size:20px;'>{'✅' if sched_ok else '❌'}</span><br/><small>Sched</small></div>",
        unsafe_allow_html=True,
    )
    col3.markdown(
        f"<div style='text-align:center;padding:8px;background:#1e293b;border-radius:8px;'>"
        f"<span style='font-size:20px;'>{'✅' if email_ok else '⚠️'}</span><br/><small>Email</small></div>",
        unsafe_allow_html=True,
    )

    # Scheduler info
    sched_status = get_scheduler_status()
    if sched_status.get("running"):
        st.info(
            f"⏱️ {sched_status.get('interval_minutes', '?')} min interval\n\n"
            f"Last run: {fmt_rome(sched_status.get('last_run'))}\n\n"
            f"Next run: {fmt_rome(sched_status.get('next_run'))}"
        )
    else:
        st.warning("⚠️ Scheduler not running")

    st.markdown("---")
    st.caption(f"v1.0.0 · {rome_now().strftime('%Y-%m-%d %H:%M')} (Rome)")


# ── Page routing ─────────────────────────────────────────────────────────────
dashboard = st.Page("pages/01_Dashboard.py", title="Dashboard", icon="📊")
etf_mgr = st.Page("pages/02_ETF_Manager.py", title="ETF Manager", icon="📋")
alerts = st.Page("pages/03_Alerts.py", title="Alerts", icon="🔔")
reports = st.Page("pages/04_Reports.py", title="Reports", icon="📄")
settings = st.Page("pages/05_Settings.py", title="Settings", icon="⚙️")

pg = st.navigation([dashboard, etf_mgr, alerts, reports, settings])
pg.run()