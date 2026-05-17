"""Shared sidebar component for ETF Monitor."""

import streamlit as st


def render_sidebar() -> None:
    """Render the shared sidebar with navigation and system status."""
    with st.sidebar:
        # Use emoji for now to avoid background issues with the PNG
        st.markdown('<span style="font-size: 48px;">📈</span>', unsafe_allow_html=True)
        st.markdown("<h1 style='margin-top:-10px;'>ETF Monitor</h1>", unsafe_allow_html=True)
        st.markdown("---")

        st.markdown("#### System Status")
        col1, col2, col3 = st.columns(3)

        db_ok = st.session_state.get("db_initialized", False)
        col1.markdown(
            f"<div style='text-align:center;padding:8px;background:#1e293b;border-radius:8px;'>"
            f"<span style='font-size:20px;'>{'✅' if db_ok else '❌'}</span><br/><small>DB</small></div>",
            unsafe_allow_html=True,
        )

        sched_ok = st.session_state.get("scheduler_started", False)
        col2.markdown(
            f"<div style='text-align:center;padding:8px;background:#1e293b;border-radius:8px;'>"
            f"<span style='font-size:20px;'>{'✅' if sched_ok else '❌'}</span><br/><small>Sched</small></div>",
            unsafe_allow_html=True,
        )

        import os
        # Check SendGrid configuration for email status
        sendgrid_configured = bool(
            os.environ.get("SENDGRID_API_KEY") and
            os.environ.get("SENDGRID_FROM_EMAIL") and
            os.environ.get("NOTIFY_EMAIL")
        )
        col3.markdown(
            f"<div style='text-align:center;padding:8px;background:#1e293b;border-radius:8px;'>"
            f"<span style='font-size:20px;'>{'✅' if sendgrid_configured else '⚠️'}</span><br/><small>Email</small></div>",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Scheduler info
        from core.scheduler import get_scheduler_status
        sched_status = get_scheduler_status()
        if sched_status.get("running"):
            last_run = sched_status.get("last_run")
            next_run = sched_status.get("next_run")
            last_str = last_run.strftime("%H:%M:%S") if last_run else "N/A"
            next_str = next_run.strftime("%H:%M:%S") if next_run else "N/A"
            st.info(
                f"⏱️ **{sched_status.get('interval_minutes', '?')} min interval**  \n"
                f"Last: {last_str}  \n"
                f"Next: {next_str}"
            )
        else:
            st.warning("⚠️ Scheduler not running")

        st.markdown("---")
        st.caption("ETF Monitor v1.0.0")