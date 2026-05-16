"""Email notification module using SendGrid HTTP API.

Works reliably on Railway/Heroku/etc. since it uses HTTPS (port 443).
"""

import logging
import os
import base64
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logger.warning("SendGrid package not installed. Install with: pip install sendgrid")

from core.fetcher import currency_symbol


def _get_sendgrid_config() -> dict:
    """Read SendGrid configuration from environment variables."""
    config = {
        "api_key": os.environ.get("SENDGRID_API_KEY", ""),
        "from_email": os.environ.get("SENDGRID_FROM_EMAIL", ""),
        "notify_email": os.environ.get("NOTIFY_EMAIL", ""),
    }
    # Log only non-sensitive info
    logger.info(f"SendGrid Config: api_key_set={bool(config['api_key'])}, from_set={bool(config['from_email'])}, notify_set={bool(config['notify_email'])}")
    return config


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
    """Send a styled HTML alert email via SendGrid."""
    if not SENDGRID_AVAILABLE:
        logger.error("SendGrid package not available. Install sendgrid to use email notifications.")
        return False

    config = _get_sendgrid_config()
    if not all([config["api_key"], config["from_email"], config["notify_email"]]):
        logger.warning("SendGrid not fully configured — skipping alert email")
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
        message = Mail(
            from_email=config["from_email"],
            to_emails=config["notify_email"],
            subject=f"ETF Alert: {ticker} - {condition}",
            html_content=_build_alert_html(ticker, etf_name, condition, current_price, change_pct, currency)
        )

        sg = SendGridAPIClient(config["api_key"])
        # Optional: set EU data residency if needed
        # if os.environ.get("SENDGRID_EU_RESIDENCY", "false").lower() == "true":
        #     sg.set_sendgrid_data_residency("eu")
        response = sg.send(message)

        # Log response details for debugging (like testmail.py does)
        logger.info(f"SendGrid response: status={response.status_code}, body={getattr(response, 'body', 'No body')}")

        if response.status_code == 202:
            logger.info(f"Alert email sent for {ticker} ({condition}) via SendGrid")
            return True
        else:
            logger.error(f"SendGrid returned unexpected status: {response.status_code}")
            logger.error(f"Response body: {getattr(response, 'body', 'No body')}")
            return False

    except Exception as exc:
        logger.error(f"Failed to send alert email via SendGrid: {type(exc).__name__}: {exc}")
        # Uncomment below for detailed debugging if needed
        # logger.debug("Full traceback:", exc_info=True)
        return False


def send_report_email(report_path: str, recipient: Optional[str] = None) -> bool:
    """Send an email with a PDF report attached via SendGrid."""
    if not SENDGRID_AVAILABLE:
        logger.error("SendGrid package not available. Install sendgrid to use email notifications.")
        return False

    config = _get_sendgrid_config()
    target = recipient or config.get("notify_email", "")
    if not all([config["api_key"], config["from_email"], target]):
        logger.warning("SendGrid not configured — skipping report email")
        return False

    try:
        message = Mail(
            from_email=config["from_email"],
            to_emails=target,
            subject="ETF Monitor Report",
            plain_text_content="Please find attached the ETF Monitor report."
        )

        # Attach the PDF report
        with open(report_path, "rb") as f:
            data = f.read()
        encoded = base64.b64encode(data).decode()
        attachment = Attachment(
            FileContent(encoded),
            FileName("etf_report.pdf"),
            FileType("application/pdf"),
            Disposition("attachment")
        )
        message.attachment = attachment

        sg = SendGridAPIClient(config["api_key"])
        # Optional: set EU data residency if needed
        # if os.environ.get("SENDGRID_EU_RESIDENCY", "false").lower() == "true":
        #     sg.set_sendgrid_data_residency("eu")
        response = sg.send(message)

        # Log response details for debugging
        logger.info(f"SendGrid report response: status={response.status_code}, body={getattr(response, 'body', 'No body')}")

        if response.status_code == 202:
            logger.info(f"Report email sent to {target} via SendGrid")
            return True
        else:
            logger.error(f"SendGrid returned unexpected status for report: {response.status_code}")
            logger.error(f"Response body: {getattr(response, 'body', 'No body')}")
            return False

    except FileNotFoundError:
        logger.error(f"Report file not found: {report_path}")
        return False
    except Exception as exc:
        logger.error(f"Failed to send report email via SendGrid: {type(exc).__name__}: {exc}")
        return False


def test_connection() -> bool:
    """Test SendGrid configuration by verifying API key format."""
    config = _get_sendgrid_config()
    if not all([config["api_key"], config["from_email"], config["notify_email"]]):
        logger.warning("SendGrid not fully configured — cannot test connection")
        return False

    # Basic validation: SendGrid API keys start with SG.
    api_key = config["api_key"]
    if not api_key.startswith("SG."):
        logger.warning("SendGrid API key doesn't appear to be valid (should start with 'SG.')")
        # Don't return False here - some keys might be different format, let SendGrid validate
        # but warn the user

    logger.info("SendGrid configuration appears valid")
    return True