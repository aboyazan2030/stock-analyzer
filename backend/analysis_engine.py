"""
Fundamental Analysis, News Sentiment & AI Recommendation Engine
Uses Claude AI to generate professional Arabic analysis report
"""
import requests
import json
import logging
import re
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


# ─── Fundamental Scoring ─────────────────────────────────────────────────────

def score_fundamentals(fins: Dict) -> Dict:
    """Score each fundamental metric and calculate overall."""
    if not fins:
        return {"overall_score": 50, "rating": "غير متاح", "details": {}}

    scores = {}

    def pct(v):
        return v * 100 if v and abs(v) < 10 else v

    # PE Ratio (lower = better, but not too low)
    pe = fins.get("pe_ratio")
    if pe:
        if 5 < pe < 15:    scores["pe"] = 90
        elif 15 <= pe < 20: scores["pe"] = 78
        elif 20 <= pe < 30: scores["pe"] = 62
        elif 30 <= pe < 50: scores["pe"] = 45
        else:               scores["pe"] = 25

    # Forward PE
    fpe = fins.get("forward_pe")
    if fpe:
        scores["forward_pe"] = 85 if fpe < 20 else 65 if fpe < 30 else 40

    # P/B Ratio
    pb = fins.get("pb_ratio")
    if pb:
        scores["pb"] = 88 if pb < 1.5 else 72 if pb < 3 else 55 if pb < 5 else 35

    # ROE
    roe = pct(fins.get("roe"))
    if roe:
        scores["roe"] = 92 if roe > 25 else 78 if roe > 15 else 60 if roe > 8 else 35

    # ROA
    roa = pct(fins.get("roa"))
    if roa:
        scores["roa"] = 88 if roa > 15 else 72 if roa > 8 else 55 if roa > 3 else 30

    # Net Margin
    margin = pct(fins.get("net_margin"))
    if margin:
        scores["net_margin"] = 90 if margin > 25 else 75 if margin > 15 else 58 if margin > 8 else 35

    # Revenue Growth
    rev_g = pct(fins.get("rev_growth"))
    if rev_g:
        scores["rev_growth"] = 92 if rev_g > 25 else 78 if rev_g > 10 else 60 if rev_g > 0 else 25

    # Earnings Growth
    earn_g = pct(fins.get("earn_growth") or fins.get("earnings_growth"))
    if earn_g:
        scores["earn_growth"] = 92 if earn_g > 30 else 78 if earn_g > 15 else 60 if earn_g > 0 else 20

    # Debt to Equity
    de = fins.get("debt_to_equity")
    if de:
        scores["debt_to_equity"] = 90 if de < 0.3 else 75 if de < 0.8 else 55 if de < 1.5 else 30

    # Current Ratio
    cr = fins.get("current_ratio")
    if cr:
        scores["current_ratio"] = 88 if cr > 2 else 72 if cr > 1.5 else 55 if cr > 1 else 25

    # Dividend Yield
    div = pct(fins.get("div_yield") or fins.get("dividend_yield"))
    if div and div > 0:
        scores["div_yield"] = 85 if div > 4 else 72 if div > 2 else 60 if div > 0.5 else 45

    # Operating Margin
    op_m = pct(fins.get("op_margin") or fins.get("operating_margin"))
    if op_m:
        scores["op_margin"] = 88 if op_m > 20 else 72 if op_m > 10 else 52 if op_m > 0 else 20

    if not scores:
        return {"overall_score": 50, "rating": "بيانات غير كافية", "details": scores}

    overall = round(sum(scores.values()) / len(scores))
    rating = (
        "ممتازة" if overall >= 80 else
        "جيدة"   if overall >= 65 else
        "متوسطة" if overall >= 50 else
        "ضعيفة"
    )

    # Sector comparison (approximate benchmarks)
    sector = fins.get("sector", "")
    sector_avgs = _get_sector_benchmarks(sector)

    return {
        "overall_score": overall,
        "rating":        rating,
        "details":       scores,
        "sector_avgs":   sector_avgs,
        "strengths":     _find_strengths(fins, scores),
        "weaknesses":    _find_weaknesses(fins, scores),
    }


def _get_sector_benchmarks(sector: str) -> Dict:
    benchmarks = {
        "Energy":          {"pe": 12, "roe": 18, "margin": 15},
        "Financials":      {"pe": 14, "roe": 12, "margin": 25},
        "Technology":      {"pe": 28, "roe": 22, "margin": 22},
        "Healthcare":      {"pe": 22, "roe": 15, "margin": 18},
        "Consumer":        {"pe": 20, "roe": 18, "margin": 12},
        "Materials":       {"pe": 15, "roe": 14, "margin": 14},
        "الطاقة":          {"pe": 12, "roe": 18, "margin": 15},
        "البنوك":          {"pe": 13, "roe": 12, "margin": 30},
        "البتروكيماويات":  {"pe": 15, "roe": 14, "margin": 14},
        "الاتصالات":       {"pe": 18, "roe": 16, "margin": 18},
        "التأمين":         {"pe": 18, "roe": 13, "margin": 10},
        "الأغذية":         {"pe": 22, "roe": 16, "margin": 10},
    }
    for key, vals in benchmarks.items():
        if key.lower() in sector.lower() or sector.lower() in key.lower():
            return vals
    return {"pe": 18, "roe": 15, "margin": 15}


