"""
Technical Analysis Engine - 6 Theories
Dow Theory, Elliott Wave, Support/Resistance, Liquidity, Candlesticks, Gann
"""
import math
import statistics
import logging
from typing import List, Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)


def sma(values, n):
    result = []
    for i in range(len(values)):
        if i < n - 1:
            result.append(None)
        else:
            result.append(sum(values[i-n+1:i+1]) / n)
    return result


def ema(values, n):
    if len(values) < n:
        return [None] * len(values)
    result = [None] * (n - 1)
    seed = sum(values[:n]) / n
    result.append(seed)
    k = 2 / (n + 1)
    prev = seed
    for v in values[n:]:
        e = v * k + prev * (1 - k)
        result.append(e)
        prev = e
    return result


def rsi(closes, period=14):
    if len(closes) < period + 1:
        return [None] * len(closes)
    result = [None] * period
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    rs = avg_gain / avg_loss if avg_loss else float("inf")
    result.append(100 - 100 / (1 + rs))
    for i in range(period + 1, len(closes)):
        diff = closes[i] - closes[i-1]
        g = max(diff, 0)
        l = max(-diff, 0)
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
        rs = avg_gain / avg_loss if avg_loss else float("inf")
        result.append(100 - 100 / (1 + rs))
    return result


def macd(closes, fast=12, slow=26, signal=9):
    e12 = ema(closes, fast)
    e26 = ema(closes, slow)
    macd_line = [(a - b) if a is not None and b is not None else None for a, b in zip(e12, e26)]
    valid_macd = [v for v in macd_line if v is not None]
    if len(valid_macd) < signal:
        sig_line = [None] * len(macd_line)
    else:
        sig_vals = ema(valid_macd, signal)
        offset = len(macd_line) - len(valid_macd)
        sig_line = [None] * offset + sig_vals
    histogram = [(m - s) if m is not None and s is not None else None for m, s in zip(macd_line, sig_line)]
    return {"macd": macd_line, "signal": sig_line, "histogram": histogram}


def bollinger(closes, n=20, k=2.0):
    upper, lower, mid = [], [], []
    for i in range(len(closes)):
        if i < n - 1:
            upper.append(None); lower.append(None); mid.append(None)
        else:
            window = closes[i-n+1:i+1]
            m = sum(window) / n
            std = statistics.stdev(window) if len(window) > 1 else 0
            mid.append(m)
            upper.append(m + k * std)
            lower.append(m - k * std)
    return {"upper": upper, "mid": mid, "lower": lower}


def stochastic(highs, lows, closes, k_period=14, d_period=3):
    k_vals = []
    for i in range(len(closes)):
        if i < k_period - 1:
            k_vals.append(None)
        else:
            hi = max(highs[i-k_period+1:i+1])
            lo = min(lows[i-k_period+1:i+1])
            k_vals.append(((closes[i] - lo) / (hi - lo) * 100) if hi != lo else 50)
    valid_k = [v for v in k_vals if v is not None]
    d_raw = sma(valid_k, d_period)
    offset = len(k_vals) - len(valid_k)
    d_vals = [None] * offset + d_raw
    return {"k": k_vals, "d": d_vals}


def atr(highs, lows, closes, period=14):
    tr = []
    for i in range(len(closes)):
        if i == 0:
            tr.append(highs[i] - lows[i])
        else:
            tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
    return sma(tr, period)


def find_pivots(highs, lows, window=5):
    peaks, troughs = [], []
    for i in range(window, len(highs) - window):
        if all(highs[i] >= highs[i-j] and highs[i] >= highs[i+j] for j in range(1, window+1)):
            peaks.append((i, highs[i]))
        if all(lows[i] <= lows[i-j] and lows[i] <= lows[i+j] for j in range(1, window+1)):
            troughs.append((i, lows[i]))
    return {"peaks": peaks, "troughs": troughs}


