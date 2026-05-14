"""Reusable ETF card widget for displaying ETF summary information."""

import streamlit as st


from core.fetcher import currency_symbol


def render_etf_card(ticker: str, name: str, price: float, change_pct: float, currency: str = "USD") -> None:
    """Render a compact ETF card showing key metrics.

    Args:
        ticker: ETF ticker symbol.
        name: Human-readable ETF name.
        price: Current price.
        change_pct: Daily change percentage.
        currency: Currency code.
    """
    change_class = "price-up" if change_pct >= 0 else "price-down"
    change_sign = "+" if change_pct >= 0 else ""

    st.markdown(
        f"""
        <div class="metric-card hover-card" style="margin-bottom:0.75rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <strong style="color:#f8fafc;font-size:1.1rem;">{ticker}</strong>
                    <br/>
                    <span style="color:#94a3b8;font-size:0.8rem;">{name[:50]}</span>
                </div>
                <div style="text-align:right;">
                    <span style="color:#f8fafc;font-size:1.2rem;font-weight:700;">{currency_symbol(currency)}{price:.2f}</span>
                    <br/>
                    <span class="{change_class}" style="font-size:0.95rem;">
                        {change_sign}{change_pct:.2f}%
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )