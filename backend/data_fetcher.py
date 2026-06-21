"""
Stock Data Fetcher - uses yfinance library
Supports Saudi (Tadawul .SR) and US markets
"""
import logging
from datetime import datetime
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


class StockDataService:
    def get_all(self, symbol: str, market: str) -> Dict[str, Any]:
        import yfinance as yf

        yahoo_sym = to_yahoo_symbol(symbol, market)
        logger.info(f"Fetching: {symbol} -> {yahoo_sym}")

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

        try:
            ticker = yf.Ticker(yahoo_sym)

            # Quote
            info = ticker.info
            if info and info.get("regularMarketPrice"):
                # Verify symbol
                returned = info.get("symbol", "").upper()
                if returned and returned != yahoo_sym.upper():
                    logger.error(f"Symbol mismatch: asked={yahoo_sym} got={returned}")
                    raise ValueError(f"Symbol mismatch: {returned} != {yahoo_sym}")

                out["quote"] = {
                    "symbol": yahoo_sym,
                    "name": info.get("longName") or info.get("shortName", ""),
                    "exchange": info.get("exchange", ""),
                    "currency": info.get("currency", ""),
                    "price": info.get("regularMarketPrice") or info.get("currentPrice"),
                    "prev_close": info.get("regularMarketPreviousClose") or info.get("previousClose"),
                    "open": info.get("regularMarketOpen") or info.get("open"),
                    "day_high": info.get("regularMarketDayHigh") or info.get("dayHigh"),
                    "day_low": info.get("regularMarketDayLow") or info.get("dayLow"),
                    "change": info.get("regularMarketChange"),
                    "change_pct": info.get("regularMarketChangePercent"),
                    "volume": info.get("regularMarketVolume") or info.get("volume"),
                    "market_cap": info.get("marketCap"),
                    "week52_high": info.get("fiftyTwoWeekHigh"),
                    "week52_low": info.get("fiftyTwoWeekLow"),
                    "pe_ratio": info.get("trailingPE"),
                    "forward_pe": info.get("forwardPE"),
                    "pb_ratio": info.get("priceToBook"),
                    "div_yield": info.get("dividendYield"),
                }
                logger.info(f"Quote OK: {yahoo_sym} @ {out['quote']['price']}")
            else:
                out["errors"].append("price_unavailable")
                logger.warning(f"No price for {yahoo_sym}")

            # Chart
            try:
                hist = ticker.history(period="6mo")
                if not hist.empty:
                    out["chart"] = {
                        "symbol": yahoo_sym,
                        "currency": info.get("currency", ""),
                        "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
                        "opens": list(hist["Open"].round(3)),
                        "highs": list(hist["High"].round(3)),
                        "lows": list(hist["Low"].round(3)),
                        "closes": list(hist["Close"].round(3)),
                        "volumes": [int(v) for v in hist["Volume"]],
                        "count": len(hist),
                    }
                    logger.info(f"Chart OK: {yahoo_sym} ({len(hist)} bars)")
                else:
                    out["errors"].append("chart_unavailable")
            except Exception as e:
                out["errors"].append("chart_unavailable")
                logger.warning(f"Chart error: {e}")

            # Fundamentals
            try:
                fins = {}
                fins["sector"]          = info.get("sector", "")
                fins["industry"]        = info.get("industry", "")
                fins["description"]     = info.get("longBusinessSummary", "")[:600]
                fins["country"]         = info.get("country", "")
                fins["employees"]       = info.get("fullTimeEmployees")
                fins["pe_ratio"]        = info.get("trailingPE")
                fins["forward_pe"]      = info.get("forwardPE")
                fins["pb_ratio"]        = info.get("priceToBook")
                fins["beta"]            = info.get("beta")
                fins["div_yield"]       = info.get("dividendYield")
                fins["payout_ratio"]    = info.get("payoutRatio")
                fins["roe"]             = info.get("returnOnEquity")
                fins["roa"]             = info.get("returnOnAssets")
                fins["gross_margin"]    = info.get("grossMargins")
                fins["op_margin"]       = info.get("operatingMargins")
                fins["net_margin"]      = info.get("profitMargins")
                fins["rev_growth"]      = info.get("revenueGrowth")
                fins["earn_growth"]     = info.get("earningsGrowth")
                fins["debt_to_equity"]  = info.get("debtToEquity")
                fins["current_ratio"]   = info.get("currentRatio")
                fins["quick_ratio"]     = info.get("quickRatio")
                fins["free_cash_flow"]  = info.get("freeCashflow")
                fins["total_revenue"]   = info.get("totalRevenue")
                fins["total_debt"]      = info.get("totalDebt")
                fins["eps_ttm"]         = info.get("trailingEps")
                fins["eps_fwd"]         = info.get("forwardEps")
                fins["book_value"]      = info.get("bookValue")
                fins["shares"]          = info.get("sharesOutstanding")
                fins["target_price"]    = info.get("targetMeanPrice")
                fins["target_low"]      = info.get("targetLowPrice")
                fins["target_high"]     = info.get("targetHighPrice")
                fins["analyst_rec"]     = info.get("recommendationKey", "")
                fins["analyst_count"]   = info.get("numberOfAnalystOpinions")
                out["fundamentals"] = fins
                logger.info(f"Fundamentals OK: {yahoo_sym}")
            except Exception as e:
                out["errors"].append("fundamentals_unavailable")
                logger.warning(f"Fundamentals error: {e}")

            # News
            try:
                news_raw = ticker.news or []
                out["news"] = [
                    {
                        "title":   n.get("title", ""),
                        "summary": n.get("summary", ""),
                        "link":    n.get("link", ""),
                        "date":    datetime.fromtimestamp(n.get("providerPublishTime", 0)).strftime("%Y-%m-%d") if n.get("providerPublishTime") else "",
                    }
                    for n in news_raw[:8]
                ]
                logger.info(f"News OK: {len(out['news'])} items")
            except Exception as e:
                logger.warning(f"News error: {e}")

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error fetching {yahoo_sym}: {e}")
            out["errors"].append(str(e))

        # Quality check
        if not out["quote"] and not out["chart"]:
            raise ValueError(
                f"لم يتم العثور على بيانات للرمز '{symbol}'. "
                "تأكد من صحة الرمز والسوق."
            )

        if out["quote"] and out["chart"]:
            out["data_quality"] = "full"
        elif out["quote"] or out["chart"]:
            out["data_quality"] = "partial"

        logger.info(f"Done: {yahoo_sym} quality={out['data_quality']}")
        return out
