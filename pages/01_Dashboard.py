"""Dashboard page — main overview with metrics, ETF table, and comparison chart."""

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from core.database import ETF, Alert, get_session
from core.fetcher import currency_symbol, fetch_current_price, fetch_history
from core.utils import rome_now
from components.etf_card import render_etf_card
from components.price_chart import render_multi_etf_chart, render_sparkline

st.markdown("# 📊 Dashboard")
st.markdown("---")

# ── Metric Cards ─────────────────────────────────────────────────────────────
session = next(get_session())
try:
    total_etfs = session.query(ETF).filter(ETF.is_active.is_(True)).count()
    active_alerts = session.query(Alert).filter(Alert.is_active.is_(True)).count()
    etfs = session.query(ETF).filter(ETF.is_active.is_(True)).all()
finally:
    session.close()

total_value = 0.0
for etf in etfs:
    if etf.quantity > 0:
        data = fetch_current_price(etf.ticker)
        if "error" not in data:
            total_value += data["price"] * etf.quantity

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total ETFs", total_etfs, border=True)
col2.metric(
    "Portfolio Value",
    f"${total_value:,.2f}" if total_value > 0 else "N/A",
    border=True,
)
col3.metric("Active Alerts", active_alerts, border=True)
col4.metric("Last Update", rome_now().strftime("%H:%M:%S"), border=True)

st.markdown("---")

# ── ETF Performance Table ────────────────────────────────────────────────────
st.markdown("<h2 class='section-header'>📋 ETF Performance Overview</h2>", unsafe_allow_html=True)

if not etfs:
    st.info("No ETFs tracked yet. Go to **ETF Manager** to add some.")
else:
    rows = []
    for etf in etfs:
        data = fetch_current_price(etf.ticker)
        if "error" in data:
            rows.append({
                "Ticker": etf.ticker,
                "Name": etf.name or etf.ticker,
                "Price": "N/A",
                "Change": "N/A",
                "Volume": "N/A",
                "Sparkline": "",
            })
        else:
            hist = fetch_history(etf.ticker, period="1mo")
            spark = render_sparkline(hist) if not hist.empty else ""

            change_cls = "price-up" if data["change_pct"] >= 0 else "price-down"
            change_sign = "+" if data["change_pct"] >= 0 else ""
            rows.append({
                "Ticker": etf.ticker,
                "Name": etf.name or etf.ticker,
                "Price": f"{currency_symbol(data.get('currency', 'USD'))}{data['price']:.2f}",
                "Change": f"<span class='{change_cls}'>{change_sign}{data['change_pct']:.2f}%</span>",
                "Volume": f"{data['volume']:,}",
                "Currency": data.get("currency", "USD"),
                "Sparkline": spark,
            })

    df = pd.DataFrame(rows)
    st.write(
        df.to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Price Chart(s) ───────────────────────────────────────────────
st.markdown("<h2 class='section-header'>📈 Price Chart</h2>", unsafe_allow_html=True)

period_map = {
    "1W": "5d",
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
}
selected_period = st.segmented_control(
    "Period",
    options=list(period_map.keys()),
    default="1M",
    key="dashboard_period",
    label_visibility="collapsed",
)

period = period_map.get(selected_period, "1mo")

if etfs:
    if len(etfs) == 1:
        # Single ETF: show actual price chart
        etf = etfs[0]
        with st.spinner(f"Loading price chart for {etf.ticker}..."):
            hist = fetch_history(etf.ticker, period=period)
            if not hist.empty:
                render_price_chart(hist, ticker=etf.ticker, title=f"{etf.ticker} Price ({period})")
            else:
                st.info(f"No historical data available for {etf.ticker}")
    else:
        # Multiple ETFs: show normalized comparison chart
        st.caption("Showing normalized performance (starting at 100) for comparison")
        histories = {}
        for etf in etfs:
            hist = fetch_history(etf.ticker, period=period)
            if not hist.empty:
                histories[etf.ticker] = hist

        if histories:
            render_multi_etf_chart(histories, period=selected_period)
        else:
            st.info("No historical data available for comparison.")
else:
    st.info("Add ETFs to see price charts.")