def calc_support_resistance(closes, highs, lows, current_price):
    pivots = find_pivots(highs, lows, window=5)
    all_levels = [p[1] for p in pivots["peaks"]] + [t[1] for t in pivots["troughs"]]
    clustered = []
    all_levels.sort()
    for level in all_levels:
        placed = False
        for cluster in clustered:
            if abs(level - cluster["center"]) / cluster["center"] < 0.015:
                cluster["levels"].append(level)
                cluster["center"] = sum(cluster["levels"]) / len(cluster["levels"])
                cluster["strength"] += 1
                placed = True
                break
        if not placed:
            clustered.append({"center": level, "levels": [level], "strength": 1})
    clustered.sort(key=lambda x: x["strength"], reverse=True)
    supports = sorted([c["center"] for c in clustered if c["center"] < current_price], reverse=True)[:3]
    resistances = sorted([c["center"] for c in clustered if c["center"] > current_price])[:3]
    recent_high = max(highs[-60:]) if len(highs) >= 60 else max(highs)
    recent_low = min(lows[-60:]) if len(lows) >= 60 else min(lows)
    swing = recent_high - recent_low
    fibs = {"0.236": round(recent_high - swing * 0.236, 3), "0.382": round(recent_high - swing * 0.382, 3), "0.500": round(recent_high - swing * 0.500, 3), "0.618": round(recent_high - swing * 0.618, 3), "0.786": round(recent_high - swing * 0.786, 3)}
    return {"supports": [round(s, 3) for s in supports], "resistances": [round(r, 3) for r in resistances], "fibonacci": fibs, "pivots": pivots, "recent_high": round(recent_high, 3), "recent_low": round(recent_low, 3)}


def dow_theory(closes, highs, lows, volumes):
    if len(closes) < 20:
        return {"error": "insufficient_data"}
    sma20 = sma(closes, 20)
    sma50 = sma(closes, min(50, len(closes)))
    current = closes[-1]
    s20 = next((v for v in reversed(sma20) if v is not None), None)
    s50 = next((v for v in reversed(sma50) if v is not None), None)
    if s20 and s50:
        if current > s20 > s50:
            trend = "صاعد"
        elif current < s20 < s50:
            trend = "هابط"
        else:
            trend = "جانبي"
    else:
        trend = "غير محدد"
    recent_closes = closes[-20:]
    peaks = [i for i in range(1, len(recent_closes)-1) if recent_closes[i] > recent_closes[i-1] and recent_closes[i] > recent_closes[i+1]]
    troughs = [i for i in range(1, len(recent_closes)-1) if recent_closes[i] < recent_closes[i-1] and recent_closes[i] < recent_closes[i+1]]
    hh = hl = lh = ll = False
    if len(peaks) >= 2:
        hh = recent_closes[peaks[-1]] > recent_closes[peaks[-2]]
        lh = recent_closes[peaks[-1]] < recent_closes[peaks[-2]]
    if len(troughs) >= 2:
        hl = recent_closes[troughs[-1]] > recent_closes[troughs[-2]]
        ll = recent_closes[troughs[-1]] < recent_closes[troughs[-2]]
    avg_vol = sum(volumes[-20:]) / 20 if volumes else 0
    last_vol = volumes[-1] if volumes else 0
    vol_confirms = last_vol > avg_vol * 1.2
    if trend == "صاعد" and hh and hl:
        phase, signal, score = "صعود مؤكد", "شراء", 82
    elif trend == "صاعد" and (hh or hl):
        phase, signal, score = "صعود انتقالي", "شراء مضاربي", 68
    elif trend == "هابط" and lh and ll:
        phase, signal, score = "هبوط مؤكد", "بيع", 25
    elif trend == "هابط" and (lh or ll):
        phase, signal, score = "هبوط انتقالي", "جني أرباح", 38
    else:
        phase, signal, score = "تجميع / جانبي", "انتظار", 52
    if vol_confirms and signal == "شراء":
        score = min(score + 8, 95)
    return {"trend": trend, "phase": phase, "signal": signal, "score": score, "hh": hh, "hl": hl, "lh": lh, "ll": ll, "vol_confirms": vol_confirms, "sma20": round(s20, 3) if s20 else None, "sma50": round(s50, 3) if s50 else None, "analysis": f"الاتجاه {trend} — {phase}. {'قمم وقيعان صاعدة.' if hh and hl else ''} {'قمم وقيعان هابطة.' if lh and ll else ''} الحجم {'يؤكد' if vol_confirms else 'لا يؤكد'} الاتجاه. إشارة: {signal}."}


