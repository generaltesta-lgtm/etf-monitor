---
name: dashboard-chart-fix
description: Fixed Dashboard chart to show actual prices for single ETF, normalized comparison for multiple ETFs
metadata:
  type: project
---

Fixed the Dashboard's price chart display to appropriately show either actual prices (for single ETF) or normalized comparison (for multiple ETFs).

**Problem:** The chart was always showing normalized prices (scaled to 0-100), making it confusing when viewing a single ETF as users expected to see actual price values.

**Root Causes:**
1. Missing import for `render_price_chart` function in pages/01_Dashboard.py
2. Chart logic always used `render_multi_etf_chart` which normalizes to 100, regardless of ETF count

**Solution Implemented:**
1. Added `render_price_chart` to imports from components.price_chart
2. Implemented intelligent chart selection logic:
   - **Single ETF**: Uses `render_price_chart()` to show actual candlestick chart with real prices
   - **Multiple ETFs (2+)**: Uses `render_multi_etf_chart()` showing normalized comparison (starting at 100) with explanatory caption
3. Updated UI text from "Price Comparison" to "Price Chart" for clarity
4. Added descriptive caption when showing normalized comparison: "Showing normalized performance (starting at 100) for comparison"

**Files Modified:**
- `etf-monitor/pages/01_Dashboard.py`: Fixed import and chart display logic

**Verification:** 
- With single ETF (e.g., VWCE.MI): Chart shows actual prices (~159.37) with proper currency Y-axis
- With multiple ETFs: Chart shows normalized performance for relative comparison
- Title accurately reflects chart type and period
- Preserves existing functionality while improving user experience

This fix ensures users see meaningful price data whether they're tracking one ETF or comparing multiple funds.