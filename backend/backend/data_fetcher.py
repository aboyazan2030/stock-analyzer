"""
Stock Data Fetcher
Supports Saudi (Tadawul .SR) and US markets via Yahoo Finance.
Symbol validation: always verifies returned symbol matches requested symbol.
"""
import requests
import logging
import xml.etree.ElementTree as ET
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


class YahooFetcher:
    BASES = [
        "https://query1.finance.yahoo.com",
        "https://query2.finance.yahoo.com",
    ]
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://finance.yahoo.com/",
        "Origin": "https://finance.yahoo.com",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._crumb = None
        self._inited = False

    def _init_session(self):
        if self._inited:
            return
        try:
            r = self.session.get("https://finance.yahoo.com/quote/AAPL", timeout=10, allow_redirects=True)
            if r.status_code == 200:
                rc = self.session.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=8)
                if rc.status_code == 200 and rc.text.strip():
                    self._crumb = rc.text.strip()
        except Exception as e:
            logger.debug(f"Session init: {e}")
        finally:
            self._inited = True

    def _params(self, extra=None):
        p = {}
        if self._crumb:
            p["crumb"] = self._crumb
        if extra:
            p.update(extra)
        return p

    def fetch_quote(self, yahoo_sym):
        self._init_session()
        fields = "regularMarketPrice,regularMarketChange,regularMarketChangePercent,regularMarketVolume,regularMarketDayHigh,regularMarketDayLow,regularMarketOpen,regularMarketPreviousClose,fiftyTwoWeekHigh,fiftyTwoWeekLow,marketCap,trailingPE,forwardPE,priceToBook,dividendYield,shortName,longName,financialCurrency,exchange,sector"
        for base in self.BASES:
            try:
                r = self.session.get(f"{base}/v7/finance/quote", params=self._params({"symbols": yahoo_sym, "fields": fields}), timeout=12)
                if r.status_code != 200:
                    continue
                data = r.json()
                results = data.get("quoteResponse", {}).get("result", [])
                if not results:
                    continue
                q = results[0]
                returned = q.get("symbol", "").upper()
                if returned != yahoo_sym.upper():
                    logger.error(f"SYMBOL MISMATCH: asked={yahoo_sym} got={returned}")
                    return None
                return q
            except Exception as e:
                logger.warning(f"Quote error ({base}): {e}")
        return None

    def fetch_chart(self, yahoo_sym, range_val="6mo"):
        self._init_session()
        interval = "1wk" if range_val in ("2y", "5y") else "1d"
        for base in self.BASES:
            try:
                r = self.session.get(f"{base}/v8/finance/chart/{yahoo_sym}", params=self._params({"interval": interval, "range": range_val, "includePrePost": "false"}), timeout=15)
                if r.status_code != 200:
                    continue
                data = r.json()
                results = data.get("chart", {}).get("result", [])
                if not results:
                    continue
                meta = results[0].get("meta", {})
                returned = meta.get("symbol", "").upper()
                if returned != yahoo_sym.upper():
                    logger.error(f"CHART MISMATCH: asked={yahoo_sym} got={returned}")
                    return None
                return results[0]
            except Exception as e:
                logger.warning(f"Chart error ({base}): {e}")
        return None

    def fetch_fundamentals(self, yahoo_sym):
        self._init_session()
        modules = ",".join(["summaryDetail","financialData","defaultKeyStatistics","incomeStatementHistory","balanceSheetHistory","cashflowStatementHistory","assetProfile","earnings"])
        for base in self.BASES:
            try:
                r = self.session.get(f"{base}/v10/finance/quoteSummary/{yahoo_sym}", params=self._params({"modules": modules}), timeout=18)
                if r.status_code != 200:
                    continue
                data = r.json()
                results = data.get("quoteSummary", {}).get("result", [])
                if results:
                    return results[0]
            except Exception as e:
                logger.warning(f"Fundamentals error ({base}): {e}")
        return None

    def fetch_news(self, yahoo_sym, count=8):
        self._init_session()
        news = []
        try:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={yahoo_sym}&region=US&lang=en-US"
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                for item in root.findall(".//item")[:count]:
                    news.append({"title": item.findtext("title","").strip(), "summary": item.findtext("description","").strip(), "link": item.findtext("link","").strip(), "date": item.findtext("pubDate","").strip()})
        except Exception as e:
            logger.warning(f"News error: {e}")
        return news


def _safe(d, *keys):
    for k in keys:
        if isinstance(d, dict):
            v = d.get(k)
            if isinstance(v, dict):
                return v.get("raw")
            if v is not None:
                return v
    return None


