"""ETF Manager page — add, edit, delete, and bulk import ETFs."""

import streamlit as st

from core.database import ETF, get_session
from core.fetcher import currency_symbol, fetch_current_price, fetch_info, validate_ticker
from components.etf_card import render_etf_card

st.markdown("# 📋 ETF Manager")
st.markdown("---")

session = next(get_session())

# ── Add New ETF ──────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1.5])

with col_left:
    st.markdown("<h3 class='section-header'>➕ Add New ETF</h3>", unsafe_allow_html=True)

    with st.form("add_etf_form", clear_on_submit=True):
        ticker_input = st.text_input(
            "Ticker Symbol",
            placeholder="e.g. SPY, QQQ, VWRL.L",
            help="Enter a valid Yahoo Finance ticker",
        )

        display_name = st.text_input(
            "Display Name (optional)",
            placeholder="Auto-fetched if blank",
        )

        quantity = st.number_input(
            "Quantity Held (optional)",
            min_value=0.0,
            step=0.01,
            value=0.0,
            format="%.4f",
        )

        submitted = st.form_submit_button("Add ETF", type="primary", use_container_width=True)

        if submitted and ticker_input:
            ticker = ticker_input.strip().upper()
            if not ticker:
                st.error("Please enter a ticker symbol")
            else:
                # Check if already tracked
                existing = session.query(ETF).filter(ETF.ticker == ticker).first()
                if existing:
                    if not existing.is_active:
                        existing.is_active = True
                        if display_name:
                            existing.name = display_name
                        existing.quantity = quantity
                        session.commit()
                        st.success(f"Reactivated {ticker}")
                        st.rerun()
                    else:
                        st.warning(f"{ticker} is already tracked")
                else:
                    with st.spinner(f"Validating {ticker}..."):
                        is_valid = validate_ticker(ticker)
                        if not is_valid:
                            st.error(f"Ticker '{ticker}' not found on Yahoo Finance")
                        else:
                            info = fetch_info(ticker)
                            name = display_name or info.get("name", ticker)
                            currency = info.get("currency", "USD")
                            new_etf = ETF(
                                ticker=ticker,
                                name=name,
                                currency=currency,
                                quantity=quantity,
                                is_active=True,
                            )
                            session.add(new_etf)
                            session.commit()
                            st.success(f"✅ {ticker} ({name}) added successfully!")
                            st.rerun()

    # Ticker preview
    if ticker_input and ticker_input.strip():
        ticker = ticker_input.strip().upper()
        data = fetch_current_price(ticker)
        if "error" not in data:
            info = fetch_info(ticker)
            name = info.get("name", ticker)
            render_etf_card(
                ticker=ticker,
                name=name,
                price=data["price"],
                change_pct=data["change_pct"],
                currency=data.get("currency", "USD"),
            )

    # Bulk import
    st.markdown("---")
    st.markdown("<h3 class='section-header'>📦 Bulk Import</h3>", unsafe_allow_html=True)
    bulk_input = st.text_area(
        "Paste comma-separated tickers",
        placeholder="SPY, QQQ, IWM, EEM, VTI",
        help="Enter tickers separated by commas or newlines",
    )
    if st.button("Import Tickers", type="secondary"):
        if bulk_input:
            tickers = [t.strip().upper() for t in bulk_input.replace("\n", ",").split(",") if t.strip()]
            added = 0
            skipped = 0
            errors = 0
            for t in tickers:
                existing = session.query(ETF).filter(ETF.ticker == t).first()
                if existing:
                    skipped += 1
                    continue
                if not validate_ticker(t):
                    errors += 1
                    continue
                info = fetch_info(t)
                name = info.get("name", t)
                new_etf = ETF(ticker=t, name=name, currency=info.get("currency", "USD"))
                session.add(new_etf)
                added += 1
            session.commit()
            if added > 0:
                st.success(f"✅ Added {added} new ETF(s)")
            if skipped > 0:
                st.info(f"⏭️ {skipped} already tracked (skipped)")
            if errors > 0:
                st.error(f"❌ {errors} invalid ticker(s)")
            if added > 0:
                st.rerun()
        else:
            st.warning("Please enter at least one ticker")

# ── Tracked ETFs Table ───────────────────────────────────────────────────────
with col_right:
    st.markdown("<h3 class='section-header'>📋 Tracked ETFs</h3>", unsafe_allow_html=True)

    etfs = session.query(ETF).filter(ETF.is_active.is_(True)).order_by(ETF.ticker).all()

    if not etfs:
        st.info("No ETFs tracked yet. Add one on the left.")
    else:
        for etf in etfs:
            data = fetch_current_price(etf.ticker)
            price = data.get("price", 0) if "error" not in data else None
            change = data.get("change_pct", 0) if "error" not in data else None

            with st.container(border=True):
                cols = st.columns([3, 1, 1, 0.8, 0.8])
                with cols[0]:
                    st.markdown(f"**{etf.ticker}**")
                    st.caption(etf.name or "")

                with cols[1]:
                    if price is not None:
                        st.markdown(f"**{currency_symbol(etf.currency)}{price:.2f}**")
                    else:
                        st.markdown("N/A")
                    st.caption(etf.currency or "USD")

                with cols[2]:
                    if change is not None:
                        cls = "price-up" if change >= 0 else "price-down"
                        sign = "+" if change >= 0 else ""
                        st.markdown(f"<span class='{cls}'>{sign}{change:.2f}%</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("N/A")

                with cols[3]:
                    edit_key = f"edit_{etf.id}"
                    if st.button("✏️", key=f"edit_btn_{etf.id}", help="Edit"):
                        st.session_state[edit_key] = not st.session_state.get(edit_key, False)

                with cols[4]:
                    if st.button("🗑️", key=f"del_btn_{etf.id}", help="Delete"):
                        # Soft delete: set inactive
                        etf.is_active = False
                        session.commit()
                        st.rerun()

                # Inline edit form
                edit_key = f"edit_{etf.id}"
                if st.session_state.get(edit_key, False):
                    with st.form(key=f"edit_form_{etf.id}"):
                        new_name = st.text_input("Name", value=etf.name or "")
                        new_qty = st.number_input("Quantity", value=etf.quantity or 0.0, step=0.01, format="%.4f")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.form_submit_button("💾 Save", type="primary"):
                                etf.name = new_name
                                etf.quantity = new_qty
                                session.commit()
                                st.session_state[edit_key] = False
                                st.success("Saved!")
                                st.rerun()
                        with c2:
                            if st.form_submit_button("Cancel"):
                                st.session_state[edit_key] = False
                                st.rerun()

session.close()