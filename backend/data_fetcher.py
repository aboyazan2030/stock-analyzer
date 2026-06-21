"""
Stock Data Fetcher - Alpha Vantage API
Supports Saudi (Tadawul .SR) and US markets
"""
import requests
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

AV_BASE = "https://www.alphavantage.co/query"


def get_api_key() -> str:
    import streamlit as st
    try:
        return st.secrets.get("ALPHA_VANTAGE_KEY", os.environ.get("ALPHA_VANTAGE_KEY", ""))
    except Exception:
        return os.environ.get("ALPHA_VANTAGE_KEY", "")


def to_yahoo_symbol(symbol: str, market: str) -> str:
    s = symbol.upper().strip()
    if market == "us":
        return s
    if s.isdigit() and len(s) == 4:
        return f"{s}.SR"
    if s.endswith(".SR") or s.endswith(".SE"):
        return s
    return f"{s}.SR"


def to_av_symbol(symbol: str, market: str) -> str:
    """Alpha Vantage uses different format for Saudi stocks"""
    s = symbol.upper().strip()
    if market == "us":
        return s
    if s.isdigit() and len(s) == 4:
        return f"{s}.SR"
    return s


class StockDataService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0"
        })

    def get_all(self, symbol: str, market: str) -> Dict[str, Any]:
        api_key = get_api_key()
        av_sym = to_av_symbol(symbol, market)
        yahoo_sym = to_yahoo_symbol(symbol, market)

        logger.info(f"Fetching: {symbol} -> {av_sym}")

        out = {
            "requested_symbol": symbol.upper(),
            "yahoo_symbol": yahoo_sym,
            "market": market,
            "fetched_at": datetime.now().isoformat(),
            "quote": None,
            "chart": None,
            "fundamentals": None,
            "news": [],
            "errors": [],
            "data_quality": "none",
        }

        if not api_key:
            raise ValueError("مفتاح Alpha Vantage API غير موجود. أضفه في Streamlit Secrets.")

        # 1. Quote - Global Quote
        try:
            r = self.session.get(AV_BASE, params={
                "function": "GLOBAL_QUOTE",
                "symbol": av_sym,
                "apikey": api_key,
            }, timeout=15)
            data = r.json()
            gq = data.get("Global Quote", {})

            if gq and gq.get("05. price"):
                price = float(gq.get("05. price", 0))
                prev_close = float(gq.get("08. previous close", 0))
                change = float(gq.get("09. change", 0))
                change_pct = gq.get("10. change percent", "0%").replace("%", "")

                out["quote"] = {
                    "symbol": yahoo_sym,
                    "name": symbol.upper(),
                    "exchange": "SR" if market == "saudi" else "US",
                    "currency": "SAR" if market == "saudi" else "USD",
                    "price": price,
                    "prev_close": prev_close,
                    "open": float(gq.get("02. open", 0)),
                    "day_high": float(gq.get("03. high", 0)),
                    "day_low": float(gq.get("04. low", 0)),
                    "change": change,
                    "change_pct": float(change_pct) if change_pct else 0,
                    "volume": int(gq.get("06. volume", 0)),
                    "market_cap": None,
                    "week52_high": None,
                    "week52_low": None,
                    "pe_ratio": None,
                    "forward_pe": None,
                    "pb_ratio": None,
                    "div_yield": None,
                }
                logger.info(f"Quote OK: {av_sym} @ {price}")
            else:
                out["errors"].append("price_unavailable")
                logger.warning(f"No quote data for {av_sym}. Response: {data}")
        except Exception as e:
            out["errors"].append("price_unavailable")
            logger.error(f"Quote error: {e}")

        # 2. Chart - Daily adjusted
        try:
            r = self.session.get(AV_BASE, params={
                "function": "TIME_SERIES_DAILY",
                "symbol": av_sym,
                "outputsize": "compact",
                "apikey": api_key,
            }, timeout=20)
            data = r.json()
            ts = data.get("Time Series (Daily)", {})

            if ts:
                dates = sorted(ts.keys())[-120:]
                out["chart"] = {
                    "symbol": yahoo_sym,
                    "currency": "SAR" if market == "saudi" else "USD",
                    "dates":   dates,
                    "opens":   [float(ts[d]["1. open"])   for d in dates],
                    "highs":   [float(ts[d]["2. high"])   for d in dates],
                    "lows":    [float(ts[d]["3. low"])    for d in dates],
                    "closes":  [float(ts[d]["4. close"])  for d in dates],
                    "volumes": [int(ts[d]["5. volume"])   for d in dates],
                    "count":   len(dates),
                }
                logger.info(f"Chart OK: {av_sym} ({len(dates)} bars)")
            else:
                out["errors"].append("chart_unavailable")
                logger.warning(f"No chart data for {av_sym}")
        except Exception as e:
            out["errors"].append("chart_unavailable")
            logger.error(f"Chart error: {e}")

        # 3. Company Overview (Fundamentals) - US stocks only
        if market == "us":
            try:
                r = self.session.get(AV_BASE, params={
                    "function": "OVERVIEW",
                    "symbol": av_sym,
                    "apikey": api_key,
                }, timeout=15)
                ov = r.json()

                if ov and ov.get("Symbol"):
                    def safe_float(v):
                        try: return float(v) if v and v != "None" else None
                        except: return None

                    fins = {
                        "sector":         ov.get("Sector", ""),
                        "industry":       ov.get("Industry", ""),
                        "description":    ov.get("Description", "")[:600],
                        "country":        ov.get("Country", ""),
                        "employees":      safe_float(ov.get("FullTimeEmployees")),
                        "pe_ratio":       safe_float(ov.get("TrailingPE")),
                        "forward_pe":     safe_float(ov.get("ForwardPE")),
                        "pb_ratio":       safe_float(ov.get("PriceToBookRatio")),
                        "beta":           safe_float(ov.get("Beta")),
                        "div_yield":      safe_float(ov.get("DividendYield")),
                        "payout_ratio":   safe_float(ov.get("PayoutRatio")),
                        "roe":            safe_float(ov.get("ReturnOnEquityTTM")),
                        "roa":            safe_float(ov.get("ReturnOnAssetsTTM")),
                        "gross_margin":   safe_float(ov.get("GrossProfitTTM")),
                        "op_margin":      safe_float(ov.get("OperatingMarginTTM")),
                        "net_margin":     safe_float(ov.get("ProfitMargin")),
                        "rev_growth":     safe_float(ov.get("QuarterlyRevenueGrowthYOY")),
                        "earn_growth":    safe_float(ov.get("QuarterlyEarningsGrowthYOY")),
                        "debt_to_equity": safe_float(ov.get("DebtToEquityRatio")),
                        "eps_ttm":        safe_float(ov.get("EPS")),
                        "book_value":     safe_float(ov.get("BookValue")),
                        "target_price":   safe_float(ov.get("AnalystTargetPrice")),
                        "analyst_rec":    ov.get("AnalystRatingStrongBuy", ""),
                        "free_cash_flow": safe_float(ov.get("OperatingCashflowTTM")),
                        "total_revenue":  safe_float(ov.get("RevenueTTM")),
                        "market_cap":     safe_float(ov.get("MarketCapitalization")),
                        "week52_high":    safe_float(ov.get("52WeekHigh")),
                        "week52_low":     safe_float(ov.get("52WeekLow")),
                        "shares":         safe_float(ov.get("SharesOutstanding")),
                    }
                    out["fundamentals"] = fins

                    # Update quote with better data
                    if out["quote"]:
                        out["quote"]["market_cap"] = fins.get("market_cap")
                        out["quote"]["week52_high"] = fins.get("week52_high")
                        out["quote"]["week52_low"] = fins.get("week52_low")
                        out["quote"]["pe_ratio"] = fins.get("pe_ratio")
                        out["quote"]["pb_ratio"] = fins.get("pb_ratio")
                        out["quote"]["div_yield"] = fins.get("div_yield")
                        out["quote"]["name"] = ov.get("Name", symbol)

                    logger.info(f"Fundamentals OK: {av_sym}")
                else:
                    out["errors"].append("fundamentals_unavailable")
            except Exception as e:
                out["errors"].append("fundamentals_unavailable")
                logger.error(f"Fundamentals error: {e}")
        else:
            out["errors"].append("fundamentals_unavailable")

        # Quality check
        if not out["quote"] and not out["chart"]:
            raise ValueError(
                f"لم يتم العثور على بيانات للرمز '{symbol}'. "
                "تأكد من صحة الرمز والسوق، أو تحقق من مفتاح API."
            )

        if out["quote"] and out["chart"]:
            out["data_quality"] = "full"
        elif out["quote"] or out["chart"]:
            out["data_quality"] = "partial"

        logger.info(f"Done: {av_sym} quality={out['data_quality']}")
        return out
