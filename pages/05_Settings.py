"""Settings page — configure check frequency, email, notifications, and data management."""

import json
import os
from datetime import datetime, timedelta, timezone

import streamlit as st

from core.database import (
    ETF,
    Alert,
    NotificationLog,
    PriceHistory,
    Setting,
    SessionLocal,
    get_session,
)
from core.notifier import test_connection as test_sendgrid_connection
from core.scheduler import get_scheduler_status, set_interval, start_scheduler, stop_scheduler

st.markdown("# ⚙️ Settings")
st.markdown("---")

session = next(get_session())

# ── Check Frequency ──────────────────────────────────────────────────────────
st.markdown("<h2 class='section-header'>⏱️ Check Frequency</h2>", unsafe_allow_html=True)

current_setting = session.query(Setting).filter(Setting.key == "check_interval_minutes").first()
current_interval = int(current_setting.value) if current_setting else 60

interval_options = {
    "15 minutes": 15,
    "30 minutes": 30,
    "1 hour": 60,
    "4 hours": 240,
    "Daily (24 hours)": 1440,
}

current_label = None
for label, value in interval_options.items():
    if value == current_interval:
        current_label = label
        break
if current_label is None:
    current_label = "1 hour"

new_label = st.radio(
    "Check every:",
    options=list(interval_options.keys()),
    index=list(interval_options.keys()).index(current_label) if current_label in interval_options else 2,
    horizontal=True,
)

sched_status = get_scheduler_status()

col1, col2, col3 = st.columns(3)
col1.info(f"Current interval: **{current_interval} min**")
col2.info(f"Next run: **{sched_status.get('next_run', 'N/A')}**")
col3.info(f"Last run: **{sched_status.get('last_run', 'N/A')}**")

col_a, col_b, col_c = st.columns(3)
with col_a:
    if st.button("Apply Interval", type="primary"):
        new_interval = interval_options[new_label]
        set_interval(new_interval)
        st.success(f"Interval updated to {new_label}")
        st.rerun()
with col_b:
    if st.button("Restart Scheduler"):
        stop_scheduler()
        start_scheduler()
        st.success("Scheduler restarted")
        st.rerun()
with col_c:
    if st.button("Stop Scheduler"):
        stop_scheduler()
        st.success("Scheduler stopped")
        st.rerun()

st.markdown("---")

# ── Email Settings (SendGrid) ─────────────────────────────────────────────────
st.markdown("<h2 class='section-header'>📧 Email Settings (SendGrid)</h2>", unsafe_allow_html=True)

with st.form("email_settings_form"):
    sendgrid_api_key = st.text_input(
        "SendGrid API Key",
        value=os.environ.get("SENDGRID_API_KEY", ""),
        type="password",
        help="Get this from SendGrid → Settings → API Keys",
        placeholder="SG.xxxxxxxx",
    )
    sendgrid_from_email = st.text_input(
        "From Email",
        value=os.environ.get("SENDGRID_FROM_EMAIL", ""),
        placeholder="alerts@yourdomain.com",
        help="Verified sender email in SendGrid",
    )
    notify_email = st.text_input(
        "Notification Email",
        value=os.environ.get("NOTIFY_EMAIL", ""),
        placeholder="your_email@gmail.com",
        help="Where you want to receive alerts",
    )

    cols = st.columns(2)
    with cols[0]:
        saved = st.form_submit_button("💾 Save & Apply", type="primary", use_container_width=True)
    with cols[1]:
        tested = st.form_submit_button("🔍 Test Connection", use_container_width=True)

if saved:
    os.environ["SENDGRID_API_KEY"] = sendgrid_api_key
    os.environ["SENDGRID_FROM_EMAIL"] = sendgrid_from_email
    os.environ["NOTIFY_EMAIL"] = notify_email
    st.success("Email settings saved for this session. Set them permanently in your .env file.")

if tested:
    with st.spinner("Testing SendGrid connection..."):
        if all([sendgrid_api_key, sendgrid_from_email, notify_email]):
            os.environ["SENDGRID_API_KEY"] = sendgrid_api_key
            os.environ["SENDGRID_FROM_EMAIL"] = sendgrid_from_email
            os.environ["NOTIFY_EMAIL"] = notify_email

            ok = test_sendgrid_connection()
            if ok:
                st.success("✅ SendGrid connection successful!")
            else:
                st.error("❌ SendGrid configuration invalid. Check API key and emails.")
        else:
            st.warning("Please fill in all fields to test.")

st.markdown("---")

