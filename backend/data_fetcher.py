"""
Stock Data Fetcher - Stooq + yfinance fallback
Free, no API key needed, supports Saudi and US markets
"""
import requests
import logging
import io
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


def to_yahoo_symbol(symbol: str, market: str) -> str:
    s = symbol.upper().strip()
    if market == "us":
        return s
    if s.isdigit() and len(s) == 4:
        return f"{s}.SR"
    if s.endswith(".SR") or s.endswith(".SE"):
        return s
    return f"{s}.SR"


def to_stooq_symbol(symbol: str, market: str) -> str:
    s = symbol.upper().strip()
    if market == "us":
        return f"{s}.US"
    if s.isdigit() and len(s) == 4:
        return f"{s}.SR"
    return f"{s}.SR"


class StockDataService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def _fetch_stooq_history(self, stooq_sym: str) -> Optional[Dict]:
        """Fetch historical data from Stooq"""
        try:
            url = f"https://stooq.com/q/d/l/?s={stooq_sym.lower()}&i=d"
            r = self.session.get(url, timeout=15)
            if r.status_code != 200 or "No data" in r.text or len(r.text) < 50:
                return None

            lines = r.text.strip().split("\n")
            if len(lines) < 2:
                return None

            dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []
            for line in lines[1:]:
                parts = line.strip().split(",")
                if len(parts) < 5:
                    continue
                try:
                    dates.append(parts[0])
                    opens.append(float(parts[1]))
                    highs.append(float(parts[2]))
                    lows.append(float(parts[3]))
                    closes.append(float(parts[4]))
                    volumes.append(int(float(parts[5])) if len(parts) > 5 and parts[5].strip() else 0)
                except (ValueError, IndexError):
                    continue

            if not closes:
                return None

            # Keep last 120 days
            dates   = dates[-120:]
            opens   = opens[-120:]
            highs   = highs[-120:]
            lows    = lows[-120:]
            closes  = closes[-120:]
            volumes = volumes[-120:]

            return {
                "dates":   dates,
                "opens":   opens,
                "highs":   highs,
                "lows":    lows,
                "closes":  closes,
                "volumes": volumes,
                "count":   len(dates),
                "last_price": closes[-1] if closes else None,
                "last_date":  dates[-1]  if dates  else None,
            }
        except Exception as e:
            logger.warning(f"Stooq error for {stooq_sym}: {e}")
            return None

    def _fetch_yfinance(self, yahoo_sym: str) -> Optional[Dict]:
        """Fallback: fetch via yfinance"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(yahoo_sym)
            info   = ticker.info or {}
            hist   = ticker.history(period="6mo")

            result = {"info": info, "hist": hist}
            return result if (info.get("regularMarketPrice") or not hist.empty) else None
        except Exception as e:
            logger.warning(f"yfinance error for {yahoo_sym}: {e}")
            return None

    def get_all(self, symbol: str, market: str) -> Dict[str, Any]:
        yahoo_sym  = to_yahoo_symbol(symbol, market)
        stooq_sym  = to_stooq_symbol(symbol, market)

        logger.info(f"Fetching: {symbol} -> stooq={stooq_sym}, yahoo={yahoo_sym}")

        out = {
            "requested_symbol": symbol.upper(),
            "yahoo_symbol":     yahoo_sym,
            "market":           market,
            "fetched_at":       datetime.now().isoformat(),
            "quote":            None,
            "chart":            None,
            "fundamentals":     None,
            "news":             [],
            "errors":           [],
            "data_quality":     "none",
        }

        # ── 1. Try Stooq for historical data ──────────────────────────
        stooq_data = self._fetch_stooq_history(stooq_sym)

        if stooq_data:
            out["chart"] = {
                "symbol":   yahoo_sym,
                "currency": "SAR" if market == "saudi" else "USD",
                **{k: stooq_data[k] for k in ["dates","opens","highs","lows","closes","volumes","count"]},
            }
            last_price = stooq_data["last_price"]
            logger.info(f"Stooq OK: {stooq_sym} @ {last_price}")

            # Build basic quote from chart data
            if last_price and len(stooq_data["closes"]) >= 2:
                prev_close = stooq_data["closes"][-2]
                change     = last_price - prev_close
                change_pct = (change / prev_close * 100) if prev_close else 0
                out["quote"] = {
                    "symbol":      yahoo_sym,
                    "name":        symbol.upper(),
                    "exchange":    "TADAWUL" if market == "saudi" else "US",
                    "currency":    "SAR" if market == "saudi" else "USD",
                    "price":       round(last_price, 3),
                    "prev_close":  round(prev_close, 3),
                    "open":        stooq_data["opens"][-1],
                    "day_high":    stooq_data["highs"][-1],
                    "day_low":     stooq_data["lows"][-1],
                    "change":      round(change, 3),
                    "change_pct":  round(change_pct, 2),
                    "volume":      stooq_data["volumes"][-1],
                    "market_cap":  None,
                    "week52_high": max(stooq_data["highs"][-252:]) if len(stooq_data["highs"]) >= 2 else None,
                    "week52_low":  min(stooq_data["lows"][-252:])  if len(stooq_data["lows"])  >= 2 else None,
                    "pe_ratio":    None,
                    "forward_pe":  None,
                    "pb_ratio":    None,
                    "div_yield":   None,
                }
        else:
            out["errors"].append("stooq_unavailable")
            logger.warning(f"Stooq failed for {stooq_sym}, trying yfinance...")

        # ── 2. Try yfinance for richer data ───────────────────────────
        yf_data = self._fetch_yfinance(yahoo_sym)

        if yf_data:
            info = yf_data.get("info", {})
            hist = yf_data.get("hist")

            # Update quote with richer yfinance data
            yf_price = (info.get("regularMarketPrice") or
                        info.get("currentPrice") or
                        (hist["Close"].iloc[-1] if hist is not None and not hist.empty else None))

            if yf_price:
                out["quote"] = {
                    "symbol":      yahoo_sym,
                    "name":        info.get("longName") or info.get("shortName", symbol),
                    "exchange":    info.get("exchange", ""),
                    "currency":    info.get("currency", "SAR" if market == "saudi" else "USD"),
                    "price":       yf_price,
                    "prev_close":  info.get("regularMarketPreviousClose") or info.get("previousClose"),
                    "open":        info.get("regularMarketOpen")  or info.get("open"),
                    "day_high":    info.get("regularMarketDayHigh") or info.get("dayHigh"),
                    "day_low":     info.get("regularMarketDayLow")  or info.get("dayLow"),
                    "change":      info.get("regularMarketChange"),
                    "change_pct":  info.get("regularMarketChangePercent"),
                    "volume":      info.get("regularMarketVolume") or info.get("volume"),
                    "market_cap":  info.get("marketCap"),
                    "week52_high": info.get("fiftyTwoWeekHigh"),
                    "week52_low":  info.get("fiftyTwoWeekLow"),
                    "pe_ratio":    info.get("trailingPE"),
                    "forward_pe":  info.get("forwardPE"),
                    "pb_ratio":    info.get("priceToBook"),
                    "div_yield":   info.get("dividendYield"),
                }
                logger.info(f"yfinance quote OK: {yahoo_sym} @ {yf_price}")

            # Chart from yfinance if Stooq failed
            if not out["chart"] and hist is not None and not hist.empty:
                out["chart"] = {
                    "symbol":   yahoo_sym,
                    "currency": info.get("currency", "USD"),
                    "dates":    [d.strftime("%Y-%m-%d") for d in hist.index],
                    "opens":    list(hist["Open"].round(3)),
                    "highs":    list(hist["High"].round(3)),
                    "lows":     list(hist["Low"].round(3)),
                    "closes":   list(hist["Close"].round(3)),
                    "volumes":  [int(v) for v in hist["Volume"]],
                    "count":    len(hist),
                }
                logger.info(f"yfinance chart OK: {yahoo_sym}")

            # Fundamentals from yfinance
            if info and info.get("sector"):
                out["fundamentals"] = {
                    "sector":         info.get("sector", ""),
                    "industry":       info.get("industry", ""),
                    "description":    info.get("longBusinessSummary", "")[:600],
                    "country":        info.get("country", ""),
                    "employees":      info.get("fullTimeEmployees"),
                    "pe_ratio":       info.get("trailingPE"),
                    "forward_pe":     info.get("forwardPE"),
                    "pb_ratio":       info.get("priceToBook"),
                    "beta":           info.get("beta"),
                    "div_yield":      info.get("dividendYield"),
                    "payout_ratio":   info.get("payoutRatio"),
                    "roe":            info.get("returnOnEquity"),
                    "roa":            info.get("returnOnAssets"),
                    "gross_margin":   info.get("grossMargins"),
                    "op_margin":      info.get("operatingMargins"),
                    "net_margin":     info.get("profitMargins"),
                    "rev_growth":     info.get("revenueGrowth"),
                    "earn_growth":    info.get("earningsGrowth"),
                    "debt_to_equity": info.get("debtToEquity"),
                    "current_ratio":  info.get("currentRatio"),
                    "free_cash_flow": info.get("freeCashflow"),
                    "total_revenue":  info.get("totalRevenue"),
                    "eps_ttm":        info.get("trailingEps"),
                    "eps_fwd":        info.get("forwardEps"),
                    "book_value":     info.get("bookValue"),
                    "shares":         info.get("sharesOutstanding"),
                    "target_price":   info.get("targetMeanPrice"),
                    "analyst_rec":    info.get("recommendationKey", ""),
                }
                logger.info(f"yfinance fundamentals OK: {yahoo_sym}")
            else:
                out["errors"].append("fundamentals_unavailable")

            # News
            try:
                import yfinance as yf
                ticker   = yf.Ticker(yahoo_sym)
                news_raw = ticker.news or []
                out["news"] = [
                    {
                        "title":   n.get("title", ""),
                        "summary": n.get("summary", ""),
                        "link":    n.get("link", ""),
                        "date":    datetime.fromtimestamp(
                            n.get("providerPublishTime", 0)
                        ).strftime("%Y-%m-%d") if n.get("providerPublishTime") else "",
                    }
                    for n in news_raw[:8]
                ]
            except Exception:
                pass
        else:
            out["errors"].append("yfinance_unavailable")

        # ── Quality Gate ──────────────────────────────────────────────
        if not out["quote"] and not out["chart"]:
            raise ValueError(
                f"لم يتم العثور على بيانات للرمز '{symbol}'. "
                "تأكد من صحة الرمز والسوق."
            )

        if out["quote"] and out["chart"]:
            out["data_quality"] = "full"
        elif out["quote"] or out["chart"]:
            out["data_quality"] = "partial"

        logger.info(f"Done: {yahoo_sym} quality={out['data_quality']} errors={out['errors']}")
        return out