def _find_strengths(fins: Dict, scores: Dict) -> List[str]:
    strengths = []
    if scores.get("roe", 0) >= 78:
        strengths.append(f"ROE مرتفع {fins.get('roe', 0)*100:.1f}% — كفاءة عالية في توظيف حقوق المساهمين")
    if scores.get("net_margin", 0) >= 75:
        strengths.append(f"هامش ربح ممتاز {fins.get('net_margin', 0)*100:.1f}% — ربحية قوية")
    if scores.get("rev_growth", 0) >= 78:
        strengths.append(f"نمو إيرادات قوي {fins.get('rev_growth', 0)*100:.1f}% — توسع مستمر")
    if scores.get("debt_to_equity", 0) >= 75:
        strengths.append(f"ميزانية صحية — نسبة دين منخفضة {fins.get('debt_to_equity', 0):.2f}")
    if scores.get("div_yield", 0) >= 72:
        strengths.append(f"عائد توزيعات مغرٍ {fins.get('div_yield', 0)*100:.1f}%")
    if scores.get("pe", 0) >= 78:
        strengths.append(f"تقييم جذاب — P/E={fins.get('pe_ratio', 0):.1f}")
    return strengths or ["مؤشرات مالية في المستوى المتوسط"]


def _find_weaknesses(fins: Dict, scores: Dict) -> List[str]:
    weaknesses = []
    if scores.get("pe", 100) <= 45:
        weaknesses.append(f"تقييم مرتفع — P/E={fins.get('pe_ratio', 0):.1f}")
    if scores.get("debt_to_equity", 100) <= 45:
        weaknesses.append(f"نسبة دين مرتفعة {fins.get('debt_to_equity', 0):.2f}")
    if scores.get("net_margin", 100) <= 45:
        weaknesses.append(f"هامش ربح ضيق {fins.get('net_margin', 0)*100:.1f}%")
    if scores.get("rev_growth", 100) <= 30:
        weaknesses.append(f"نمو إيرادات ضعيف أو سلبي {fins.get('rev_growth', 0)*100:.1f}%")
    if scores.get("current_ratio", 100) <= 30:
        weaknesses.append(f"سيولة منخفضة — نسبة تداول {fins.get('current_ratio', 0):.2f}")
    return weaknesses or ["لا توجد نقاط ضعف جوهرية واضحة"]


# ─── News Sentiment ───────────────────────────────────────────────────────────

POSITIVE_KEYWORDS = [
    "profit", "growth", "record", "increase", "beat", "strong", "buy",
    "upgrade", "outperform", "dividend", "expansion", "partnership",
    "ربح", "نمو", "ارتفاع", "قوي", "شراء", "توزيعات", "توسع",
    "تجاوز", "تطور", "نجاح", "زيادة", "رفع", "إيجابي"
]
NEGATIVE_KEYWORDS = [
    "loss", "decline", "miss", "weak", "downgrade", "sell", "lawsuit",
    "bankruptcy", "cut", "warning", "investigation", "fraud",
    "خسارة", "انخفاض", "ضعف", "بيع", "تراجع", "قضية", "غرامة",
    "تخفيض", "تحقيق", "مخاوف", "سلبي", "هبوط"
]


def analyze_news_sentiment(news_items: List[Dict]) -> Dict:
    if not news_items:
        return {"score": 50, "sentiment": "محايد", "analyzed": []}

    analyzed = []
    pos_count = neg_count = neu_count = 0

    for item in news_items:
        text = (item.get("title", "") + " " + item.get("summary", "")).lower()
        pos_hits = sum(1 for kw in POSITIVE_KEYWORDS if kw.lower() in text)
        neg_hits = sum(1 for kw in NEGATIVE_KEYWORDS if kw.lower() in text)

        if pos_hits > neg_hits + 1:
            sentiment = "إيجابي"
            impact = "عالي" if pos_hits > 3 else "متوسط"
            pos_count += 1
        elif neg_hits > pos_hits + 1:
            sentiment = "سلبي"
            impact = "عالي" if neg_hits > 3 else "متوسط"
            neg_count += 1
        else:
            sentiment = "محايد"
            impact = "منخفض"
            neu_count += 1

        analyzed.append({
            "title":     item.get("title", ""),
            "date":      item.get("date", ""),
            "sentiment": sentiment,
            "impact":    impact,
            "link":      item.get("link", ""),
        })

    total = len(news_items)
    pos_pct = pos_count / total
    neg_pct = neg_count / total

    score = round(50 + (pos_pct - neg_pct) * 50)
    score = max(10, min(95, score))

    overall = (
        "إيجابي" if score >= 65 else
        "سلبي"   if score <= 40 else
        "محايد"
    )
    return {
        "score":    score,
        "sentiment": overall,
        "pos_count": pos_count,
        "neg_count": neg_count,
        "neu_count": neu_count,
        "analyzed":  analyzed,
    }


