"""Background scheduler module using APScheduler.

Handles periodic ETF price fetching, alert evaluation, and logging.
Runs in a background thread to avoid blocking Streamlit's render loop.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.database import Alert, ETF, NotificationLog, PriceHistory, Setting, get_session
from core.fetcher import fetch_current_price
from core.notifier import send_alert_email

logger = logging.getLogger(__name__)

scheduler: Optional[BackgroundScheduler] = None
_last_run: Optional[datetime] = None
_next_run: Optional[datetime] = None
_interval_minutes: int = 60


def _check_alerts(etf_id: int, ticker: str, current_price: float, change_pct: float) -> None:
    """Evaluate all active alerts for an ETF and trigger notifications."""
    session = next(get_session())
    try:
        alerts = (
            session.query(Alert)
            .filter(Alert.etf_id == etf_id, Alert.is_active.is_(True))
            .all()
        )
        etf = session.query(ETF).filter(ETF.id == etf_id).first()

        for alert in alerts:
            triggered = False
            condition_msg = ""

            if alert.alert_type == "ABOVE" and current_price > alert.threshold:
                triggered = True
                condition_msg = (
                    f"Price ${current_price:.2f} is above ${alert.threshold:.2f}"
                )
            elif alert.alert_type == "BELOW" and current_price < alert.threshold:
                triggered = True
                condition_msg = (
                    f"Price ${current_price:.2f} is below ${alert.threshold:.2f}"
                )
            elif alert.alert_type == "CHANGE_PCT" and abs(change_pct) > alert.threshold:
                triggered = True
                condition_msg = (
                    f"Daily change {change_pct:+.2f}% exceeds {alert.threshold:.2f}%"
                )

            if triggered:
                alert.triggered_at = datetime.now(timezone.utc)
                message = (
                    f"Alert triggered for {ticker}: {condition_msg}. "
                    f"Current price: ${current_price:.2f}, Change: {change_pct:+.2f}%"
                )
                log = NotificationLog(alert_id=alert.id, message=message, status="OK")
                session.add(log)
                session.commit()

                # Send email notification
                if etf:
                    send_alert_email(
                        alert=alert,
                        ticker=ticker,
                        etf_name=etf.name or ticker,
                        current_price=current_price,
                        change_pct=change_pct,
                    )
    except Exception as exc:
        logger.error("Error checking alerts for ETF %s: %s", ticker, exc)
        session.rollback()
    finally:
        session.close()


def _fetch_and_store() -> None:
    """Main scheduled job: fetch prices for all active ETFs and store to DB."""
    global _last_run, _next_run
    _last_run = datetime.now(timezone.utc)
    _next_run = _last_run + timedelta(minutes=_interval_minutes)

    session = next(get_session())
    try:
        etfs = session.query(ETF).filter(ETF.is_active.is_(True)).all()
        if not etfs:
            logger.info("No active ETFs to fetch")
            return

        for etf in etfs:
            try:
                data = fetch_current_price(etf.ticker)
                if "error" in data:
                    log = NotificationLog(
                        alert_id=None,
                        message=f"Fetch error for {etf.ticker}: {data['error']}",
                        status="ERROR",
                    )
                    session.add(log)
                    session.commit()
                    continue

                price_record = PriceHistory(
                    etf_id=etf.id,
                    price=data["price"],
                    volume=data["volume"],
                    change_pct=data["change_pct"],
                )
                session.add(price_record)
                session.commit()

                _check_alerts(
                    etf_id=etf.id,
                    ticker=etf.ticker,
                    current_price=data["price"],
                    change_pct=data["change_pct"],
                )
            except Exception as exc:
                logger.error("Error processing ETF %s: %s", etf.ticker, exc)
                session.rollback()

    except Exception as exc:
        logger.error("Scheduler run error: %s", exc)
    finally:
        session.close()


def start_scheduler() -> None:
    """Start the background scheduler. Idempotent (won't double-start)."""
    global scheduler, _interval_minutes

    if scheduler is not None and scheduler.running:
        logger.info("Scheduler already running")
        return

    session = next(get_session())
    try:
        setting = session.query(Setting).filter(Setting.key == "check_interval_minutes").first()
        if setting and setting.value:
            _interval_minutes = int(setting.value)
    except Exception:
        _interval_minutes = 60
    finally:
        session.close()

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        _fetch_and_store,
        trigger=IntervalTrigger(minutes=_interval_minutes),
        id="etf_fetch_job",
        name="Fetch ETF Prices",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started with %d-minute interval", _interval_minutes)


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("Scheduler stopped")


def set_interval(minutes: int) -> None:
    """Change the check interval. Reschedules the job."""
    global scheduler, _interval_minutes, _next_run

    _interval_minutes = max(1, minutes)

    session = next(get_session())
    try:
        setting = session.query(Setting).filter(Setting.key == "check_interval_minutes").first()
        if setting:
            setting.value = str(_interval_minutes)
        else:
            session.add(Setting(key="check_interval_minutes", value=str(_interval_minutes)))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

    if scheduler and scheduler.running:
        scheduler.reschedule_job(
            "etf_fetch_job",
            trigger=IntervalTrigger(minutes=_interval_minutes),
        )
        _next_run = datetime.now(timezone.utc) + timedelta(minutes=_interval_minutes)


def get_next_run() -> Optional[datetime]:
    """Get the next scheduled run time."""
    global _next_run
    return _next_run


def get_last_run() -> Optional[datetime]:
    """Get the last run time."""
    global _last_run
    return _last_run


def get_scheduler_status() -> Dict[str, Any]:
    """Return current scheduler status as a dict."""
    global scheduler, _last_run, _next_run, _interval_minutes
    return {
        "running": scheduler is not None and scheduler.running,
        "interval_minutes": _interval_minutes,
        "last_run": _last_run,
        "next_run": _next_run,
    }