# ── Notification Preferences ─────────────────────────────────────────────────
st.markdown("<h2 class='section-header'>🔔 Notification Preferences</h2>", unsafe_allow_html=True)

notify_above = session.query(Setting).filter(Setting.key == "notify_on_above").first()
notify_below = session.query(Setting).filter(Setting.key == "notify_on_below").first()
notify_change = session.query(Setting).filter(Setting.key == "notify_on_change_pct").first()

with st.form("notif_prefs"):
    n_above = st.checkbox("Price Above alerts", value=notify_above.value == "true" if notify_above else True)
    n_below = st.checkbox("Price Below alerts", value=notify_below.value == "true" if notify_below else True)
    n_change = st.checkbox("Daily Change % alerts", value=notify_change.value == "true" if notify_change else False)

    if st.form_submit_button("Save Preferences", type="primary"):
        _save_setting("notify_on_above", "true" if n_above else "false")
        _save_setting("notify_on_below", "true" if n_below else "false")
        _save_setting("notify_on_change_pct", "true" if n_change else "false")
        st.success("Notification preferences saved!")
        st.rerun()

st.markdown("---")

# ── Data Management ──────────────────────────────────────────────────────────
st.markdown("<h2 class='section-header'>🗃️ Data Management</h2>", unsafe_allow_html=True)

col_d1, col_d2, col_d3 = st.columns(3)

with col_d1:
    retention_days = st.number_input(
        "Retain price history (days)",
        min_value=1,
        max_value=365,
        value=90,
    )
    if st.button("🧹 Clear Old Data", type="secondary", use_container_width=True):
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        deleted = session.query(PriceHistory).filter(PriceHistory.fetched_at < cutoff).count()
        session.query(PriceHistory).filter(PriceHistory.fetched_at < cutoff).delete()
        session.commit()
        st.success(f"Deleted {deleted} old price records")

with col_d2:
    if st.button("📤 Export All Data (JSON)", use_container_width=True):
        export_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "etfs": [],
            "alerts": [],
            "price_history_count": 0,
        }

        etfs = session.query(ETF).all()
        for e in etfs:
            export_data["etfs"].append({
                "id": e.id,
                "ticker": e.ticker,
                "name": e.name,
                "currency": e.currency,
                "quantity": e.quantity,
                "added_at": e.added_at.isoformat() if e.added_at else None,
                "is_active": e.is_active,
            })

        alerts = session.query(Alert).all()
        for a in alerts:
            export_data["alerts"].append({
                "id": a.id,
                "etf_id": a.etf_id,
                "alert_type": a.alert_type,
                "threshold": a.threshold,
                "is_active": a.is_active,
                "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
            })

        export_data["price_history_count"] = session.query(PriceHistory).count()

        json_str = json.dumps(export_data, indent=2, default=str)
        st.download_button(
            "📥 Download JSON",
            data=json_str,
            file_name=f"etf_monitor_export_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True,
        )

with col_d3:
    if st.button("🔄 Reset to Defaults", type="secondary", use_container_width=True):
        session.query(Setting).delete()
        session.commit()
        _seed_default_settings(session)
        st.success("Settings reset to defaults")
        st.rerun()

st.markdown("---")

# ── About Section ────────────────────────────────────────────────────────────
st.markdown("<h2 class='section-header'>ℹ️ About</h2>", unsafe_allow_html=True)

st.markdown(
    """
    | Property | Value |
    |----------|-------|
    | **Version** | 1.0.0 |
    | **Stack** | Python · Streamlit · yfinance · APScheduler · SQLite |
    | **Deploy** | Railway.app |
    | **License** | MIT |
    """
)

st.markdown(
    """
    **Links:**
    - [GitHub Repository](https://github.com/yourusername/etf-monitor)
    - [Streamlit Documentation](https://docs.streamlit.io)
    """
)

session.close()


def _save_setting(key: str, value: str) -> None:
    """Helper to upsert a setting."""
    sess = next(get_session())
    try:
        setting = sess.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = value
        else:
            sess.add(Setting(key=key, value=value))
        sess.commit()
    except Exception:
        sess.rollback()
    finally:
        sess.close()


def _seed_default_settings(session) -> None:
    """Re-seed default settings after reset."""
    defaults = {
        "check_interval_minutes": "60",
        "notify_on_above": "true",
        "notify_on_below": "true",
        "notify_on_change_pct": "false",
        "data_retention_days": "90",
    }
    for k, v in defaults.items():
        session.add(Setting(key=k, value=v))
    session.commit()