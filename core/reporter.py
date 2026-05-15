"""Report generation module — PDF and CSV report creation using fpdf2 and pandas."""

import io
import os
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Optional

import pandas as pd

from core.database import Alert, ETF, PriceHistory, get_session
from core.fetcher import currency_symbol
from core.utils import fmt_rome_date, rome_now


def generate_pdf_report(
    etf_ids: List[int],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> bytes:
    """Generate a PDF report with cover page, per-ETF stats, and charts.

    Args:
        etf_ids: List of ETF database IDs to include.
        date_from: ISO date string for start of range (optional).
        date_to: ISO date string for end of range (optional).

    Returns:
        PDF file content as bytes.
    """
    from fpdf import FPDF

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── Cover Page ───────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 297, "F")

    pdf.set_text_color(248, 250, 252)
    pdf.set_font("Helvetica", "B", 28)
    pdf.ln(60)
    pdf.cell(0, 15, "ETF Monitor Report", align="C")
    pdf.ln(12)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 10, f"Generated: {rome_now().strftime('%Y-%m-%d %H:%M')} (Rome)", align="C")
    pdf.ln(10)

    session = next(get_session())
    try:
        etfs = session.query(ETF).filter(ETF.id.in_(etf_ids)).all()
        pdf.set_text_color(100, 116, 139)
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 8, f"ETFs included: {', '.join(e.ticker for e in etfs)}", align="C")
        pdf.ln(40)

        # ── Per-ETF Sections ─────────────────────────────────────────────────
        for etf in etfs:
            pdf.add_page()
            pdf.set_fill_color(15, 23, 42)
            pdf.rect(0, 0, 210, 297, "F")

            pdf.set_text_color(248, 250, 252)
            pdf.set_font("Helvetica", "B", 20)
            pdf.cell(0, 12, f"{etf.ticker} - {etf.name or ''}", align="L")
            pdf.ln(16)

            # Price history table
            query = session.query(PriceHistory).filter(PriceHistory.etf_id == etf.id)
            if date_from:
                query = query.filter(PriceHistory.fetched_at >= date_from)
            if date_to:
                query = query.filter(PriceHistory.fetched_at <= date_to)
            records = query.order_by(PriceHistory.fetched_at.desc()).limit(100).all()

            if records:
                pdf.set_text_color(148, 163, 184)
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 8, "Price History (last 100 points)", align="L")
                pdf.ln(10)

                # Table header
                pdf.set_fill_color(30, 41, 59)
                pdf.set_text_color(226, 232, 240)
                pdf.set_font("Helvetica", "B", 9)
                col_w = [35, 35, 35, 35]
                headers = ["Date", "Price", "Volume", "Change %"]
                for i, h in enumerate(headers):
                    pdf.cell(col_w[i], 8, h, border=0, fill=True, align="C")
                pdf.ln()

                # Table rows
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(203, 213, 225)
                sym = currency_symbol(etf.currency)

                for rec in records[:30]:  # Limit to 30 rows for PDF
                    ts = rec.fetched_at.strftime("%Y-%m-%d %H:%M") if rec.fetched_at else "N/A"
                    pdf.cell(col_w[0], 7, ts, align="C")
                    pdf.cell(col_w[1], 7, f"{sym}{rec.price:.2f}", align="C")
                    pdf.cell(col_w[2], 7, f"{int(rec.volume):,}", align="C")
                    change_clr = (34, 197, 94) if rec.change_pct >= 0 else (239, 68, 68)
                    pdf.set_text_color(*change_clr)
                    pdf.cell(col_w[3], 7, f"{rec.change_pct:+.2f}%", align="C")
                    pdf.set_text_color(203, 213, 225)
                    pdf.ln()

                # Summary stats
                prices = [r.price for r in records]
                if prices:
                    pdf.ln(10)
                    pdf.set_text_color(148, 163, 184)
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.cell(0, 8, "Summary Statistics", align="L")
                    pdf.ln(10)

                    pdf.set_font("Helvetica", "", 9)
                    pdf.set_text_color(203, 213, 225)
                    stats = [
                        ("High", f"{sym}{max(prices):.2f}"),
                        ("Low", f"{sym}{min(prices):.2f}"),
                        ("Average", f"{sym}{sum(prices)/len(prices):.2f}"),
                        ("Latest", f"{sym}{prices[0]:.2f}"),
                    ]
                    for label, val in stats:
                        pdf.cell(40, 7, label, align="L")
                        pdf.cell(40, 7, val, align="L")
                        pdf.ln()

            # Alerts for this ETF
            alerts = session.query(Alert).filter(Alert.etf_id == etf.id).all()
            if alerts:
                pdf.ln(10)
                pdf.set_text_color(148, 163, 184)
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 8, "Active Alerts", align="L")
                pdf.ln(10)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(203, 213, 225)
                for a in alerts:
                    status = "Triggered" if a.triggered_at else "Active"
                    pdf.cell(0, 7, f"  {a.alert_type} @ {a.threshold:.2f} [{status}]", align="L")
                    pdf.ln()
    finally:
        session.close()

    # Footer
    pdf.ln(20)
    pdf.set_text_color(71, 85, 105)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "ETF Monitor - Automated Report", align="C")

    return bytes(pdf.output())


def generate_csv_report(
    etf_ids: List[int],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> str:
    """Generate a CSV string of price history for selected ETFs.

    Args:
        etf_ids: List of ETF database IDs.
        date_from: ISO date string for start of range (optional).
        date_to: ISO date string for end of range (optional).

    Returns:
        CSV-formatted string.
    """
    session = next(get_session())
    try:
        etfs = session.query(ETF).filter(ETF.id.in_(etf_ids)).all()
        all_rows = []

        for etf in etfs:
            query = session.query(PriceHistory).filter(PriceHistory.etf_id == etf.id)
            if date_from:
                query = query.filter(PriceHistory.fetched_at >= date_from)
            if date_to:
                query = query.filter(PriceHistory.fetched_at <= date_to)
            records = query.order_by(PriceHistory.fetched_at).all()

            for rec in records:
                ts = rec.fetched_at.strftime("%Y-%m-%d %H:%M:%S") if rec.fetched_at else ""
                all_rows.append({
                    "Ticker": etf.ticker,
                    "Name": etf.name or "",
                    "Date": ts,
                    "Price": rec.price,
                    "Volume": int(rec.volume),
                    "Change_%": rec.change_pct,
                })

        if not all_rows:
            return "No data available for the selected criteria"

        df = pd.DataFrame(all_rows)
        return df.to_csv(index=False)
    finally:
        session.close()


def generate_summary_report() -> Dict:
    """Aggregate dashboard stats for summary display.

    Returns:
        Dict with keys: total_etfs, total_alerts, triggered_alerts, last_update.
    """
    session = next(get_session())
    try:
        total_etfs = session.query(ETF).filter(ETF.is_active.is_(True)).count()
        total_alerts = session.query(Alert).filter(Alert.is_active.is_(True)).count()
        triggered = session.query(Alert).filter(Alert.triggered_at.isnot(None)).count()

        price_count = session.query(PriceHistory).count()

        return {
            "total_etfs": total_etfs,
            "total_alerts": total_alerts,
            "triggered_alerts": triggered,
            "total_price_records": price_count,
            "report_generated_at": rome_now().strftime("%Y-%m-%d %H:%M"),
        }
    finally:
        session.close()