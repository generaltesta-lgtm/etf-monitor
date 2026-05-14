"""Database module for ETF Monitor.

SQLAlchemy ORM models and session management for SQLite.
Provides init_db(), get_session(), and typed model classes with seed data.
"""

import os
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, create_engine
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, relationship, sessionmaker

DB_DIR = os.environ.get("DB_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_NAME = "etf_monitor.db"
DB_PATH = os.path.join(DB_DIR, DB_NAME)
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class ETF(Base):
    """Model representing a tracked ETF."""

    __tablename__ = "etfs"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = Column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = Column(String(200), nullable=True)
    currency: Mapped[str] = Column(String(10), default="USD")
    quantity: Mapped[float] = Column(Float, default=0.0)
    added_at: Mapped[datetime] = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active: Mapped[bool] = Column(Boolean, default=True)

    price_history = relationship("PriceHistory", back_populates="etf", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="etf", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ETF(ticker={self.ticker}, name={self.name})>"


class PriceHistory(Base):
    """Model storing historical price data points."""

    __tablename__ = "price_history"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    etf_id: Mapped[int] = Column(Integer, ForeignKey("etfs.id"), nullable=False, index=True)
    price: Mapped[float] = Column(Float, nullable=False)
    volume: Mapped[float] = Column(Float, default=0.0)
    change_pct: Mapped[float] = Column(Float, default=0.0)
    fetched_at: Mapped[datetime] = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    etf = relationship("ETF", back_populates="price_history")

    def __repr__(self) -> str:
        return f"<PriceHistory(etf_id={self.etf_id}, price={self.price}, fetched_at={self.fetched_at})>"


class Alert(Base):
    """Model representing a user-defined price alert."""

    __tablename__ = "alerts"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    etf_id: Mapped[int] = Column(Integer, ForeignKey("etfs.id"), nullable=False, index=True)
    alert_type: Mapped[str] = Column(String(20), nullable=False)  # ABOVE / BELOW / CHANGE_PCT
    threshold: Mapped[float] = Column(Float, nullable=False)
    custom_note: Mapped[str] = Column(Text, nullable=True)
    is_active: Mapped[bool] = Column(Boolean, default=True)
    triggered_at: Mapped[datetime] = Column(DateTime, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    etf = relationship("ETF", back_populates="alerts")
    notification_logs = relationship("NotificationLog", back_populates="alert", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Alert(etf_id={self.etf_id}, type={self.alert_type}, threshold={self.threshold})>"


class NotificationLog(Base):
    """Model logging sent notifications."""

    __tablename__ = "notifications_log"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = Column(Integer, ForeignKey("alerts.id"), nullable=True, index=True)
    message: Mapped[str] = Column(Text, nullable=False)
    sent_at: Mapped[datetime] = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status: Mapped[str] = Column(String(20), default="OK")  # OK / ERROR

    alert = relationship("Alert", back_populates="notification_logs")

    def __repr__(self) -> str:
        return f"<NotificationLog(id={self.id}, status={self.status})>"


class Setting(Base):
    """Key-value store for application settings."""

    __tablename__ = "settings"

    key: Mapped[str] = Column(String(100), primary_key=True)
    value: Mapped[str] = Column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<Setting(key={self.key}, value={self.value})>"


def init_db() -> None:
    """Initialize the database, create tables, and seed default data."""
    Base.metadata.create_all(bind=engine)
    _seed_default_etfs()
    _seed_default_settings()


def _seed_default_etfs() -> None:
    """Pre-load 5 popular ETFs if the table is empty."""
    session = next(get_session())
    try:
        existing = session.query(ETF).count()
        if existing > 0:
            return

        defaults = [
            {"ticker": "SPY", "name": "SPDR S&P 500 ETF Trust", "currency": "USD"},
            {"ticker": "QQQ", "name": "Invesco QQQ Trust (Nasdaq-100)", "currency": "USD"},
            {"ticker": "IWDA.AS", "name": "iShares Core MSCI World UCITS ETF", "currency": "USD"},
            {"ticker": "VWRL.L", "name": "Vanguard FTSE All-World UCITS ETF", "currency": "GBP"},
            {"ticker": "CSPX.L", "name": "iShares Core S&P 500 UCITS ETF", "currency": "GBP"},
        ]
        for etf_data in defaults:
            etf = ETF(**etf_data)
            session.add(etf)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _seed_default_settings() -> None:
    """Set default application settings if none exist."""
    session = next(get_session())
    try:
        existing = session.query(Setting).count()
        if existing > 0:
            return

        defaults = {
            "check_interval_minutes": "60",
            "notify_on_above": "true",
            "notify_on_below": "true",
            "notify_on_change_pct": "false",
            "data_retention_days": "90",
        }
        for key, value in defaults.items():
            setting = Setting(key=key, value=value)
            session.add(setting)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy Session, closing it after use."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()