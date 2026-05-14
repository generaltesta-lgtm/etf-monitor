# 📈 ETF Monitor

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Deploy on Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E?logo=railway&logoColor=white)](https://railway.app)

A production-ready web application for monitoring ETF prices, setting automated price alerts, generating PDF/CSV reports, and receiving email notifications.

## Features

- **Live Price Tracking** — Real-time ETF prices via Yahoo Finance (yfinance)
- **Price Charts** — Interactive Plotly candlestick and multi-ETF comparison charts
- **Automated Checks** — Background scheduler (15 min, 30 min, 1h, 4h, daily)
- **Price Alerts** — Trigger notifications when price goes above/below thresholds or daily change exceeds a percentage
- **Email Notifications** — Styled HTML alerts via SMTP (Gmail compatible)
- **PDF Reports** — Professional reports with cover page, price history tables, and stats
- **CSV Export** — Download price history as flat CSV
- **Portfolio Tracking** — Optional quantity tracking with portfolio value calculation
- **Bulk Import** — Add multiple ETFs at once
- **Data Management** — Export all data as JSON, clear old history, reset settings

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| Data Source | Yahoo Finance (yfinance) |
| Database | SQLite (SQLAlchemy ORM) |
| Charts | Plotly |
| Scheduler | APScheduler |
| PDF | fpdf2 |
| Email | smtplib (TLS) |
| Deployment | Railway.app |

## Local Setup

### Prerequisites

- Python 3.11+
- pip

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/etf-monitor.git
cd etf-monitor
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure environment**

```bash
cp .env.example .env
```

Edit `.env` with your SMTP credentials (optional — the app works without email).

4. **Run the app**

```bash
streamlit run app.py
```

5. **Open in browser**

Navigate to `http://localhost:8501`.

## Screenshots

*Dashboard view showing ETF metrics and comparison charts (coming soon)*
*ETF Manager with live ticker preview (coming soon)*
*Alerts configuration panel (coming soon)*
*Report generation page (coming soon)*

## Railway Deployment

Deploy to Railway in 5 minutes:

1. **Fork this repo** on GitHub
2. **Create a Railway account** at [railway.app](https://railway.app)
3. **New Project** → **Deploy from GitHub repo**
4. **Add environment variables** (see `.env.example`)
5. **Add a Volume** for the SQLite database:
   - Settings → Volume → Add Volume
   - Mount path: `/app/data`
6. **Deploy** — Railway auto-detects the Procfile
7. **Access** — Railway provides a `*.railway.app` URL

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SMTP_HOST` | SMTP server hostname | No |
| `SMTP_PORT` | SMTP server port (default: 587) | No |
| `SMTP_USER` | SMTP username/email | No |
| `SMTP_PASSWORD` | SMTP app password | No |
| `NOTIFY_EMAIL` | Alert recipient email | No |
| `DATABASE_URL` | Database URL (default: sqlite) | No |
| `CHECK_INTERVAL_MINUTES` | Price check interval | No |

### Email Configuration (Gmail)

To enable email alerts with Gmail:

1. Enable [2-Factor Authentication](https://myaccount.google.com/security) on your Google Account
2. Generate an [App Password](https://myaccount.google.com/apppasswords)
3. Use the app password in your `.env` or Railway variables:
   - `SMTP_HOST=smtp.gmail.com`
   - `SMTP_PORT=587`
   - `SMTP_USER=your.email@gmail.com`
   - `SMTP_PASSWORD=your_16_char_app_password`
   - `NOTIFY_EMAIL=alerts@example.com`

## Project Structure

```
etf-monitor/
├── app.py                  # Streamlit entry point
├── core/
│   ├── database.py         # SQLAlchemy models & DB init
│   ├── fetcher.py          # yfinance price fetching
│   ├── scheduler.py        # APScheduler background jobs
│   ├── notifier.py         # Email notifications
│   └── reporter.py         # PDF & CSV report generation
├── pages/
│   ├── 01_Dashboard.py     # Main overview
│   ├── 02_ETF_Manager.py   # Add/edit/delete ETFs
│   ├── 03_Alerts.py        # Price alert management
│   ├── 04_Reports.py       # Report generation
│   └── 05_Settings.py      # Configuration
├── components/
│   ├── etf_card.py         # ETF summary card
│   ├── price_chart.py      # Plotly charts
│   └── sidebar.py          # Sidebar component
└── assets/
    └── style.css           # Custom stylesheet
```

## Usage Guide

### Adding ETFs
1. Go to **ETF Manager** → Enter a ticker (e.g., `SPY`, `QQQ`, `VWRL.L`)
2. Optionally set a display name and quantity held
3. Click **Add ETF** — live preview shows current price
4. Use **Bulk Import** to add multiple tickers at once

### Setting Alerts
1. Go to **Alerts** → Select an ETF
2. Choose condition: Price Above / Price Below / Daily Change %
3. Set the threshold value
4. Click **Create Alert** — you'll be notified when triggered

### Generating Reports
1. Go to **Reports** → Select date range and ETFs
2. Choose PDF or CSV format
3. Click **Generate Report** → Download directly or send via email

### Configuring the Scheduler
1. Go to **Settings** → Select check frequency (15 min to daily)
2. The scheduler automatically fetches prices and evaluates alerts
3. Next/Last run times are shown in the sidebar

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Acknowledgments

- [Streamlit](https://streamlit.io) for the amazing web framework
- [yfinance](https://github.com/ranaroussi/yfinance) for Yahoo Finance data
- [Plotly](https://plotly.com) for interactive charts
- [APScheduler](https://apscheduler.readthedocs.io) for background scheduling