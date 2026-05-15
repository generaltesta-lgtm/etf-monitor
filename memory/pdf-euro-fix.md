---
name: pdf-euro-fix
description: Fixed PDF generation Unicode encoding error for Euro and other currency symbols
metadata:
  type: project
---

Fixed FPDFUnicodeEncodingException when generating PDF reports with currency symbols like Euro (€), Pound (£), etc. The issue occurred because fpdf2's standard Helvetica font doesn't support Unicode currency symbols.

**Problem:** 
- PDF generation failed with: `fpdf.errors.FPDFUnicodeEncodingException: Character "€" at index 0 in text is outside the range of characters supported by the font used: "helvetica"`
- This happened when displaying prices for ETFs traded in EUR (like VWCE.MI) or other currencies with Unicode symbols

**Root Cause:**
The reporter.py was using `currency_symbol()` function which returns Unicode symbols (€, £, ¥, etc.) that aren't supported by fpdf2's default Helvetica font.

**Solution:**
Modified core/reporter.py to use currency codes (EUR, GBP, USD, etc.) instead of Unicode symbols in PDF reports:
- Line 97: Changed `sym = currency_symbol(etf.currency)` to `currency_code = etf.currency`  
- Line 102: Changed `f"{sym}{rec.price:.2f}"` to `f"{currency_code}{rec.price:.2f}"`
- Lines 123-126: Updated statistics section to use currency codes instead of symbols

**Files Modified:**
- `etf-monitor/core/reporter.py`: Replaced currency symbols with currency codes in PDF generation

**Verification:**
- PDF reports now generate successfully for ETFs in any currency
- Prices display as "EUR159.37" instead of "€159.37" (functional equivalent)
- All other PDF functionality (charts, tables, formatting) preserved
- No impact on CSV reports or web interface display

**Alternative Considered:** Using Unicode fonts like DejaVuSans with fpdf2 would have preserved symbols but added complexity. Currency codes are clearer for financial reports and avoid font dependency issues.