def elliott_wave(closes, highs, lows):
    if len(closes) < 30:
        return {"error": "insufficient_data"}
    rsi_vals = rsi(closes, 14)
    current_rsi = next((v for v in reversed(rsi_vals) if v is not None), 50)
    current_price = closes[-1]
    recent_high = max(highs[-60:]) if len(highs) >= 60 else max(highs)
    recent_low = min(lows[-60:]) if len(lows) >= 60 else min(lows)
    position_pct = (current_price - recent_low) / (recent_high - recent_low) * 100 if recent_high != recent_low else 50
    if position_pct < 20:
        wave, w_type, next_wave, score, target_mult = "2 أو B (تصحيحية)", "تصحيحية", "3 أو C (دافعة)", 72, 1.20
    elif position_pct < 40:
        wave, w_type, next_wave, score, target_mult = "1 أو A (دافعة)", "دافعة", "2 أو B (تصحيحية)", 60, 1.08
    elif position_pct < 60 and current_rsi < 65:
        wave, w_type, next_wave, score, target_mult = "3 (دافعة — الأقوى)", "دافعة", "4 (تصحيحية)", 85, 1.15
    elif position_pct < 75 and current_rsi > 60:
        wave, w_type, next_wave, score, target_mult = "5 (دافعة — اكتمال)", "دافعة", "A (تصحيحية)", 55, 1.05
    else:
        wave, w_type, next_wave, score, target_mult = "A أو C (تصحيحية)", "تصحيحية", "موجة دافعة جديدة", 40, 0.92
    target = round(current_price * target_mult, 3)
    return {"current_wave": wave, "wave_type": w_type, "next_wave": next_wave, "position_pct": round(position_pct, 1), "target": target, "rsi": round(current_rsi, 1), "score": score, "analysis": f"السهم في الموجة {wave} ({w_type}). موقعه {position_pct:.0f}% من النطاق. الموجة القادمة: {next_wave}. الهدف: {target}."}


def detect_candlestick_patterns(opens, highs, lows, closes):
    patterns = []
    n = len(closes)
    if n < 3:
        return patterns

    def body(i): return abs(closes[i] - opens[i])
    def range_(i): return highs[i] - lows[i]
    def upper_shadow(i): return highs[i] - max(opens[i], closes[i])
    def lower_shadow(i): return min(opens[i], closes[i]) - lows[i]
    def is_bull(i): return closes[i] > opens[i]
    def is_bear(i): return closes[i] < opens[i]

    i = n - 1
    r = range_(i); b = body(i); us = upper_shadow(i); ls = lower_shadow(i)
    if r > 0 and b / r < 0.1:
        patterns.append({"name": "دوجي", "type": "محايد", "signal": "انعكاس محتمل", "strength": "متوسط", "bullish": None})
    if is_bull(i) and ls > 2 * b and us < 0.1 * r and b > 0:
        patterns.append({"name": "مطرقة ↑", "type": "انعكاس صعودي", "signal": "شراء", "strength": "قوي", "bullish": True})
    if is_bear(i) and us > 2 * b and ls < 0.1 * r and b > 0:
        patterns.append({"name": "نجمة ساقطة ↓", "type": "انعكاس هبوطي", "signal": "بيع", "strength": "قوي", "bullish": False})
    if b > 0.9 * r and is_bull(i):
        patterns.append({"name": "ماروبوزو صاعد ↑", "type": "استمرار صعودي", "signal": "شراء قوي", "strength": "قوي جداً", "bullish": True})
    if b > 0.9 * r and is_bear(i):
        patterns.append({"name": "ماروبوزو هابط ↓", "type": "استمرار هبوطي", "signal": "بيع قوي", "strength": "قوي جداً", "bullish": False})
    if i >= 1:
        p = i - 1
        if is_bear(p) and is_bull(i) and closes[i] > opens[p] and opens[i] < closes[p]:
            patterns.append({"name": "ابتلاع شرائي ↑", "type": "انعكاس صعودي", "signal": "شراء قوي", "strength": "قوي جداً", "bullish": True})
        if is_bull(p) and is_bear(i) and closes[i] < opens[p] and opens[i] > closes[p]:
            patterns.append({"name": "ابتلاع بيعي ↓", "type": "انعكاس هبوطي", "signal": "بيع قوي", "strength": "قوي جداً", "bullish": False})
    if i >= 2:
        a, b_, c = i-2, i-1, i
        if (is_bear(a) and body(b_) < 0.3*range_(b_) and is_bull(c) and closes[c] > (opens[a]+closes[a])/2):
            patterns.append({"name": "نجمة الصباح ↑", "type": "انعكاس صعودي", "signal": "شراء قوي", "strength": "قوي جداً", "bullish": True})
        if (is_bull(a) and body(b_) < 0.3*range_(b_) and is_bear(c) and closes[c] < (opens[a]+closes[a])/2):
            patterns.append({"name": "نجمة المساء ↓", "type": "انعكاس هبوطي", "signal": "بيع قوي", "strength": "قوي جداً", "bullish": False})
        if all(is_bull(x) and body(x) > 0.6*range_(x) for x in [a, b_, c]) and closes[a] < closes[b_] < closes[c]:
            patterns.append({"name": "ثلاثة جنود بيض ↑", "type": "استمرار صعودي", "signal": "شراء قوي", "strength": "قوي جداً", "bullish": True})
        if all(is_bear(x) and body(x) > 0.6*range_(x) for x in [a, b_, c]) and closes[a] > closes[b_] > closes[c]:
            patterns.append({"name": "ثلاثة غربان سود ↓", "type": "استمرار هبوطي", "signal": "بيع قوي", "strength": "قوي جداً", "bullish": False})

    if not patterns:
        bull = closes[-1] > opens[-1]
        patterns.append({"name": "شمعة صاعدة" if bull else "شمعة هابطة", "type": "استمرار", "signal": "استمرار الاتجاه", "strength": "ضعيف", "bullish": bull})
    return patterns