def parse_quote(q):
    return {"symbol": q.get("symbol"), "name": q.get("longName") or q.get("shortName",""), "exchange": q.get("exchange",""), "currency": q.get("financialCurrency") or q.get("currency",""), "price": q.get("regularMarketPrice"), "prev_close": q.get("regularMarketPreviousClose"), "open": q.get("regularMarketOpen"), "day_high": q.get("regularMarketDayHigh"), "day_low": q.get("regularMarketDayLow"), "change": q.get("regularMarketChange"), "change_pct": q.get("regularMarketChangePercent"), "volume": q.get("regularMarketVolume"), "market_cap": q.get("marketCap"), "week52_high": q.get("fiftyTwoWeekHigh"), "week52_low": q.get("fiftyTwoWeekLow"), "pe_ratio": q.get("trailingPE"), "forward_pe": q.get("forwardPE"), "pb_ratio": q.get("priceToBook"), "div_yield": q.get("dividendYield")}


def parse_chart(c):
    meta = c.get("meta", {})
    ts = c.get("timestamp", [])
    ind = c.get("indicators", {}).get("quote", [{}])[0]
    rows = [(datetime.fromtimestamp(t).strftime("%Y-%m-%d"), o, h, l, cl, v) for t, o, h, l, cl, v in zip(ts, ind.get("open",[]), ind.get("high",[]), ind.get("low",[]), ind.get("close",[]), ind.get("volume",[])) if cl is not None and h is not None and l is not None]
    return {"symbol": meta.get("symbol"), "currency": meta.get("currency",""), "dates": [r[0] for r in rows], "opens": [r[1] for r in rows], "highs": [r[2] for r in rows], "lows": [r[3] for r in rows], "closes": [r[4] for r in rows], "volumes": [r[5] for r in rows], "count": len(rows)}


def parse_fundamentals(f):
    sd = f.get("summaryDetail", {})
    fd = f.get("financialData", {})
    ks = f.get("defaultKeyStatistics", {})
    ap = f.get("assetProfile", {})
    return {"sector": ap.get("sector",""), "industry": ap.get("industry",""), "description": ap.get("longBusinessSummary","")[:600], "country": ap.get("country",""), "employees": ap.get("fullTimeEmployees"), "pe_ratio": _safe(sd,"trailingPE"), "forward_pe": _safe(sd,"forwardPE"), "pb_ratio": _safe(sd,"priceToBook"), "beta": _safe(sd,"beta"), "div_yield": _safe(sd,"dividendYield"), "payout_ratio": _safe(sd,"payoutRatio"), "roe": _safe(fd,"returnOnEquity"), "roa": _safe(fd,"returnOnAssets"), "gross_margin": _safe(fd,"grossMargins"), "op_margin": _safe(fd,"operatingMargins"), "net_margin": _safe(fd,"profitMargins"), "rev_growth": _safe(fd,"revenueGrowth"), "earn_growth": _safe(fd,"earningsGrowth"), "debt_to_equity": _safe(fd,"debtToEquity"), "current_ratio": _safe(fd,"currentRatio"), "free_cash_flow": _safe(fd,"freeCashflow"), "total_revenue": _safe(fd,"totalRevenue"), "eps_ttm": _safe(ks,"trailingEps"), "eps_fwd": _safe(ks,"forwardEps"), "book_value": _safe(ks,"bookValue"), "target_price": _safe(fd,"targetMeanPrice"), "analyst_rec": fd.get("recommendationKey","")}


class StockDataService:
    def __init__(self):
        self.fetcher = YahooFetcher()

    def get_all(self, symbol, market):
        yahoo_sym = to_yahoo_symbol(symbol, market)
        out = {"requested_symbol": symbol.upper(), "yahoo_symbol": yahoo_sym, "market": market, "fetched_at": datetime.now().isoformat(), "quote": None, "chart": None, "fundamentals": None, "news": [], "errors": [], "data_quality": "none"}
        raw_quote = self.fetcher.fetch_quote(yahoo_sym)
        if raw_quote:
            out["quote"] = parse_quote(raw_quote)
        else:
            out["errors"].append("price_unavailable")
        raw_chart = self.fetcher.fetch_chart(yahoo_sym, "6mo")
        if raw_chart:
            out["chart"] = parse_chart(raw_chart)
        else:
            out["errors"].append("chart_unavailable")
        raw_fins = self.fetcher.fetch_fundamentals(yahoo_sym)
        if raw_fins:
            out["fundamentals"] = parse_fundamentals(raw_fins)
        else:
            out["errors"].append("fundamentals_unavailable")
        out["news"] = self.fetcher.fetch_news(yahoo_sym)
        if not out["quote"] and not out["chart"]:
            raise ValueError(f"لم يتم العثور على بيانات للرمز '{symbol}'.")
        if out["quote"] and out["chart"]:
            out["data_quality"] = "full"
        elif out["quote"] or out["chart"]:
            out["data_quality"] = "partial"
        return out