# ─── Claude AI Report Generator ───────────────────────────────────────────────

def generate_ai_report(
    symbol: str,
    market: str,
    quote: Dict,
    fundamentals_score: Dict,
    technical: Dict,
    news_sentiment: Dict,
    fins: Dict,
    api_key: str,
) -> Dict:
    """
    Call Claude API to generate professional Arabic analysis report
    and final recommendation.
    """
    price    = quote.get("price", 0) if quote else 0
    name     = quote.get("name", symbol) if quote else symbol
    currency = quote.get("currency", "") if quote else ""

    tech_score  = technical.get("tech_score", 50)
    fund_score  = fundamentals_score.get("overall_score", 50)
    fund_rating = fundamentals_score.get("rating", "غير معروف")
    news_score  = news_sentiment.get("score", 50)
    news_sent   = news_sentiment.get("sentiment", "محايد")

    rsi_val  = technical.get("rsi", 50)
    dow      = technical.get("dow", {})
    elliott  = technical.get("elliott", {})
    candles  = technical.get("candlesticks", [])
    gann     = technical.get("gann", {})
    liq      = technical.get("liquidity", {})
    sr       = technical.get("support_resistance", {})

    market_ar = "السوق السعودي (تاسي)" if market == "saudi" else "السوق الأمريكي"

    prompt = f"""أنت محلل مالي خبير. حلّل هذا السهم وأصدر توصية احترافية نهائية.

السهم: {name} ({symbol}) — {market_ar}
السعر الحالي: {price} {currency}

=== التحليل الفني (درجة: {tech_score}/100) ===
• RSI: {rsi_val} {'— تشبع بيعي (فرصة شراء)' if rsi_val and rsi_val < 30 else '— تشبع شرائي (تحذير)' if rsi_val and rsi_val > 70 else ''}
• MACD: {'إيجابي صاعد' if technical.get('macd_hist', 0) and technical.get('macd_hist') > 0 else 'سلبي هابط'}
• داو: {dow.get('trend','—')} — {dow.get('phase','—')} — إشارة: {dow.get('signal','—')}
• إليوت: الموجة {elliott.get('current_wave','—')} ({elliott.get('wave_type','—')}) — الهدف: {elliott.get('target','—')}
• شموع: {candles[0]['name'] if candles else '—'} ({candles[0]['signal'] if candles else '—'})
• السيولة: {liq.get('signal','—')} — {liq.get('ad_trend','—')}
• جان: {gann.get('angle_pos','—')}
• دعم 1: {sr.get('supports',[None])[0] if sr.get('supports') else '—'}
• مقاومة 1: {sr.get('resistances',[None])[0] if sr.get('resistances') else '—'}

=== التحليل الأساسي (درجة: {fund_score}/100 — {fund_rating}) ===
• P/E: {fins.get('pe_ratio','—')} | Forward P/E: {fins.get('forward_pe','—')}
• P/B: {fins.get('pb_ratio','—')} | ROE: {round(fins.get('roe',0)*100,1) if fins.get('roe') else '—'}%
• هامش الربح: {round(fins.get('net_margin',0)*100,1) if fins.get('net_margin') else '—'}%
• نمو الإيرادات: {round(fins.get('rev_growth',0)*100,1) if fins.get('rev_growth') else '—'}%
• الدين/حقوق: {fins.get('debt_to_equity','—')}
• نقاط القوة: {'; '.join(fundamentals_score.get('strengths',[])[:2])}
• نقاط الضعف: {'; '.join(fundamentals_score.get('weaknesses',[])[:2])}

=== الأخبار (درجة: {news_score}/100 — {news_sent}) ===
إيجابية: {news_sentiment.get('pos_count',0)} | سلبية: {news_sentiment.get('neg_count',0)} | محايدة: {news_sentiment.get('neu_count',0)}

أجب بـ JSON فقط (بدون أي نص خارج {{}}):

{{
  "executive_summary": "ملخص تنفيذي احترافي 3-4 جمل يشرح وضع السهم الحالي",
  "technical_narrative": "شرح مفصل للوضع الفني وأهم الإشارات",
  "fundamental_narrative": "تقييم أساسيات الشركة ومقارنتها بالقطاع",
  "news_narrative": "تأثير الأخبار على السهم قصيراً ومتوسطاً",
  "risks": ["خطر 1", "خطر 2", "خطر 3"],
  "catalysts": ["محفز 1", "محفز 2", "محفز 3"],
  "recommendation": {{
    "action": "شراء قوي أو شراء أو احتفاظ أو مراقبة أو جني أرباح أو بيع",
    "confidence": 78,
    "entry_price": {price},
    "stop_loss": 0.00,
    "target1": 0.00,
    "target2": 0.00,
    "target3": 0.00,
    "risk_reward": "1:2.5",
    "timeframe": "سوينغ (2-4 أسابيع) أو مضاربة أو استثمار",
    "reasoning": "مبرر التوصية في جملتين"
  }}
}}"""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model":      "claude-sonnet-4-6",
                "max_tokens": 2000,
                "system":     "أنت محلل مالي خبير. أجب بـ JSON صحيح فقط بدون أي نص خارج {}.",
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["content"][0]["text"]

        # Extract JSON
        json_obj = None
        try:
            json_obj = json.loads(content.strip())
        except Exception:
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                json_obj = json.loads(match.group())

        if json_obj:
            logger.info(f"AI report generated for {symbol}")
            return json_obj

    except Exception as e:
        logger.error(f"AI report error: {e}")

    # Fallback: rule-based recommendation
    return _rule_based_recommendation(
        symbol, price, currency, tech_score, fund_score, news_score,
        dow, sr, rsi_val, technical.get("macd_hist")
    )