def liquidity_analysis(closes, volumes, highs, lows):
    if len(closes) < 20 or not volumes:
        return {"error": "insufficient_data"}
    avg_vol_20 = sum(volumes[-20:]) / 20
    avg_vol_5 = sum(volumes[-5:]) / 5
    last_vol = volumes[-1]
    current = closes[-1]
    vol_ratio = last_vol / avg_vol_20 if avg_vol_20 else 1
    obv = [0]
    for i in range(1, len(closes)):
        v = volumes[i] if volumes[i] else 0
        if closes[i] > closes[i-1]:
            obv.append(obv[-1] + v)
        elif closes[i] < closes[i-1]:
            obv.append(obv[-1] - v)
        else:
            obv.append(obv[-1])
    obv_trend = "صاعد" if obv[-1] > obv[-20] else "هابط"
    ad = 0; ad_vals = []
    for i in range(len(closes)):
        h, l, c = highs[i], lows[i], closes[i]
        v = volumes[i] if volumes[i] else 0
        mfm = ((c - l) - (h - c)) / (h - l) if h != l else 0
        ad += mfm * v
        ad_vals.append(ad)
    ad_trend = "تجميع" if ad_vals[-1] > ad_vals[-10] else "تصريف"
    price_move = abs(current - closes[-2]) / closes[-2] * 100 if len(closes) > 1 and closes[-2] else 0
    smart_money = vol_ratio > 2.0 and price_move > 1.0
    price_up = current > closes[-5] if len(closes) >= 5 else True
    vol_expanding = avg_vol_5 > avg_vol_20
    if price_up and vol_expanding:
        signal, score = "شراء مؤسسي — سيولة ذكية داخلة", 80
    elif price_up and not vol_expanding:
        signal, score = "صعود بسيولة متراجعة — ضعيف", 55
    elif not price_up and vol_expanding:
        signal, score = "ضغط بيعي بسيولة قوية — خطر", 30
    else:
        signal, score = "حركة طبيعية", 50
    return {"score": score, "signal": signal, "vol_ratio": round(vol_ratio, 2), "obv_trend": obv_trend, "ad_trend": ad_trend, "smart_money": smart_money, "vol_expanding": vol_expanding, "avg_vol_20": round(avg_vol_20), "last_volume": last_vol, "analysis": f"السيولة: {signal}. نسبة الحجم: {vol_ratio:.1f}x. OBV {obv_trend}. {'✓ سيولة ذكية' if smart_money else ''}. {ad_trend}."}


def gann_theory(closes, highs, lows, dates):
    if len(closes) < 30:
        return {"error": "insufficient_data"}
    current = closes[-1]
    recent_high = max(highs[-60:]) if len(highs) >= 60 else max(highs)
    recent_low = min(lows[-60:]) if len(lows) >= 60 else min(lows)
    swing = recent_high - recent_low
    unit = swing / 45 if swing else 1
    days_from_low = len(closes)
    gann_1x1 = recent_low + days_from_low * unit
    gann_2x1 = recent_low + days_from_low * unit * 2
    gann_1x2 = recent_low + days_from_low * unit * 0.5
    if current > gann_2x1:
        angle_pos, gann_score = "فوق زاوية 2×1 — قوي جداً", 85
    elif current > gann_1x1:
        angle_pos, gann_score = "بين 1×1 و 2×1 — صاعد", 70
    elif current > gann_1x2:
        angle_pos, gann_score = "بين 1×2 و 1×1 — متذبذب", 50
    else:
        angle_pos, gann_score = "تحت زاوية 1×2 — ضعيف", 30
    sqrt_price = math.sqrt(current)
    next_sq = (math.floor(sqrt_price) + 1) ** 2
    cycles = []
    n = len(closes)
    for cycle in [90, 144, 180, 360]:
        if n % cycle < 5 or cycle - (n % cycle) < 5:
            cycles.append(f"دورة {cycle} يوم")
    return {"score": gann_score, "angle_pos": angle_pos, "gann_1x1": round(gann_1x1, 3), "gann_2x1": round(gann_2x1, 3), "gann_1x2": round(gann_1x2, 3), "sqrt_price": round(sqrt_price, 2), "next_sq_level": round(next_sq, 2), "time_cycles": cycles if cycles else ["لا توجد دورات حرجة"], "analysis": f"موقع السعر: {angle_pos}. زاوية 1×1: {gann_1x1:.2f}. مربع السعر: √{current:.0f}={sqrt_price:.1f}."}


