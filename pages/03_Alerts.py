"""Alerts page — create, view, and test price alerts."""

from datetime import datetime, timezone

import streamlit as st

from core.database import Alert, ETF, NotificationLog, get_session
from core.fetcher import currency_symbol, fetch_current_price
from core.notifier import send_alert_email, test_connection

st.markdown("# 🔔 Alerts")
st.markdown("---")

session = next(get_session())

# Ensure session state for test email flag
if "test_email_sent" not in st.session_state:
    st.session_state.test_email_sent = False

# ── Create Alert Form ────────────────────────────────────────────────────────
col_form, col_table = st.columns([1, 1.5])

with col_form:
    st.markdown("<h3 class='section-header'>➕ New Alert</h3>", unsafe_allow_html=True)

    etfs = session.query(ETF).filter(ETF.is_active.is_(True)).order_by(ETF.ticker).all()
    if not etfs:
        st.warning("No active ETFs. Add one in ETF Manager first.")
    else:
        etf_options = {f"{e.ticker} - {e.name or ''}": e.id for e in etfs}

        with st.form("alert_form", clear_on_submit=True):
            selected_etf_label = st.selectbox(
                "Select ETF",
                options=list(etf_options.keys()),
            )

            alert_type = st.selectbox(
                "Condition",
                options=[
                    ("ABOVE", "Price Above"),
                    ("BELOW", "Price Below"),
                    ("CHANGE_PCT", "Daily Change %"),
                ],
                format_func=lambda x: x[1],
            )

            threshold = st.number_input(
                "Threshold Value",
                min_value=0.0,
                step=0.01,
                format="%.4f",
                help="Price in USD, or percentage for Daily Change",
            )

            custom_note = st.text_input(
                "Custom Note (optional)",
                placeholder="e.g. Earnings week alert",
            )

            submitted = st.form_submit_button("Create Alert", type="primary", use_container_width=True)

            if submitted and selected_etf_label:
                etf_id = etf_options[selected_etf_label]
                alert = Alert(
                    etf_id=etf_id,
                    alert_type=alert_type[0],
                    threshold=threshold,
                    custom_note=custom_note or None,
                    is_active=True,
                )
                session.add(alert)
                session.commit()
                st.success("✅ Alert created!")
                st.rerun()

    st.markdown("---")

    # Test notification
    st.markdown("<h3 class='section-header'>📧 Test Notification</h3>", unsafe_allow_html=True)
    if st.button("Send Test Email", type="secondary", use_container_width=True):
        # Import here to avoid circular imports
        from core.notifier import send_test_email
        with st.spinner("Sending test email..."):
            if send_test_email():
                st.session_state.test_email_sent = True
                st.success("✅ Test email sent successfully! Check your notification email.")
            else:
                st.session_state.test_email_sent = True
                st.error(
                    "❌ Failed to send test email. Check SendGrid configuration and logs."
                )

# ── Active Alerts Table ──────────────────────────────────────────────────────
with col_table:
    st.markdown("<h3 class='section-header'>🔔 Active Alerts</h3>", unsafe_allow_html=True)

    alerts = (
        session.query(Alert)
        .join(ETF)
        .order_by(Alert.created_at.desc())
        .all()
    )

    if not alerts:
        st.info("No alerts configured. Create one on the left.")
    else:
        type_labels = {"ABOVE": "Price Above", "BELOW": "Price Below", "CHANGE_PCT": "Daily Change %"}

        for alert in alerts:
            etf = alert.etf
            data = fetch_current_price(etf.ticker)
            current_price = data.get("price", 0) if "error" not in data else None

            triggered = alert.triggered_at is not None

            badge_class = "badge-triggered" if triggered else "badge-active"
            badge_text = "🔔 Triggered" if triggered else "✅ Active"

            with st.container(border=True):
                cols = st.columns([2.5, 1.5, 1.5, 1, 0.8, 0.8])

                with cols[0]:
                    st.markdown(f"**{etf.ticker}** — {type_labels.get(alert.alert_type, alert.alert_type)}")
                    st.caption(f"Threshold: {alert.threshold:.4f}")

                with cols[1]:
                    if current_price is not None:
                        st.markdown(f"Current: **{currency_symbol(etf.currency)}{current_price:.2f}**")
                    else:
                        st.markdown("Price: N/A")

                with cols[2]:
                    st.markdown(
                        f"<span class='{badge_class}'>{badge_text}</span>",
                        unsafe_allow_html=True,
                    )

                with cols[3]:
                    if alert.custom_note:
                        st.caption(alert.custom_note)

                with cols[4]:
                    if triggered:
                        if st.button("🔁", key=f"reset_{alert.id}", help="Reset alert"):
                            alert.triggered_at = None
                            session.commit()
                            st.rerun()

                with cols[5]:
                    if st.button("❌", key=f"del_alert_{alert.id}", help="Delete alert"):
                        session.delete(alert)
                        session.commit()
                        st.rerun()

    st.markdown("---")

    # ── Alert History ────────────────────────────────────────────────────────
    st.markdown("<h3 class='section-header'>📜 Alert History</h3>", unsafe_allow_html=True)

    logs = (
        session.query(NotificationLog)
        .order_by(NotificationLog.sent_at.desc())
        .limit(50)
        .all()
    )

    if not logs:
        st.info("No alert history yet.")
    else:
        for log in logs:
            status_icon = "✅" if log.status == "OK" else "❌"
            ts = log.sent_at.strftime("%Y-%m-%d %H:%M:%S") if log.sent_at else "N/A"
            st.markdown(
                f"<div style='padding:6px 12px;background:#1e293b;border-radius:6px;margin-bottom:4px;'>"
                f"<span style='color:#94a3b8;font-size:0.8rem;'>{ts}</span> "
                f"{status_icon} {log.message[:120]}"
                f"</div>",
                unsafe_allow_html=True,
            )

session.close()