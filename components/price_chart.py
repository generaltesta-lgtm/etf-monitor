"""Plotly chart component for ETF price visualization."""

from typing import List, Optional

from core.fetcher import currency_symbol

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


def render_price_chart(
    history: pd.DataFrame,
    ticker: str,
    title: Optional[str] = None,
    height: int = 450,
    show_volume: bool = True,
) -> None:
    """Render an interactive Plotly candlestick or line chart.

    Args:
        history: DataFrame with OHLCV data from yfinance.
        ticker: ETF ticker symbol.
        title: Optional chart title.
        height: Chart height in pixels.
        show_volume: Whether to show volume subplot.
    """
    if history.empty:
        st.info(f"No price history available for {ticker}")
        return

    rows = 2 if show_volume else 1
    row_heights = [0.7, 0.3] if show_volume else [1.0]

    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=row_heights)

    # Candlestick trace
    fig.add_trace(
        go.Candlestick(
            x=history.index,
            open=history["Open"],
            high=history["High"],
            low=history["Low"],
            close=history["Close"],
            name=ticker,
            increasing_line_color="#22c55e",
            decreasing_line_color="#ef4444",
        ),
        row=1,
        col=1,
    )

    if show_volume and "Volume" in history.columns:
        colors = ["#22c55e" if history["Close"].iloc[i] >= history["Open"].iloc[i] else "#ef4444" for i in range(len(history))]
        fig.add_trace(
            go.Bar(
                x=history.index,
                y=history["Volume"],
                name="Volume",
                marker_color=colors,
                opacity=0.5,
            ),
            row=2,
            col=1,
        )

    fig.update_layout(
        title=title or f"{ticker} Price Chart",
        height=height,
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font={"color": "#e2e8f0", "size": 12},
        xaxis_rangeslider_visible=False,
        margin={"l": 40, "r": 20, "t": 40, "b": 20},
        hovermode="x unified",
    )

    fig.update_yaxes(gridcolor="#334155", zerolinecolor="#334155")
    fig.update_xaxes(gridcolor="#334155")

    st.plotly_chart(fig, use_container_width=True)


def render_multi_etf_chart(
    histories: dict,
    period: str = "1mo",
    height: int = 500,
) -> None:
    """Render a multi-line chart comparing multiple ETFs normalized to 100.

    Args:
        histories: Dict mapping ticker -> price DataFrame.
        period: Display period label.
        height: Chart height in pixels.
    """
    fig = go.Figure()
    fig.update_layout(
        title=f"ETF Comparison (Normalized to 100) — {period}",
        height=height,
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font={"color": "#e2e8f0", "size": 12},
        margin={"l": 40, "r": 20, "t": 40, "b": 20},
        hovermode="x unified",
        legend={"bgcolor": "rgba(0,0,0,0)", "font": {"color": "#e2e8f0"}},
    )

    colors = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899"]
    for i, (ticker, hist) in enumerate(histories.items()):
        if hist.empty:
            continue
        close = hist["Close"]
        if len(close) == 0:
            continue
        normalized = (close / close.iloc[0]) * 100
        fig.add_trace(
            go.Scatter(
                x=normalized.index,
                y=normalized.values,
                mode="lines",
                name=ticker,
                line={"color": colors[i % len(colors)], "width": 2},
                hovertemplate=f"{ticker}: %{{y:.2f}}<br>%{{x}}<extra></extra>",
            )
        )

    fig.update_yaxes(gridcolor="#334155", zerolinecolor="#334155")
    fig.update_xaxes(gridcolor="#334155")

    st.plotly_chart(fig, use_container_width=True)


def render_sparkline(history: pd.DataFrame, height: int = 40, width: int = 120) -> str:
    """Generate an HTML SVG sparkline for use in tables.

    Args:
        history: DataFrame with Close column.
        height: SVG height in pixels.
        width: SVG width in pixels.

    Returns:
        SVG string for embedding in HTML.
    """
    if history.empty or "Close" not in history.columns:
        return '<span style="color:#64748b;font-size:0.8rem;">N/A</span>'

    close = history["Close"].values
    if len(close) < 2:
        return f'<span style="color:#e2e8f0;">${close[-1]:.2f}</span>'

    min_v, max_v = close.min(), close.max()
    range_v = max_v - min_v if max_v != min_v else 1
    padding = 4

    points = []
    for i, val in enumerate(close):
        x = padding + (i / max(1, len(close) - 1)) * (width - 2 * padding)
        y = height - padding - ((val - min_v) / range_v) * (height - 2 * padding)
        points.append(f"{x:.1f},{y:.1f}")

    color = "#22c55e" if close[-1] >= close[0] else "#ef4444"
    polyline = " ".join(points)

    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<polyline points="{polyline}" fill="none" stroke="{color}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        f"</svg>"
    )