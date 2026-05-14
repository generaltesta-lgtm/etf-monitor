"""ETF data fetching module using yfinance.

Provides functions for fetching current prices, historical data, and ETF metadata.
All external calls are wrapped in try/except blocks returning error dicts.
"""

from typing import Any, Dict, List

import pandas as pd
import yfinance as yf

_CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CHF": "Fr",
    "CAD": "C$",
    "AUD": "A$",
    "HKD": "HK$",
    "SGD": "S$",
    "SEK": "kr",
    "NOK": "kr",
    "DKK": "kr",
    "NZD": "NZ$",
    "MXN": "MX$",
    "CNY": "¥",
    "INR": "₹",
    "KRW": "₩",
    "BRL": "R$",
    "ZAR": "R",
    "TRY": "₺",
    "PLN": "zł",
    "RUB": "₽",
}


def currency_symbol(currency_code: str) -> str:
    """Return the currency symbol for a given ISO currency code.

    Args:
        currency_code: ISO 4217 currency code (e.g. 'USD', 'EUR', 'GBP').

    Returns:
        Currency symbol string. Falls back to the code itself if unknown.
    """
    return _CURRENCY_SYMBOLS.get(currency_code.upper(), currency_code)


def fetch_current_price(ticker: str) -> Dict[str, Any]:
    """Fetch the latest price data for a given ticker.

    Args:
        ticker: Stock/ETF ticker symbol.

    Returns:
        Dict with keys: price, volume, change_pct, high_52w, low_52w, currency.
        On error, returns {"error": "..."}.
    """
    try:
        etf = yf.Ticker(ticker)
        hist = etf.history(period="2d")
        if hist.empty:
            return {"error": f"No price data found for {ticker}"}

        latest = hist.iloc[-1]
        price = float(latest["Close"])
        volume = float(latest["Volume"]) if "Volume" in latest and pd.notna(latest["Volume"]) else 0.0

        change_pct = 0.0
        if len(hist) >= 2:
            prev_close = float(hist.iloc[-2]["Close"])
            if prev_close > 0:
                change_pct = ((price - prev_close) / prev_close) * 100.0

        info = etf.info or {}
        currency = info.get("currency", "USD")
        high_52w = info.get("fiftyTwoWeekHigh", 0.0) or 0.0
        low_52w = info.get("fiftyTwoWeekLow", 0.0) or 0.0

        return {
            "price": round(price, 4),
            "volume": int(volume),
            "change_pct": round(change_pct, 2),
            "high_52w": round(high_52w, 2) if high_52w else None,
            "low_52w": round(low_52w, 2) if low_52w else None,
            "currency": currency,
        }
    except Exception as exc:
        return {"error": f"Failed to fetch price for {ticker}: {str(exc)}"}


def fetch_history(ticker: str, period: str = "1mo") -> pd.DataFrame:
    """Fetch historical price data for a given ticker.

    Args:
        ticker: Stock/ETF ticker symbol.
        period: Time period string (1d, 5d, 1mo, 3mo, 6mo, 1y, 5y).

    Returns:
        DataFrame with columns: Date, Open, High, Low, Close, Volume.
        Empty DataFrame on error.
    """
    valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "5y", "max"]
    if period not in valid_periods:
        period = "1mo"

    try:
        etf = yf.Ticker(ticker)
        df = etf.history(period=period)
        if df.empty:
            return pd.DataFrame()
        return df
    except Exception:
        return pd.DataFrame()


def fetch_info(ticker: str) -> Dict[str, Any]:
    """Fetch full metadata for a given ticker.

    Args:
        ticker: Stock/ETF ticker symbol.

    Returns:
        Dict with metadata keys (longName, expenseRatio, totalAssets, currency, etc.).
        Returns {"error": "..."} on failure.
    """
    try:
        etf = yf.Ticker(ticker)
        info = etf.info or {}
        return {
            "name": info.get("longName", info.get("shortName", ticker)),
            "expense_ratio": info.get("expenseRatio", info.get("annualReportExpenseRatio", 0)),
            "aum": info.get("totalAssets", info.get("navPrice", 0)),
            "currency": info.get("currency", "USD"),
            "category": info.get("category", "N/A"),
            "ytd_return": info.get("ytdReturn", info.get("fundPerformance", 0)),
            "bid": info.get("bid", 0),
            "ask": info.get("ask", 0),
            "previous_close": info.get("previousClose", 0),
            "day_range": info.get("dayRange", "N/A"),
            "year_range": info.get("fiftyTwoWeekRange", "N/A"),
        }
    except Exception as exc:
        return {"error": f"Failed to fetch info for {ticker}: {str(exc)}"}


def validate_ticker(ticker: str) -> bool:
    """Check if a ticker exists on Yahoo Finance.

    Args:
        ticker: Stock/ETF ticker symbol to validate.

    Returns:
        True if the ticker returns valid price data, False otherwise.
    """
    try:
        etf = yf.Ticker(ticker.strip())
        hist = etf.history(period="1d")
        return not hist.empty
    except Exception:
        return False


def batch_fetch_prices(tickers: List[str]) -> Dict[str, Dict[str, Any]]:
    """Fetch current prices for multiple tickers efficiently.

    Uses yfinance's batch download capability.

    Args:
        tickers: List of ticker symbols.

    Returns:
        Dict mapping ticker -> price data dict.
    """
    results: Dict[str, Dict[str, Any]] = {}
    if not tickers:
        return results

    try:
        data = yf.download(tickers=" ".join(tickers), period="2d", group_by="ticker", threads=True)
        if data.empty:
            return {t: {"error": "No data returned"} for t in tickers}

        if len(tickers) == 1:
            ticker = tickers[0]
            latest = data.iloc[-1] if len(data) > 0 else data
            price = float(latest.get("Close", 0))
            volume = float(latest.get("Volume", 0)) if pd.notna(latest.get("Volume", 0)) else 0.0
            change_pct = 0.0
            if len(data) >= 2:
                prev = float(data.iloc[-2].get("Close", 0))
                if prev > 0:
                    change_pct = ((price - prev) / prev) * 100.0
            results[ticker] = {
                "price": round(price, 4),
                "volume": int(volume),
                "change_pct": round(change_pct, 2),
                "currency": "USD",
            }
        else:
            for ticker in tickers:
                try:
                    if ticker in data.columns.levels[1] if hasattr(data.columns, "levels") else False:
                        tkr_data = data[ticker]
                        close_col = "Close"
                        vol_col = "Volume"
                        if close_col not in tkr_data.columns:
                            close_col = tkr_data.columns[0]
                        latest = tkr_data.iloc[-1] if len(tkr_data) > 0 else tkr_data
                        price = float(latest.get(close_col, 0))
                        volume = float(latest.get(vol_col, 0)) if pd.notna(latest.get(vol_col, 0)) else 0.0
                        change_pct = 0.0
                        if len(tkr_data) >= 2:
                            prev = float(tkr_data.iloc[-2].get(close_col, 0))
                            if prev > 0:
                                change_pct = ((price - prev) / prev) * 100.0
                        results[ticker] = {
                            "price": round(price, 4),
                            "volume": int(volume),
                            "change_pct": round(change_pct, 2),
                            "currency": "USD",
                        }
                    else:
                        results[ticker] = {"error": "Ticker not found in batch data"}
                except Exception as exc:
                    results[ticker] = {"error": str(exc)}
    except Exception as exc:
        return {t: {"error": str(exc)} for t in tickers}

    return results