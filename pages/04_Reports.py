"""Reports page — generate and download PDF/CSV reports with email option."""

import os
import tempfile
from datetime import datetime, timedelta, timezone

import streamlit as st

from core.database import ETF, get_session
from core.notifier import send_report_email
from core.reporter import generate_csv_report, generate_pdf_report, generate_summary_report
from core.utils import rome_now

st.markdown("# 📄 Reports")
st.markdown("---")

# ── Summary Stats ────────────────────────────────────────────────────────────
summary = generate_summary_report()
col1, col2, col3, col4 = st.columns(4)
col1.metric("ETFs Tracked", summary["total_etfs"], border=True)
col2.metric("Active Alerts", summary["total_alerts"], border=True)
col3.metric("Triggered Alerts", summary["triggered_alerts"], border=True)
col4.metric("Price Records", summary["total_price_records"], border=True)

st.markdown("---")

# ── Report Configuration ─────────────────────────────────────────────────────
st.markdown("<h2 class='section-header'>📝 Report Configuration</h2>", unsafe_allow_html=True)

session = next(get_session())
etfs = session.query(ETF).filter(ETF.is_active.is_(True)).order_by(ETF.ticker).all()
session.close()

if not etfs:
    st.warning("No ETFs tracked yet. Go to ETF Manager to add some.")
    st.stop()

etf_options = {f"{e.ticker} — {e.name or ''}": e.id for e in etfs}

# Date range
today = rome_now().date()
default_from = today - timedelta(days=30)

col_date1, col_date2 = st.columns(2)
with col_date1:
    date_from = st.date_input("From", value=default_from)
with col_date2:
    date_to = st.date_input("To", value=today)

# ETF multi-select
selected_labels = st.multiselect(
    "Select ETFs",
    options=list(etf_options.keys()),
    default=list(etf_options.keys())[:3] if len(etf_options) >= 3 else list(etf_options.keys()),
)

# Format selection
report_format = st.radio("Format", options=["PDF", "CSV"], horizontal=True, index=0)

# Email toggle
send_email = st.checkbox("Send report via email", value=False)
recipient_email = ""
if send_email:
    recipient_email = st.text_input(
        "Recipient Email",
        placeholder="alerts@example.com",
        value=os.environ.get("NOTIFY_EMAIL", ""),
    )

st.markdown("---")

# ── Generate Report ──────────────────────────────────────────────────────────
if st.button("🚀 Generate Report", type="primary", use_container_width=True):
    if not selected_labels:
        st.error("Please select at least one ETF")
        st.stop()

    selected_ids = [etf_options[label] for label in selected_labels]
    date_from_str = date_from.isoformat()
    date_to_str = (date_to + timedelta(days=1)).isoformat()  # Include end day

    with st.spinner("Generating report..."):
        if report_format == "PDF":
            pdf_bytes = generate_pdf_report(
                etf_ids=selected_ids,
                date_from=date_from_str,
                date_to=date_to_str,
            )

            # Preview
            st.markdown("<h3 class='section-header'>📊 Report Statistics</h3>", unsafe_allow_html=True)
            cols = st.columns(3)
            session = next(get_session())
            total_records = 0
            for eid in selected_ids:
                etf_obj = session.query(ETF).filter(ETF.id == eid).first()
                if etf_obj:
                    cols[0].markdown(f"**{etf_obj.ticker}**")
            session.close()
            cols[1].metric("Format", "PDF", border=True)
            cols[2].metric("ETFs", len(selected_ids), border=True)

            # Download button
            st.download_button(
                label="📥 Download PDF Report",
                data=pdf_bytes,
                file_name=f"etf_report_{today.isoformat()}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

            # Email
            if send_email and recipient_email:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf_bytes)
                    tmp_path = tmp.name

                with st.spinner("Sending email..."):
                    success = send_report_email(report_path=tmp_path, recipient=recipient_email)
                    if success:
                        st.success(f"✅ Report sent to {recipient_email}")
                    else:
                        st.error("❌ Failed to send email. Check email settings.")

                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        else:  # CSV
            csv_str = generate_csv_report(
                etf_ids=selected_ids,
                date_from=date_from_str,
                date_to=date_to_str,
            )

            # Preview
            st.markdown("<h3 class='section-header'>📊 CSV Preview</h3>", unsafe_allow_html=True)
            if csv_str != "No data available for the selected criteria":
                lines = csv_str.split("\n")
                preview = "\n".join(lines[:11])  # header + 10 rows
                st.code(preview, language="csv")
                st.caption(f"Showing {min(10, len(lines)-1)} of {len(lines)-1} data rows")

            st.download_button(
                label="📥 Download CSV Report",
                data=csv_str,
                file_name=f"etf_report_{today.isoformat()}.csv",
                mime="text/csv",
                use_container_width=True,
            )

            if send_email:
                st.info("CSV reports cannot be emailed automatically. Please download and send manually.")

    st.success("✅ Report generated successfully!")