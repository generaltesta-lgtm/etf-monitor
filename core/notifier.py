"""Email notification module using smtplib.

Supports Gmail SMTP (port 587 / TLS). Sends styled HTML alert emails and
report attachments. Gracefully degrades when env vars are missing.
"""

import logging
import os
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

from core.fetcher import currency_symbol


def _get_smtp_config() -> dict:
    """Read SMTP configuration from environment variables."""
    return {
        "host": os.environ.get("SMTP_HOST", ""),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "notify_email": os.environ.get("NOTIFY_EMAIL", ""),
    }


def _build_alert_html(
    ticker: str,
    etf_name: str,
    condition: str,
    current_price: float,
    change_pct: float,
    currency: str = "USD",
) -> str:
    """Build a styled HTML email body for an alert notification."""
    change_class = "positive" if change_pct >= 0 else "negative"
    change_sign = "+" if change_pct >= 0 else ""
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="padding:24px;">
            <tr>
                <td align="center">
                    <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.1);">
                        <tr>
                            <td style="background:#0f172a;padding:24px;text-align:center;">
                                <h1 style="color:#f8fafc;margin:0;font-size:20px;">📈 ETF Monitor Alert</h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:24px;">
                                <h2 style="color:#1e293b;margin:0 0 4px 0;">{etf_name}</h2>
                                <p style="color:#64748b;margin:0 0 20px 0;font-size:14px;">{ticker}</p>
                                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin-bottom:20px;">
                                    <p style="margin:0 0 8px 0;font-size:16px;font-weight:600;color:#1e293b;">{condition}</p>
                                    <table width="100%" cellpadding="8">
                                        <tr>
                                            <td style="color:#64748b;font-size:14px;">Current Price</td>
                                            <td style="text-align:right;font-size:20px;font-weight:700;color:#1e293b;">{currency_symbol(currency)}{current_price:.2f}</td>
                                        </tr>
                                        <tr>
                                            <td style="color:#64748b;font-size:14px;">Daily Change</td>
                                            <td style="text-align:right;font-size:16px;font-weight:600;color:{'#22c55e' if change_pct >= 0 else '#ef4444'};">{change_sign}{change_pct:.2f}%</td>
                                        </tr>
                                    </table>
                                </div>
                                <p style="color:#94a3b8;font-size:12px;text-align:center;">
                                    This alert was triggered by your ETF Monitor settings.
                                    <br>Logged at {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def send_alert_email(
    alert: object,
    ticker: str,
    etf_name: str,
    current_price: float,
    change_pct: float,
    currency: str = "USD",
) -> bool:
    """Send a styled HTML alert email.

    Args:
        alert: Alert model instance.
        ticker: ETF ticker symbol.
        etf_name: Human-readable ETF name.
        current_price: Current price value.
        change_pct: Daily change percentage.
        currency: Currency code.

    Returns:
        True if sent successfully, False otherwise (also logs warnings).
    """
    config = _get_smtp_config()
    if not all([config["host"], config["user"], config["password"], config["notify_email"]]):
        logger.warning("SMTP not configured — skipping alert email")
        return False

    # Map alert type to human-readable condition
    sym = currency_symbol(currency)
    condition_map = {
        "ABOVE": f"Price crossed ABOVE {sym}{alert.threshold:.2f}",
        "BELOW": f"Price crossed BELOW {sym}{alert.threshold:.2f}",
        "CHANGE_PCT": f"Daily change exceeded {alert.threshold:.2f}%",
    }
    condition = condition_map.get(alert.alert_type, f"Alert condition met (threshold: {alert.threshold})")

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"ETF Alert: {ticker} - {condition}"
        msg["From"] = config["user"]
        msg["To"] = config["notify_email"]

        html = _build_alert_html(ticker, etf_name, condition, current_price, change_pct, currency)
        msg.attach(MIMEText(html, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP(config["host"], config["port"]) as server:
            server.starttls(context=context)
            server.login(config["user"], config["password"])
            server.sendmail(config["user"], config["notify_email"], msg.as_string())

        logger.info("Alert email sent for %s (%s)", ticker, condition)
        return True
    except Exception as exc:
        logger.error("Failed to send alert email: %s", exc)
        return False


def send_report_email(report_path: str, recipient: Optional[str] = None) -> bool:
    """Send an email with a PDF report attached.

    Args:
        report_path: Path to the PDF report file.
        recipient: Email address to send to. Falls back to NOTIFY_EMAIL env var.

    Returns:
        True if sent successfully, False otherwise.
    """
    config = _get_smtp_config()
    target = recipient or config.get("notify_email", "")
    if not all([config["host"], config["user"], config["password"], target]):
        logger.warning("SMTP not configured — skipping report email")
        return False

    try:
        msg = MIMEMultipart()
        msg["Subject"] = "ETF Monitor Report"
        msg["From"] = config["user"]
        msg["To"] = target

        msg.attach(MIMEText("Please find attached the ETF Monitor report.", "plain"))

        with open(report_path, "rb") as f:
            part = MIMEApplication(f.read(), _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename="etf_report.pdf")
            msg.attach(part)

        context = ssl.create_default_context()
        with smtplib.SMTP(config["host"], config["port"]) as server:
            server.starttls(context=context)
            server.login(config["user"], config["password"])
            server.sendmail(config["user"], target, msg.as_string())

        logger.info("Report email sent to %s", target)
        return True
    except Exception as exc:
        logger.error("Failed to send report email: %s", exc)
        return False


def test_connection() -> bool:
    """Test SMTP connection by attempting to log in.

    Returns:
        True if connection and login succeed, False otherwise.
    """
    config = _get_smtp_config()
    if not all([config["host"], config["user"], config["password"]]):
        logger.warning("SMTP not fully configured — cannot test connection")
        return False

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(config["host"], config["port"]) as server:
            server.starttls(context=context)
            server.login(config["user"], config["password"])
        logger.info("SMTP connection test passed")
        return True
    except Exception as exc:
        logger.error("SMTP connection test failed: %s", exc)
        return False