def _rule_based_recommendation(
    symbol, price, currency, tech_score, fund_score, news_score,
    dow, sr, rsi_val, macd_hist
) -> Dict:
    """Fallback rule-based recommendation when AI unavailable."""
    combined = tech_score * 0.45 + fund_score * 0.30 + news_score * 0.25

    if combined >= 78 and (rsi_val or 50) < 45:
        action = "شراء قوي"
        confidence = min(88, round(combined))
    elif combined >= 70:
        action = "شراء"
        confidence = min(80, round(combined))
    elif combined >= 60:
        action = "احتفاظ"
        confidence = min(72, round(combined))
    elif combined >= 50:
        action = "مراقبة"
        confidence = min(62, round(combined))
    elif combined >= 40:
        action = "جني أرباح"
        confidence = min(65, round(100 - combined))
    else:
        action = "بيع"
        confidence = min(75, round(100 - combined))

    supports    = sr.get("supports",    [price * 0.95])
    resistances = sr.get("resistances", [price * 1.05])
    stop_loss = round(supports[0] * 0.98, 3) if supports else round(price * 0.93, 3)
    t1 = round(resistances[0] if resistances else price * 1.06, 3)
    t2 = round(resistances[1] if len(resistances) > 1 else price * 1.12, 3)
    t3 = round(resistances[2] if len(resistances) > 2 else price * 1.20, 3)
    rr = round((t2 - price) / (price - stop_loss), 1) if price > stop_loss else 1.5

    trend = dow.get("trend", "غير محدد")
    phase = dow.get("phase", "")

    return {
        "executive_summary": (
            f"التحليل الشامل لسهم {symbol} يُشير إلى درجة فنية {tech_score}/100 "
            f"وأساسيات بدرجة {fund_score}/100. "
            f"الاتجاه العام {trend} في مرحلة {phase}. "
            f"المؤشرات تدعم توصية {action}."
        ),
        "technical_narrative": (
            f"الاتجاه {trend}. RSI={rsi_val} "
            f"({'تشبع بيعي' if rsi_val and rsi_val < 30 else 'تشبع شرائي' if rsi_val and rsi_val > 70 else 'محايد'}). "
            f"MACD {'إيجابي' if macd_hist and macd_hist > 0 else 'سلبي'}."
        ),
        "fundamental_narrative": f"الأساسيات بدرجة {fund_score}/100.",
        "news_narrative": f"المشاعر الإعلامية درجة {news_score}/100.",
        "risks":      ["مخاطر السوق العامة", "تقلبات الأسعار", "المخاطر القطاعية"],
        "catalysts":  ["تحسن المؤشرات الفنية", "قوة الأساسيات", "إشارات السيولة"],
        "recommendation": {
            "action":      action,
            "confidence":  confidence,
            "entry_price": round(price, 3),
            "stop_loss":   stop_loss,
            "target1":     t1,
            "target2":     t2,
            "target3":     t3,
            "risk_reward": f"1:{rr}",
            "timeframe":   "سوينغ (2-4 أسابيع)",
            "reasoning":   f"بناءً على التحليل المتكامل: درجة فنية {tech_score}/100 وأساسيات {fund_score}/100.",
        },
    }