def run_technical_analysis(chart_data):
    closes  = [c for c in chart_data.get("closes",  []) if c is not None]
    opens   = [o for o in chart_data.get("opens",   []) if o is not None]
    highs   = [h for h in chart_data.get("highs",   []) if h is not None]
    lows    = [l for l in chart_data.get("lows",    []) if l is not None]
    volumes = [v for v in chart_data.get("volumes", []) if v is not None]
    dates   = chart_data.get("dates", [])

    if len(closes) < 10:
        return {"error": "بيانات تاريخية غير كافية للتحليل"}

    rsi_vals   = rsi(closes)
    macd_data  = macd(closes)
    boll_data  = bollinger(closes)
    stoch_data = stochastic(highs, lows, closes) if highs and lows else {"k": [], "d": []}
    atr_vals   = atr(highs, lows, closes) if highs and lows else []
    sr_data    = calc_support_resistance(closes, highs, lows, closes[-1]) if highs and lows else {}

    def last_valid(lst): return next((v for v in reversed(lst) if v is not None), None)

    current_rsi  = last_valid(rsi_vals)
    current_hist = last_valid(macd_data["histogram"])
    current_atr  = last_valid(atr_vals)
    boll_upper   = last_valid(boll_data["upper"])
    boll_lower   = last_valid(boll_data["lower"])
    boll_mid     = last_valid(boll_data["mid"])
    stoch_k      = last_valid(stoch_data["k"])
    stoch_d      = last_valid(stoch_data["d"])
    sma5_v  = last_valid(sma(closes, 5))
    sma20_v = last_valid(sma(closes, 20))
    sma50_v = last_valid(sma(closes, min(50, len(closes))))
    sma200_v= last_valid(sma(closes, min(200, len(closes))))

    dow_r      = dow_theory(closes, highs, lows, volumes) if highs and lows and volumes else {}
    elliott_r  = elliott_wave(closes, highs, lows) if highs and lows else {}
    candles    = detect_candlestick_patterns(opens, highs, lows, closes) if opens and highs and lows else []
    liquidity_r= liquidity_analysis(closes, volumes, highs, lows) if volumes and highs and lows else {}
    gann_r     = gann_theory(closes, highs, lows, dates) if highs and lows else {}

    scores = [dow_r.get("score", 50), elliott_r.get("score", 50), 65 if sr_data else 50, liquidity_r.get("score", 50), (78 if candles and candles[0].get("bullish") else 30 if candles and candles[0].get("bullish") is False else 55), gann_r.get("score", 50)]
    tech_score = round(sum(scores) / len(scores))
    price = closes[-1]

    return {"price": round(price, 3), "tech_score": tech_score, "rsi": round(current_rsi, 1) if current_rsi else None, "macd_hist": round(current_hist, 4) if current_hist else None, "sma5": round(sma5_v, 3) if sma5_v else None, "sma20": round(sma20_v, 3) if sma20_v else None, "sma50": round(sma50_v, 3) if sma50_v else None, "sma200": round(sma200_v, 3) if sma200_v else None, "boll_upper": round(boll_upper, 3) if boll_upper else None, "boll_mid": round(boll_mid, 3) if boll_mid else None, "boll_lower": round(boll_lower, 3) if boll_lower else None, "stoch_k": round(stoch_k, 1) if stoch_k else None, "stoch_d": round(stoch_d, 1) if stoch_d else None, "atr": round(current_atr, 3) if current_atr else None, "support_resistance": sr_data, "dow": dow_r, "elliott": elliott_r, "candlesticks": candles, "liquidity": liquidity_r, "gann": gann_r}
