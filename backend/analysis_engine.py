"""
Fundamental Analysis, News Sentiment & AI Recommendation Engine
Uses Claude AI (if available) or Smart Rule-Based fallback
"""
import requests
import json
import logging
import re
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


# ─── Fundamental Scoring ─────────────────────────────────────────────────────

def score_fundamentals(fins: Dict) -> Dict:
    if not fins:
        return {"overall_score": 50, "rating": "غير متاح", "details": {}}

    scores = {}

    def pct(v):
        return v * 100 if v and abs(v) < 10 else v

    pe = fins.get("pe_ratio")
    if pe:
        if 5 < pe < 15:    scores["pe"] = 90
        elif 15 <= pe < 20: scores["pe"] = 78
        elif 20 <= pe < 30: scores["pe"] = 62
        elif 30 <= pe < 50: scores["pe"] = 45
        else:               scores["pe"] = 25

    fpe = fins.get("forward_pe")
    if fpe:
        scores["forward_pe"] = 85 if fpe < 20 else 65 if fpe < 30 else 40

    pb = fins.get("pb_ratio")
    if pb:
        scores["pb"] = 88 if pb < 1.5 else 72 if pb < 3 else 55 if pb < 5 else 35

    roe = pct(fins.get("roe"))
    if roe:
        scores["roe"] = 92 if roe > 25 else 78 if roe > 15 else 60 if roe > 8 else 35

    roa = pct(fins.get("roa"))
    if roa:
        scores["roa"] = 88 if roa > 15 else 72 if roa > 8 else 55 if roa > 3 else 30

    margin = pct(fins.get("net_margin"))
    if margin:
        scores["net_margin"] = 90 if margin > 25 else 75 if margin > 15 else 58 if margin > 8 else 35

    rev_g = pct(fins.get("rev_growth"))
    if rev_g:
        scores["rev_growth"] = 92 if rev_g > 25 else 78 if rev_g > 10 else 60 if rev_g > 0 else 25

    earn_g = pct(fins.get("earn_growth") or fins.get("earnings_growth"))
    if earn_g:
        scores["earn_growth"] = 92 if earn_g > 30 else 78 if earn_g > 15 else 60 if earn_g > 0 else 20

    de = fins.get("debt_to_equity")
    if de:
        scores["debt_to_equity"] = 90 if de < 0.3 else 75 if de < 0.8 else 55 if de < 1.5 else 30

    cr = fins.get("current_ratio")
    if cr:
        scores["current_ratio"] = 88 if cr > 2 else 72 if cr > 1.5 else 55 if cr > 1 else 25

    div = pct(fins.get("div_yield") or fins.get("dividend_yield"))
    if div and div > 0:
        scores["div_yield"] = 85 if div > 4 else 72 if div > 2 else 60 if div > 0.5 else 45

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
        "score":     score,
        "sentiment": overall,
        "pos_count": pos_count,
        "neg_count": neg_count,
        "neu_count": neu_count,
        "analyzed":  analyzed,
    }


# ─── Smart Rule-Based Report (بدون API) ──────────────────────────────────────

def _smart_rule_based_report(
    symbol: str,
    price: float,
    currency: str,
    tech_score: int,
    fund_score: int,
    news_score: int,
    technical: Dict,
    fundamentals_score: Dict,
    news_sentiment: Dict,
    fins: Dict,
) -> Dict:
    """
    تقرير ذكي مفصّل يُولَّد من البيانات الفعلية بدون الحاجة لـ Claude API.
    يستخدم المؤشرات الفنية والأساسية والأخبار لبناء تقرير احترافي.
    """

    # ── دالة مساعدة للتحقق من الأرقام ───────────────────────────────────────
    def safe_num(v, default=0):
        try:
            f = float(v) if v is not None else default
            return default if (f != f or f == float("inf") or f == float("-inf")) else f
        except Exception:
            return default

    # ── استخراج البيانات الفنية ──────────────────────────────────────────────
    rsi_val   = safe_num(technical.get("rsi"), 50)
    macd_hist = safe_num(technical.get("macd_hist"), 0)
    sma20     = technical.get("sma20")
    sma50     = technical.get("sma50")
    sma200    = technical.get("sma200")
    dow       = technical.get("dow", {})
    elliott   = technical.get("elliott", {})
    candles   = technical.get("candlesticks", [])
    liq       = technical.get("liquidity", {})
    gann      = technical.get("gann", {})
    sr        = technical.get("support_resistance", {})

    trend     = dow.get("trend", "غير محدد")
    phase     = dow.get("phase", "")
    dow_sig   = dow.get("signal", "")
    ell_wave  = elliott.get("current_wave", "")
    ell_type  = elliott.get("wave_type", "")
    ell_tgt   = elliott.get("target")
    liq_sig   = liq.get("signal", "")
    obv       = liq.get("obv_trend", "")
    candle    = candles[0] if candles else {}
    supports    = sr.get("supports", [])
    resistances = sr.get("resistances", [])

    # ── حساب التوصية ─────────────────────────────────────────────────────────
    combined = tech_score * 0.45 + fund_score * 0.30 + news_score * 0.25

    # تعديل بناءً على RSI
    if rsi_val < 30:
        combined += 8   # تشبع بيعي = فرصة شراء
    elif rsi_val > 75:
        combined -= 8   # تشبع شرائي = تحذير

    # تعديل بناءً على MACD
    if macd_hist > 0:
        combined += 3
    elif macd_hist < 0:
        combined -= 3

    # تعديل بناءً على اتجاه داو
    if "صاعد" in trend:
        combined += 5
    elif "هابط" in trend:
        combined -= 5

    combined = max(10, min(95, combined))

    # تحديد التوصية
    if combined >= 80:
        action, confidence = "شراء قوي", min(90, round(combined))
    elif combined >= 68:
        action, confidence = "شراء", min(82, round(combined))
    elif combined >= 58:
        action, confidence = "احتفاظ", min(74, round(combined))
    elif combined >= 48:
        action, confidence = "مراقبة", min(65, round(combined))
    elif combined >= 38:
        action, confidence = "جني أرباح", min(68, round(100 - combined))
    else:
        action, confidence = "بيع", min(78, round(100 - combined))

    # ── حساب الأهداف ووقف الخسارة ────────────────────────────────────────────
    stop_loss = round(supports[0] * 0.985, 3) if supports else round(price * 0.93, 3)
    t1 = round(resistances[0] if resistances else price * 1.05, 3)
    t2 = round(resistances[1] if len(resistances) > 1 else price * 1.10, 3)
    t3 = round(resistances[2] if len(resistances) > 2 else price * 1.18, 3)

    try:
        if price and stop_loss and price > stop_loss and (t2 - price) > 0:
            rr_raw = (t2 - price) / (price - stop_loss)
            rr = round(rr_raw, 1) if rr_raw == rr_raw and rr_raw != float("inf") and rr_raw < 20 else 1.5
        else:
            rr = 1.5
    except Exception:
        rr = 1.5

    # تحديد مدة التوصية
    if tech_score >= 70 and rsi_val < 50:
        timeframe = "مضاربة قصيرة (أسبوع)"
    elif combined >= 65:
        timeframe = "سوينغ (2-4 أسابيع)"
    else:
        timeframe = "متوسط المدى (1-3 أشهر)"

    # ── بناء الملخص التنفيذي ─────────────────────────────────────────────────
    fund_rating = fundamentals_score.get("rating", "—")
    news_sent   = news_sentiment.get("sentiment", "محايد")

    # وضع السعر مقارنة بالمتوسطات
    price_vs_sma = []
    if sma20 and price > sma20:
        price_vs_sma.append("فوق المتوسط المتحرك 20")
    elif sma20 and price < sma20:
        price_vs_sma.append("تحت المتوسط المتحرك 20")
    if sma50 and price > sma50:
        price_vs_sma.append("فوق المتوسط المتحرك 50")
    elif sma50 and price < sma50:
        price_vs_sma.append("تحت المتوسط المتحرك 50")

    sma_text = " و".join(price_vs_sma) if price_vs_sma else "موقع السعر من المتوسطات غير محدد"

    rsi_text = (
        f"RSI عند {rsi_val:.0f} في منطقة تشبع بيعي — فرصة شراء محتملة" if rsi_val < 30 else
        f"RSI عند {rsi_val:.0f} في منطقة تشبع شرائي — توخَّ الحذر" if rsi_val > 70 else
        f"RSI عند {rsi_val:.0f} في المنطقة المحايدة — لا توجد إشارات متطرفة"
    )

    macd_text = (
        f"MACD إيجابي ({macd_hist:.3f}) — زخم صاعد" if macd_hist > 0 else
        f"MACD سلبي ({macd_hist:.3f}) — ضغط هابط"
    )

    executive_summary = (
        f"سهم {symbol} يُسجّل درجة تقنية {tech_score}/100 وأساسيات {fund_rating} بـ {fund_score}/100. "
        f"السعر {sma_text}. "
        f"الاتجاه العام {trend} في مرحلة {phase}. "
        f"المؤشرات المتكاملة تدعم توصية «{action}» بثقة {confidence}%."
    )

    # ── التحليل الفني التفصيلي ────────────────────────────────────────────────
    technical_narrative = (
        f"**الاتجاه العام ({trend}):** {phase}. "
        f"نظرية داو تُصدر إشارة «{dow_sig}».\n\n"
        f"**المؤشرات الرئيسية:** {rsi_text}. {macd_text}.\n\n"
        f"**موجات إليوت:** السهم في الموجة {ell_wave} ({ell_type})"
        f"{f' — الهدف المتوقع: {ell_tgt:.2f} {currency}' if ell_tgt else ''}.\n\n"
        f"**السيولة:** {liq_sig}. OBV في اتجاه {obv}.\n\n"
        f"**الشموع اليابانية:** {candle.get('name', '—')} — {candle.get('signal', '—')}.\n\n"
        f"**الدعم والمقاومة:** "
        f"دعم رئيسي عند {supports[0]:.2f}" if supports else "الدعم غير محدد"
    )
    if supports and resistances:
        technical_narrative += f" — مقاومة رئيسية عند {resistances[0]:.2f}."

    # ── التحليل الأساسي التفصيلي ─────────────────────────────────────────────
    strengths  = fundamentals_score.get("strengths", [])
    weaknesses = fundamentals_score.get("weaknesses", [])
    sector_avgs = fundamentals_score.get("sector_avgs", {})

    pe  = fins.get("pe_ratio")
    roe = fins.get("roe")
    div = fins.get("div_yield")

    fund_lines = [f"الأساسيات مُصنَّفة «{fund_rating}» بإجمالي {fund_score}/100."]
    if pe:
        avg_pe = sector_avgs.get("pe", 18)
        fund_lines.append(
            f"P/E={pe:.1f} {'أقل من' if pe < avg_pe else 'أعلى من'} "
            f"متوسط القطاع ({avg_pe}) — "
            f"{'تقييم جذاب' if pe < avg_pe else 'تقييم مرتفع نسبياً'}."
        )
    if roe:
        fund_lines.append(f"ROE={roe*100:.1f}% — {'كفاءة ممتازة' if roe > 0.15 else 'في المستوى المتوسط'}.")
    if div and div > 0:
        fund_lines.append(f"عائد التوزيعات {div*100:.1f}% — {'مغرٍ للمستثمرين' if div > 0.03 else 'معتدل'}.")

    fundamental_narrative = " ".join(fund_lines)

    # ── تحليل الأخبار ────────────────────────────────────────────────────────
    pos_c = news_sentiment.get("pos_count", 0)
    neg_c = news_sentiment.get("neg_count", 0)
    neu_c = news_sentiment.get("neu_count", 0)
    total_news = pos_c + neg_c + neu_c

    if total_news == 0:
        news_narrative = "لا تتوفر أخبار حديثة للتحليل."
    else:
        dominant = "الأخبار الإيجابية" if pos_c > neg_c else "الأخبار السلبية" if neg_c > pos_c else "الأخبار المحايدة"
        news_narrative = (
            f"من إجمالي {total_news} خبر: {pos_c} إيجابي، {neg_c} سلبي، {neu_c} محايد. "
            f"{dominant} هي الغالبة مما يعكس مشاعر {news_sent} تجاه السهم. "
            f"درجة المشاعر الإعلامية {news_sentiment.get('score', 50)}/100."
        )

    # ── المحفزات والمخاطر (مفصّلة بالأرقام الفعلية) ─────────────────────────
    catalysts = []
    risks = []

    # ── محفزات فنية ──────────────────────────────────────────────────────────
    if "صاعد" in trend:
        catalysts.append(f"اتجاه {trend} مؤكد بنظرية داو — مرحلة {phase} — إشارة: {dow_sig}")

    if rsi_val < 30:
        catalysts.append(f"RSI={rsi_val:.1f} في منطقة تشبع بيعي (أقل من 30) — فرصة دخول قوية")
    elif rsi_val < 45:
        catalysts.append(f"RSI={rsi_val:.1f} في منطقة منخفضة — مساحة جيدة للصعود")

    if macd_hist > 0:
        catalysts.append(f"MACD إيجابي ({macd_hist:.4f}) — زخم صاعد مؤكد")

    if sma20 and price > sma20:
        catalysts.append(f"السعر ({price:.2f}) فوق SMA20 ({sma20:.2f}) — اتجاه قصير المدى صاعد")

    if sma50 and price > sma50:
        catalysts.append(f"السعر ({price:.2f}) فوق SMA50 ({sma50:.2f}) — اتجاه متوسط المدى صاعد")

    if obv == "صاعد":
        catalysts.append(f"OBV صاعد — تدفق سيولة مؤسسية داخل السهم")

    liq_ratio = liq.get("vol_ratio", 0)
    if liq_ratio and liq_ratio > 1.5:
        catalysts.append(f"حجم تداول {liq_ratio:.1f}x أعلى من المتوسط — اهتمام مرتفع بالسهم")

    if candle.get("bullish"):
        catalysts.append(f"نموذج شمعة «{candle.get('name','')}» — إشارة {candle.get('signal','')} بقوة {candle.get('strength','')}")

    if ell_wave and "دافع" in (ell_type or ""):
        catalysts.append(f"موجة إليوت {ell_wave} ({ell_type})" + (f" — هدف {ell_tgt:.2f} {currency}" if ell_tgt else ""))

    if supports:
        catalysts.append(f"دعم قوي عند {supports[0]:.2f} — قاعدة صلبة للسعر")

    # محفزات أساسية
    if strengths:
        catalysts.extend(strengths[:2])

    # ── مخاطر فنية ───────────────────────────────────────────────────────────
    if rsi_val > 75:
        risks.append(f"RSI={rsi_val:.1f} في منطقة تشبع شرائي (أعلى من 70) — تصحيح محتمل")
    elif rsi_val > 65:
        risks.append(f"RSI={rsi_val:.1f} يقترب من منطقة التشبع الشرائي (70) — توخَّ الحذر")

    if macd_hist < 0:
        risks.append(f"MACD سلبي ({macd_hist:.4f}) — ضغط بيعي مستمر")

    if sma20 and price < sma20:
        risks.append(f"السعر ({price:.2f}) تحت SMA20 ({sma20:.2f}) — ضعف قصير المدى")

    if sma50 and price < sma50:
        risks.append(f"السعر ({price:.2f}) تحت SMA50 ({sma50:.2f}) — ضعف متوسط المدى")

    if "هابط" in trend:
        risks.append(f"الاتجاه العام {trend} — خطر الاستمرار في الهبوط")

    if resistances:
        risks.append(f"مقاومة قوية عند {resistances[0]:.2f} — عائق أمام الصعود")
    if len(resistances) > 1:
        risks.append(f"مقاومة ثانية عند {resistances[1]:.2f} — هدف صعب الاختراق")

    if candle.get("bullish") is False:
        risks.append(f"نموذج شمعة «{candle.get('name','')}» هبوطي — إشارة {candle.get('signal','')}")

    if liq_ratio and liq_ratio < 0.5:
        risks.append(f"حجم تداول ضعيف ({liq_ratio:.1f}x المتوسط) — سيولة منخفضة")

    # مخاطر أساسية
    if weaknesses:
        risks.extend(weaknesses[:2])

    # ── تأكد من وجود بنود كافية ──────────────────────────────────────────────
    if not catalysts:
        catalysts = [
            f"درجة فنية {tech_score}/100 — مستوى مقبول",
            f"درجة أساسية {fund_score}/100 — {fundamentals_score.get('rating','متوسط')}",
            "إمكانية تحسن المؤشرات على المدى القريب",
        ]
    if not risks:
        risks = [
            "مخاطر السوق العامة والتقلبات الطبيعية",
            f"عدم وجود إشارات فنية واضحة — درجة {tech_score}/100",
            "يُنصح بالانتظار لتأكيد الاتجاه",
        ]

    catalysts = catalysts[:5]
    risks = risks[:5]

    # ── مبرر التوصية ─────────────────────────────────────────────────────────
    reasoning = (
        f"بناءً على التحليل المتكامل: درجة فنية {tech_score}/100 "
        f"وأساسيات {fund_score}/100 وأخبار {news_sentiment.get('score',50)}/100. "
        f"الاتجاه {trend} {'يدعم' if 'صاعد' in trend else 'لا يدعم'} قرار الشراء. "
        f"نسبة المخاطرة/العائد {rr}:1."
    )

    return {
        "executive_summary":      executive_summary,
        "technical_narrative":    technical_narrative,
        "fundamental_narrative":  fundamental_narrative,
        "news_narrative":         news_narrative,
        "risks":                  risks,
        "catalysts":              catalysts,
        "recommendation": {
            "action":      action,
            "confidence":  confidence,
            "entry_price": round(float(price), 3),
            "stop_loss":   stop_loss,
            "target1":     t1,
            "target2":     t2,
            "target3":     t3,
            "risk_reward": f"1:{rr}",
            "timeframe":   timeframe,
            "reasoning":   reasoning,
        },
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
    liq      = technical.get("liquidity", {})
    sr       = technical.get("support_resistance", {})

    market_ar = "السوق السعودي (تاسي)" if market == "saudi" else "السوق الأمريكي"

    # ── محاولة Claude API ────────────────────────────────────────────────────
    if api_key:
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

            json_obj = None
            try:
                json_obj = json.loads(content.strip())
            except Exception:
                match = re.search(r'\{[\s\S]*\}', content)
                if match:
                    json_obj = json.loads(match.group())

            if json_obj:
                logger.info(f"Claude AI report generated for {symbol}")
                return json_obj

        except Exception as e:
            logger.warning(f"Claude API failed, using smart fallback: {e}")

    # ── التقرير الذكي التلقائي (بدون API) ───────────────────────────────────
    logger.info(f"Generating smart rule-based report for {symbol}")
    return _smart_rule_based_report(
        symbol=symbol,
        price=float(price) if price else 0,
        currency=currency,
        tech_score=tech_score,
        fund_score=fund_score,
        news_score=news_score,
        technical=technical,
        fundamentals_score=fundamentals_score,
        news_sentiment=news_sentiment,
        fins=fins,
    )
