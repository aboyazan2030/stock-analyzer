"""
محلل الأسهم الذكي — Stock Analyzer Pro
Streamlit Web App — Saudi (TASI) & US Markets
"""
import streamlit as st
import os
import logging
from datetime import datetime
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from data_fetcher    import StockDataService
from technical_analysis import run_technical_analysis
from analysis_engine import (
    score_fundamentals, analyze_news_sentiment, generate_ai_report
)

# ─── Plotly ───────────────────────────────────────────────────────────────────
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("app")

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="محلل الأسهم الذكي",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');

* { font-family: 'Cairo', 'Segoe UI', sans-serif !important; direction: rtl; }

.main { background: #070B14; }

.metric-card {
    background: linear-gradient(135deg, #111827, #0D1A2E);
    border: 1px solid #1A2540;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    margin-bottom: 8px;
}
.metric-label { font-size: 12px; color: #6B7A99; margin-bottom: 4px; }
.metric-value { font-size: 22px; font-weight: 900; }
.metric-green { color: #00E676; }
.metric-red   { color: #FF3D5A; }
.metric-blue  { color: #00C4FF; }
.metric-gold  { color: #F4C430; }

.section-header {
    background: linear-gradient(90deg, #0D1A2E, transparent);
    border-right: 4px solid #00C4FF;
    padding: 10px 14px;
    margin: 20px 0 12px;
    border-radius: 0 8px 8px 0;
    font-size: 16px;
    font-weight: 800;
    color: #00C4FF;
}

.theory-card {
    background: #111827;
    border: 1px solid #1A2540;
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 8px;
}

.rec-box {
    border-radius: 14px;
    padding: 24px;
    text-align: center;
    margin-bottom: 20px;
}
.rec-buy   { background: linear-gradient(135deg, #00E67618, #111827); border: 2px solid #00E676; }
.rec-sell  { background: linear-gradient(135deg, #FF3D5A18, #111827); border: 2px solid #FF3D5A; }
.rec-hold  { background: linear-gradient(135deg, #00C4FF18, #111827); border: 2px solid #00C4FF; }
.rec-watch { background: linear-gradient(135deg, #F4C43018, #111827); border: 2px solid #F4C430; }

.target-card {
    border-radius: 10px;
    padding: 12px;
    text-align: center;
    margin-bottom: 6px;
}

.news-item {
    background: #111827;
    border: 1px solid #1A2540;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
}

.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
}
.badge-green  { background: #00E67620; color: #00E676; border: 1px solid #00E67640; }
.badge-red    { background: #FF3D5A20; color: #FF3D5A; border: 1px solid #FF3D5A40; }
.badge-yellow { background: #F4C43020; color: #F4C430; border: 1px solid #F4C43040; }
.badge-blue   { background: #00C4FF20; color: #00C4FF; border: 1px solid #00C4FF40; }
.badge-gray   { background: #37414120; color: #8899AA; border: 1px solid #37414140; }

.info-row {
    display: flex;
    justify-content: space-between;
    padding: 7px 0;
    border-bottom: 1px solid #1A254020;
    font-size: 13px;
}
.info-label { color: #6B7A99; }
.info-value { font-weight: 700; color: #E8EDF5; }

.stButton > button {
    background: linear-gradient(135deg, #00C4FF, #0088AA) !important;
    color: #000 !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 800 !important;
    font-size: 16px !important;
    height: 48px !important;
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────
def score_color(s: int) -> str:
    return "metric-green" if s >= 72 else "metric-gold" if s >= 50 else "metric-red"

def rec_class(action: str) -> str:
    a = action.lower()
    if "شراء" in a or "buy" in a:  return "rec-buy"
    if "بيع" in a or "sell" in a:  return "rec-sell"
    if "جني" in a:                  return "rec-watch"
    if "مراقب" in a:               return "rec-watch"
    return "rec-hold"

def rec_color(action: str) -> str:
    a = action.lower()
    if "شراء" in a: return "#00E676"
    if "بيع"  in a: return "#FF3D5A"
    if "جني"  in a: return "#F4C430"
    return "#00C4FF"

def fmt_number(v, suffix="", precision=2) -> str:
    if v is None: return "—"
    if isinstance(v, float) and abs(v) > 1e9:
        return f"{v/1e9:.1f}B {suffix}"
    if isinstance(v, float) and abs(v) > 1e6:
        return f"{v/1e6:.1f}M {suffix}"
    return f"{v:.{precision}f} {suffix}".strip()

def pct(v) -> str:
    if v is None: return "—"
    return f"{v*100:.1f}%" if abs(v) < 10 else f"{v:.1f}%"

def metric_card(label: str, value: str, color_class: str = "metric-blue"):
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value {color_class}">{value}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

def section_header(title: str):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)

def score_badge(score: int) -> str:
    c = "badge-green" if score >= 72 else "badge-yellow" if score >= 50 else "badge-red"
    return f'<span class="badge {c}">{score}/100</span>'


# ─── Chart Builder ────────────────────────────────────────────────────────────
def build_chart(chart_data: dict, technical: dict, symbol: str, currency: str = "") -> go.Figure:
    """
    بناء رسم بياني تفاعلي احترافي يحتوي على:
    - شموع يابانية (OHLC)
    - خطوط المتوسطات (SMA 20, 50, 200)
    - بولينجر باندز
    - مستويات الدعم والمقاومة
    - مؤشر RSI
    - حجم التداول
    """

    dates   = chart_data.get("dates",   [])
    opens   = chart_data.get("opens",   [])
    highs   = chart_data.get("highs",   [])
    lows    = chart_data.get("lows",    [])
    closes  = chart_data.get("closes",  [])
    volumes = chart_data.get("volumes", [])

    if not dates or not closes:
        return None

    # ── Layout: 3 rows (price 60% | RSI 20% | Volume 20%) ───────────────────
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.60, 0.20, 0.20],
        subplot_titles=("", "RSI", "حجم التداول")
    )

    # ── 1. Candlestick ────────────────────────────────────────────────────────
    fig.add_trace(
        go.Candlestick(
            x=dates,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name="السعر",
            increasing_line_color="#00E676",
            decreasing_line_color="#FF3D5A",
            increasing_fillcolor="#00E67640",
            decreasing_fillcolor="#FF3D5A40",
            line=dict(width=1),
        ),
        row=1, col=1
    )

    # ── 2. Moving Averages ────────────────────────────────────────────────────
    def compute_sma(values, n):
        result = []
        for i in range(len(values)):
            if i < n - 1:
                result.append(None)
            else:
                result.append(round(sum(values[i-n+1:i+1]) / n, 3))
        return result

    sma20  = compute_sma(closes, 20)
    sma50  = compute_sma(closes, min(50, len(closes)))
    sma200 = compute_sma(closes, min(200, len(closes)))

    fig.add_trace(go.Scatter(
        x=dates, y=sma20, name="SMA 20",
        line=dict(color="#00C4FF", width=1.5, dash="solid"),
        opacity=0.9, hovertemplate="SMA20: %{y:.3f}<extra></extra>"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=dates, y=sma50, name="SMA 50",
        line=dict(color="#F4C430", width=1.5, dash="solid"),
        opacity=0.9, hovertemplate="SMA50: %{y:.3f}<extra></extra>"
    ), row=1, col=1)

    if len(closes) >= 100:
        fig.add_trace(go.Scatter(
            x=dates, y=sma200, name="SMA 200",
            line=dict(color="#FB923C", width=1.5, dash="dot"),
            opacity=0.8, hovertemplate="SMA200: %{y:.3f}<extra></extra>"
        ), row=1, col=1)

    # ── 3. Bollinger Bands ────────────────────────────────────────────────────
    import statistics as stats_lib

    def compute_bollinger(values, n=20, k=2.0):
        upper, lower, mid = [], [], []
        for i in range(len(values)):
            if i < n - 1:
                upper.append(None); lower.append(None); mid.append(None)
            else:
                window = values[i-n+1:i+1]
                m = sum(window) / n
                std = stats_lib.stdev(window) if len(window) > 1 else 0
                mid.append(round(m, 3))
                upper.append(round(m + k * std, 3))
                lower.append(round(m - k * std, 3))
        return upper, mid, lower

    bb_upper, bb_mid, bb_lower = compute_bollinger(closes)

    fig.add_trace(go.Scatter(
        x=dates, y=bb_upper, name="Bollinger ↑",
        line=dict(color="#9333EA", width=1, dash="dash"),
        opacity=0.6, hovertemplate="BB↑: %{y:.3f}<extra></extra>"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=dates, y=bb_lower, name="Bollinger ↓",
        line=dict(color="#9333EA", width=1, dash="dash"),
        fill="tonexty",
        fillcolor="rgba(147,51,234,0.05)",
        opacity=0.6, hovertemplate="BB↓: %{y:.3f}<extra></extra>"
    ), row=1, col=1)

    # ── 4. Support & Resistance ───────────────────────────────────────────────
    sr = technical.get("support_resistance", {})
    supports    = sr.get("supports", [])
    resistances = sr.get("resistances", [])

    for level in supports[:3]:
        if level:
            fig.add_hline(
                y=level, row=1, col=1,
                line=dict(color="#00E676", width=1, dash="dot"),
                annotation_text=f"دعم {level:.2f}",
                annotation_position="left",
                annotation_font=dict(color="#00E676", size=10),
            )

    for level in resistances[:3]:
        if level:
            fig.add_hline(
                y=level, row=1, col=1,
                line=dict(color="#FF3D5A", width=1, dash="dot"),
                annotation_text=f"مقاومة {level:.2f}",
                annotation_position="left",
                annotation_font=dict(color="#FF3D5A", size=10),
            )

    # ── 5. RSI ────────────────────────────────────────────────────────────────
    def compute_rsi(values, period=14):
        if len(values) < period + 1:
            return [None] * len(values)
        result = [None] * period
        gains, losses = [], []
        for i in range(1, period + 1):
            diff = values[i] - values[i-1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        rs = avg_gain / avg_loss if avg_loss else float("inf")
        result.append(round(100 - 100 / (1 + rs), 2))
        for i in range(period + 1, len(values)):
            diff = values[i] - values[i-1]
            g = max(diff, 0)
            l = max(-diff, 0)
            avg_gain = (avg_gain * (period - 1) + g) / period
            avg_loss = (avg_loss * (period - 1) + l) / period
            rs = avg_gain / avg_loss if avg_loss else float("inf")
            result.append(round(100 - 100 / (1 + rs), 2))
        return result

    rsi_vals = compute_rsi(closes)

    fig.add_trace(go.Scatter(
        x=dates, y=rsi_vals, name="RSI",
        line=dict(color="#00C4FF", width=2),
        hovertemplate="RSI: %{y:.1f}<extra></extra>"
    ), row=2, col=1)

    # RSI zones
    fig.add_hrect(y0=70, y1=100, row=2, col=1,
                  fillcolor="rgba(255,61,90,0.1)", line_width=0)
    fig.add_hrect(y0=0, y1=30, row=2, col=1,
                  fillcolor="rgba(0,230,118,0.1)", line_width=0)
    fig.add_hline(y=70, row=2, col=1,
                  line=dict(color="#FF3D5A", width=1, dash="dot"))
    fig.add_hline(y=30, row=2, col=1,
                  line=dict(color="#00E676", width=1, dash="dot"))
    fig.add_hline(y=50, row=2, col=1,
                  line=dict(color="#6B7A99", width=0.5, dash="dot"))

    # ── 6. Volume Bars ────────────────────────────────────────────────────────
    vol_colors = []
    for i in range(len(closes)):
        if i == 0:
            vol_colors.append("#00C4FF")
        elif closes[i] >= closes[i-1]:
            vol_colors.append("#00E676")
        else:
            vol_colors.append("#FF3D5A")

    fig.add_trace(go.Bar(
        x=dates, y=volumes, name="الحجم",
        marker_color=vol_colors,
        opacity=0.7,
        hovertemplate="الحجم: %{y:,.0f}<extra></extra>"
    ), row=3, col=1)

    # ── Layout Styling ────────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text=f"📊 {symbol} — الرسم البياني التفاعلي",
            font=dict(color="#E8EDF5", size=16, family="Cairo"),
            x=0.5,
        ),
        paper_bgcolor="#070B14",
        plot_bgcolor="#0D1220",
        font=dict(color="#E8EDF5", family="Cairo"),
        height=700,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(17,24,39,0.8)",
            bordercolor="#1A2540",
            borderwidth=1,
            font=dict(size=11),
        ),
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
    )

    # Grid styling for all rows
    for row_n in range(1, 4):
        xaxis_key = "xaxis" if row_n == 1 else f"xaxis{row_n}"
        yaxis_key = "yaxis" if row_n == 1 else f"yaxis{row_n}"

        fig.update_layout(**{
            xaxis_key: dict(
                gridcolor="#1A2540",
                gridwidth=0.5,
                showgrid=True,
                zeroline=False,
                tickfont=dict(color="#6B7A99", size=10),
                showspikes=True,
                spikecolor="#00C4FF",
                spikethickness=1,
                spikedash="dot",
            ),
            yaxis_key: dict(
                gridcolor="#1A2540",
                gridwidth=0.5,
                showgrid=True,
                zeroline=False,
                tickfont=dict(color="#6B7A99", size=10),
                side="right",
                showspikes=True,
                spikecolor="#00C4FF",
                spikethickness=1,
            ),
        })

    # RSI y-axis range
    fig.update_layout(yaxis2=dict(range=[0, 100], tickvals=[30, 50, 70]))

    # Subplot titles styling
    for ann in fig.layout.annotations:
        ann.font.color = "#6B7A99"
        ann.font.size  = 11

    return fig


def show_chart_controls(chart_data: dict) -> dict:
    """عرض خيارات تحكم الرسم البياني"""
    dates  = chart_data.get("dates", [])
    closes = chart_data.get("closes", [])
    total  = len(dates)

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        period_options = {
            "شهر (30 يوم)": 30,
            "3 أشهر": 90,
            "6 أشهر (الكل)": total,
        }
        if total >= 120:
            period_options["4 أشهر"] = 120
        selected_period = st.selectbox(
            "الفترة الزمنية",
            options=list(period_options.keys()),
            index=2,
            key="chart_period"
        )
        n = period_options[selected_period]

    with col2:
        show_options = st.multiselect(
            "عناصر الرسم",
            ["SMA", "Bollinger", "دعم/مقاومة"],
            default=["SMA", "Bollinger", "دعم/مقاومة"],
            key="chart_elements"
        )

    with col3:
        chart_type = st.radio(
            "نوع الرسم",
            ["شموع", "خطي"],
            index=0,
            key="chart_type"
        )

    return {
        "n": n,
        "show_sma": "SMA" in show_options,
        "show_bb": "Bollinger" in show_options,
        "show_sr": "دعم/مقاومة" in show_options,
        "chart_type": chart_type,
    }


# ─── Main App ─────────────────────────────────────────────────────────────────
def main():
    # Sidebar
    with st.sidebar:
        st.markdown("## 📊 محلل الأسهم الذكي")
        st.markdown("---")

        st.markdown("### 🔍 بحث عن سهم")
        symbol = st.text_input(
            "رمز السهم",
            placeholder="مثال: 2222 أو AAPL",
            help="أدخل رمز السهم بالأرقام للسوق السعودي أو بالحروف للأمريكي"
        ).strip().upper()

        market = st.selectbox(
            "السوق",
            options=["saudi", "us"],
            format_func=lambda x: "🇸🇦 السوق السعودي (تاسي)" if x == "saudi" else "🇺🇸 السوق الأمريكي"
        )

        api_key = st.text_input(
            "🔑 مفتاح Claude API (اختياري)",
            type="password",
            placeholder="sk-ant-...",
            help="لتفعيل التحليل الذكي. اتركه فارغاً للتحليل التلقائي"
        )

        analyze_btn = st.button("🔍 تحليل الآن", use_container_width=True)

        st.markdown("---")
        st.markdown("### ⚡ أسهم شائعة")
        quick = {
            "🇸🇦 السوق السعودي": [
                ("2222", "أرامكو"), ("1120", "الراجحي"), ("7010", "STC"),
                ("2010", "سابك"), ("1010", "معادن"), ("2350", "المراعي"),
            ],
            "🇺🇸 السوق الأمريكي": [
                ("AAPL", "أبل"), ("NVDA", "إنفيديا"), ("TSLA", "تسلا"),
                ("MSFT", "مايكروسوفت"), ("AMZN", "أمازون"), ("META", "ميتا"),
            ]
        }
        for group, stocks in quick.items():
            st.caption(group)
            cols = st.columns(3)
            for idx, (sym, name) in enumerate(stocks):
                with cols[idx % 3]:
                    if st.button(sym, key=f"q_{sym}", help=name):
                        st.session_state["quick_symbol"] = sym
                        st.session_state["quick_market"] = "saudi" if group.startswith("🇸🇦") else "us"
                        st.rerun()

        st.markdown("---")
        st.caption("الإصدار 4.0 | تحليل ذكي + رسم بياني تفاعلي")

    # Handle quick select
    if "quick_symbol" in st.session_state:
        symbol = st.session_state.pop("quick_symbol")
        market = st.session_state.pop("quick_market", "saudi")

    # ── Home Screen ───────────────────────────────────────────────────────────
    if not analyze_btn and "result" not in st.session_state:
        st.markdown("""
        <div style="text-align:center; padding: 60px 20px;">
            <div style="font-size:64px; margin-bottom:20px;">📊</div>
            <h1 style="color:#00C4FF; font-size:36px; font-weight:900;">محلل الأسهم الاحترافي</h1>
            <p style="color:#6B7A99; font-size:16px; margin-top:10px;">
                تحليل شامل للأسهم السعودية والأمريكية بالذكاء الاصطناعي
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        features = [
            ("📡", "بيانات حية", "Yahoo Finance — أسعار ومؤشرات وأخبار فورية"),
            ("📈", "6 نظريات فنية", "داو · إليوت · جان · شموع · دعم/مقاومة · سيولة"),
            ("📊", "تحليل أساسي", "14 مؤشر مالي مع مقارنة القطاع"),
            ("🤖", "ذكاء اصطناعي", "Claude AI يدمج كل التحليلات في تقرير احترافي"),
            ("🎯", "توصية نهائية", "شراء/بيع مع أهداف ووقف خسارة"),
            ("🕯️", "رسم بياني تفاعلي", "شموع يابانية + RSI + بولينجر + دعم/مقاومة"),
        ]
        for i, (icon, title, desc) in enumerate(features):
            with [col1, col2, col3][i % 3]:
                st.markdown(
                    f'<div class="theory-card" style="text-align:center">'
                    f'<div style="font-size:28px;margin-bottom:8px">{icon}</div>'
                    f'<div style="font-weight:800;color:#E8EDF5;margin-bottom:4px">{title}</div>'
                    f'<div style="font-size:12px;color:#6B7A99;line-height:1.5">{desc}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        return

    # ── Analysis Flow ─────────────────────────────────────────────────────────
    if analyze_btn:
        if not symbol:
            st.error("⚠️ يرجى إدخال رمز السهم")
            return

        with st.spinner(f"⏳ جاري جلب بيانات {symbol}..."):
            try:
                logger.info(f"Analysis requested: {symbol} / {market}")
                svc = StockDataService()

                status = st.empty()
                status.info("📡 جلب البيانات الحية...")
                raw = svc.get_all(symbol, market)

                status.info("📈 التحليل الفني...")
                technical = {}
                if raw.get("chart"):
                    technical = run_technical_analysis(raw["chart"])

                status.info("📊 التحليل الأساسي...")
                fins = raw.get("fundamentals", {}) or {}
                fund_scores = score_fundamentals(fins)

                status.info("📰 تحليل الأخبار...")
                news_sent = analyze_news_sentiment(raw.get("news", []))

                ai_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
                if ai_key:
                    status.info("🤖 توليد التقرير الذكي...")
                ai_report = generate_ai_report(
                    symbol, market,
                    raw.get("quote", {}),
                    fund_scores, technical, news_sent, fins,
                    api_key=ai_key,
                )

                status.empty()

                st.session_state["result"] = {
                    "symbol":      symbol,
                    "market":      market,
                    "raw":         raw,
                    "technical":   technical,
                    "fund_scores": fund_scores,
                    "news_sent":   news_sent,
                    "ai_report":   ai_report,
                    "fins":        fins,
                }
                logger.info(f"Analysis complete: {symbol}")

            except ValueError as e:
                st.error(f"⚠️ {e}")
                return
            except Exception as e:
                st.error(f"❌ خطأ في التحليل: {e}")
                return

    # ── Display Results ───────────────────────────────────────────────────────
    if "result" not in st.session_state:
        return

    r         = st.session_state["result"]
    raw       = r["raw"]
    technical = r["technical"]
    fund_sc   = r["fund_scores"]
    news_s    = r["news_sent"]
    ai        = r["ai_report"]
    fins      = r["fins"]
    quote     = raw.get("quote", {}) or {}
    rec       = ai.get("recommendation", {})

    # ── Header ────────────────────────────────────────────────────────────────
    name       = quote.get("name") or fins.get("sector") or r["symbol"]
    price      = quote.get("price") or (raw.get("chart",{}) or {}).get("closes",["—"])[-1]
    change     = quote.get("change", 0) or 0
    change_pct = quote.get("change_pct", 0) or 0
    currency   = quote.get("currency") or ""
    market_ar  = "🇸🇦 السوق السعودي" if r["market"] == "saudi" else "🇺🇸 السوق الأمريكي"

    up = change >= 0
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#111827,#0A1422);border:1px solid #1A2540;
         border-radius:14px;padding:20px;margin-bottom:20px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
            <div>
                <h2 style="color:#E8EDF5;margin:0;font-size:22px;font-weight:900">{name}</h2>
                <div style="color:#6B7A99;font-size:13px;margin:4px 0">
                    {r['symbol']} · {market_ar} · {fins.get('sector','') or quote.get('exchange','')}
                </div>
                <div style="margin-top:8px">
                    <span class="badge badge-blue">{raw.get('data_quality','—')}</span>
                    <span class="badge badge-gray" style="margin-right:6px">
                        {datetime.now().strftime('%H:%M')}
                    </span>
                </div>
            </div>
            <div style="text-align:left">
                <div style="font-size:36px;font-weight:900;color:#E8EDF5;line-height:1">
                    {fmt_number(price)} <span style="font-size:16px;color:#6B7A99">{currency}</span>
                </div>
                <div style="color:{'#00E676' if up else '#FF3D5A'};font-size:16px;font-weight:700;margin-top:4px">
                    {'▲' if up else '▼'} {abs(change):.3f} ({'+' if up else ''}{change_pct:.2f}%)
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Key stats row
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: metric_card("أعلى 52 أسبوع", fmt_number(quote.get("week52_high")), "metric-green")
    with c2: metric_card("أدنى 52 أسبوع", fmt_number(quote.get("week52_low")), "metric-red")
    with c3: metric_card("حجم التداول", fmt_number(quote.get("volume"), "", 0), "metric-blue")
    with c4: metric_card("القيمة السوقية", fmt_number(quote.get("market_cap"), currency, 0), "metric-blue")
    with c5: metric_card("التقني", f"{technical.get('tech_score',0)}/100",
                         score_color(technical.get("tech_score",0)))
    with c6: metric_card("الأساسي", f"{fund_sc.get('overall_score',0)}/100",
                         score_color(fund_sc.get("overall_score",0)))

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_chart, tab_rec, tab_tech, tab_fund, tab_news, tab_raw = st.tabs([
        "🕯️ الرسم البياني", "🎯 التوصية", "📈 التحليل الفني",
        "📋 الأساسي", "📰 الأخبار", "📦 البيانات الخام"
    ])

    # ── TAB 0: Chart (الجديد) ─────────────────────────────────────────────────
    with tab_chart:
        chart_data = raw.get("chart") or {}

        if not chart_data or not chart_data.get("closes"):
            st.warning("⚠️ لا تتوفر بيانات تاريخية كافية لعرض الرسم البياني")
        else:
            section_header("🕯️ الرسم البياني التفاعلي")

            # Summary stats above chart
            closes  = chart_data.get("closes", [])
            highs   = chart_data.get("highs", [])
            lows    = chart_data.get("lows", [])
            dates   = chart_data.get("dates", [])
            volumes = chart_data.get("volumes", [])

            if len(closes) >= 2:
                last_close  = closes[-1]
                first_close = closes[0]
                period_chg  = last_close - first_close
                period_pct  = (period_chg / first_close * 100) if first_close else 0
                avg_vol     = sum(v for v in volumes if v) / len([v for v in volumes if v]) if volumes else 0
                period_high = max(highs) if highs else 0
                period_low  = min(lows) if lows else 0

                m1, m2, m3, m4, m5 = st.columns(5)
                with m1:
                    metric_card(
                        f"التغير ({len(closes)} يوم)",
                        f"{'+' if period_chg >= 0 else ''}{period_chg:.2f}",
                        "metric-green" if period_chg >= 0 else "metric-red"
                    )
                with m2:
                    metric_card(
                        "نسبة التغير",
                        f"{'+' if period_pct >= 0 else ''}{period_pct:.1f}%",
                        "metric-green" if period_pct >= 0 else "metric-red"
                    )
                with m3:
                    metric_card("أعلى سعر", fmt_number(period_high), "metric-green")
                with m4:
                    metric_card("أدنى سعر", fmt_number(period_low), "metric-red")
                with m5:
                    metric_card("متوسط الحجم", fmt_number(avg_vol, "", 0), "metric-blue")

            st.markdown("<br>", unsafe_allow_html=True)

            # Build and display chart
            fig = build_chart(
                chart_data, technical,
                symbol=r["symbol"],
                currency=currency
            )

            if fig:
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={
                        "displayModeBar": True,
                        "displaylogo": False,
                        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                        "toImageButtonOptions": {
                            "format": "png",
                            "filename": f"chart_{r['symbol']}",
                            "height": 700,
                            "width": 1400,
                            "scale": 2,
                        },
                    }
                )

            # Chart legend explanation
            with st.expander("📖 دليل قراءة الرسم البياني"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("""
                    **🕯️ الشموع اليابانية**
                    - 🟢 شمعة خضراء = إغلاق أعلى من الافتتاح (صعود)
                    - 🔴 شمعة حمراء = إغلاق أقل من الافتتاح (هبوط)
                    - الظل العلوي = أعلى سعر في اليوم
                    - الظل السفلي = أدنى سعر في اليوم
                    """)
                with col2:
                    st.markdown("""
                    **📊 المتوسطات المتحركة**
                    - 🔵 SMA 20 = متوسط 20 يوم (قصير المدى)
                    - 🟡 SMA 50 = متوسط 50 يوم (متوسط المدى)
                    - 🟠 SMA 200 = متوسط 200 يوم (طويل المدى)
                    - السعر فوق المتوسطات = اتجاه صاعد ✅
                    """)
                with col3:
                    st.markdown("""
                    **📉 RSI (مؤشر القوة النسبية)**
                    - فوق 70 = منطقة تشبع شرائي ⚠️ (بيع محتمل)
                    - تحت 30 = منطقة تشبع بيعي ✅ (شراء محتمل)
                    - 30-70 = منطقة محايدة
                    - الخطوط الأرجوانية = بولينجر باندز
                    """)

    # ── TAB 1: Recommendation ─────────────────────────────────────────────────
    with tab_rec:
        action = rec.get("action", "مراقبة")
        conf   = rec.get("confidence", 50)
        color  = rec_color(action)
        cls    = rec_class(action)

        st.markdown(f"""
        <div class="rec-box {cls}">
            <div style="font-size:12px;color:#6B7A99;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px">
                التوصية النهائية
            </div>
            <div style="font-size:44px;font-weight:900;color:{color};letter-spacing:-1px;margin-bottom:8px">
                {action}
            </div>
            <div style="font-size:15px;color:#6B7A99">
                درجة الثقة: <span style="color:{color};font-weight:900;font-size:20px">{conf}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        with c1: metric_card("الفني", f"{technical.get('tech_score',0)}/100", score_color(technical.get("tech_score",0)))
        with c2: metric_card("الأساسي", f"{fund_sc.get('overall_score',0)}/100", score_color(fund_sc.get("overall_score",0)))
        with c3: metric_card("الأخبار", f"{news_s.get('score',0)}/100", score_color(news_s.get("score",0)))
        with c4: metric_card("السيولة", f"{technical.get('liquidity',{}).get('score',50)}/100",
                              score_color(technical.get("liquidity",{}).get("score",50)))

        st.markdown("<br>", unsafe_allow_html=True)

        entry = rec.get("entry_price", price)
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(f'<div class="target-card" style="background:#00C4FF12;border:1px solid #00C4FF30">'
                        f'<div style="font-size:10px;color:#6B7A99;margin-bottom:4px">سعر الدخول</div>'
                        f'<div style="font-size:20px;font-weight:900;color:#00C4FF">{fmt_number(entry)}</div></div>',
                        unsafe_allow_html=True)
        colors = ["#00E676"] * 3 + ["#FF3D5A"]
        labels = ["الهدف ١", "الهدف ٢", "الهدف ٣", "وقف الخسارة"]
        vals   = [rec.get("target1"), rec.get("target2"), rec.get("target3"), rec.get("stop_loss")]
        for col, lbl, val, clr in zip([c2,c3,c4,c5], labels, vals, colors):
            with col:
                st.markdown(f'<div class="target-card" style="background:{clr}12;border:1px solid {clr}30">'
                            f'<div style="font-size:10px;color:#6B7A99;margin-bottom:4px">{lbl}</div>'
                            f'<div style="font-size:20px;font-weight:900;color:{clr}">{fmt_number(val)}</div></div>',
                            unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.info(f"⚖️ **نسبة المخاطرة/العائد:** {rec.get('risk_reward','—')}")
        with c2:
            st.info(f"⏱️ **مدة التوصية:** {rec.get('timeframe','—')}")

        section_header("🤖 تقرير الذكاء الاصطناعي")
        if ai.get("executive_summary"):
            st.markdown(f"""
            <div style="background:#F4C43010;border:1px solid #F4C43030;border-radius:10px;padding:16px;line-height:1.9">
                {ai['executive_summary']}
            </div>
            """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if ai.get("catalysts"):
                st.markdown("**✅ المحفزات الإيجابية**")
                for c_ in ai["catalysts"]:
                    st.markdown(f"• {c_}")
        with col2:
            if ai.get("risks"):
                st.markdown("**⚠️ المخاطر**")
                for r_ in ai["risks"]:
                    st.markdown(f"• {r_}")

        if ai.get("recommendation", {}).get("reasoning"):
            st.markdown(f"**📝 مبرر التوصية:** {rec['reasoning']}")

    # ── TAB 2: Technical ──────────────────────────────────────────────────────
    with tab_tech:
        if not technical:
            st.warning("⚠️ لا تتوفر بيانات تاريخية كافية للتحليل الفني")
        else:
            section_header("📊 المؤشرات الفنية الرئيسية")
            c1,c2,c3,c4,c5,c6,c7,c8 = st.columns(8)
            inds = [
                ("RSI", technical.get("rsi"), lambda v: "metric-green" if v < 30 else "metric-red" if v > 70 else "metric-blue"),
                ("MACD", technical.get("macd_hist"), lambda v: "metric-green" if v and v > 0 else "metric-red"),
                ("SMA 20", technical.get("sma20"), lambda v: "metric-blue"),
                ("SMA 50", technical.get("sma50"), lambda v: "metric-blue"),
                ("SMA 200", technical.get("sma200"), lambda v: "metric-blue"),
                ("Bollinger ↑", technical.get("boll_upper"), lambda v: "metric-gold"),
                ("Bollinger ↓", technical.get("boll_lower"), lambda v: "metric-gold"),
                ("Stoch K", technical.get("stoch_k"), lambda v: "metric-green" if v and v < 20 else "metric-red" if v and v > 80 else "metric-blue"),
            ]
            for col_, (label, val, color_fn) in zip([c1,c2,c3,c4,c5,c6,c7,c8], inds):
                with col_:
                    metric_card(label, fmt_number(val) if val else "—", color_fn(val))

            section_header("🔬 النظريات الستة")
            col1, col2 = st.columns(2)

            theories = [
                ("📊", "نظرية داو", technical.get("dow", {}),
                 lambda d: f"الاتجاه: {d.get('trend','—')} | {d.get('phase','—')} | إشارة: {d.get('signal','—')}"),
                ("🌊", "موجات إليوت", technical.get("elliott", {}),
                 lambda d: f"الموجة: {d.get('current_wave','—')} ({d.get('wave_type','—')}) | الهدف: {fmt_number(d.get('target'))}"),
                ("💧", "السيولة والفوليوم", technical.get("liquidity", {}),
                 lambda d: f"{d.get('signal','—')} | OBV: {d.get('obv_trend','—')} | {d.get('ad_trend','—')}"),
                ("⚙️", "نظرية جان", technical.get("gann", {}),
                 lambda d: f"{d.get('angle_pos','—')} | مربع: {d.get('sqrt_price','—')}"),
            ]

            for idx, (icon, title, data, desc_fn) in enumerate(theories):
                with [col1, col2][idx % 2]:
                    score = data.get("score", 0)
                    s_color = "#00E676" if score >= 72 else "#F4C430" if score >= 50 else "#FF3D5A"
                    with st.expander(f"{icon} {title} — {score}/100"):
                        st.progress(score / 100)
                        st.markdown(f"**الملخص:** {desc_fn(data)}")
                        if data.get("analysis"):
                            st.markdown(f"**التحليل:** {data['analysis']}")

            section_header("🕯️ نماذج الشموع اليابانية")
            candles = technical.get("candlesticks", [])
            if candles:
                for c_ in candles:
                    bull = c_.get("bullish")
                    cls  = "badge-green" if bull else "badge-red" if bull is False else "badge-yellow"
                    st.markdown(
                        f'<div class="news-item">'
                        f'<span class="badge {cls}" style="margin-left:8px">{c_["signal"]}</span>'
                        f'<strong>{c_["name"]}</strong> — {c_["type"]} — قوة: {c_["strength"]}'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            section_header("🎯 الدعم والمقاومة")
            sr = technical.get("support_resistance", {})
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**🟢 مستويات الدعم**")
                for i, s in enumerate(sr.get("supports", []), 1):
                    st.metric(f"دعم {i}", fmt_number(s))
            with col2:
                st.markdown("**🔴 مستويات المقاومة**")
                for i, r_ in enumerate(sr.get("resistances", []), 1):
                    st.metric(f"مقاومة {i}", fmt_number(r_))
            with col3:
                st.markdown("**📐 مستويات فيبوناتشي**")
                for k, v in sr.get("fibonacci", {}).items():
                    st.metric(f"Fib {k}", fmt_number(v))

            if ai.get("technical_narrative"):
                section_header("🤖 تحليل فني تفصيلي")
                st.markdown(ai["technical_narrative"])

    # ── TAB 3: Fundamentals ───────────────────────────────────────────────────
    with tab_fund:
        if not fins:
            st.warning("⚠️ البيانات الأساسية غير متوفرة")
        else:
            col1, col2 = st.columns([1, 2])
            with col1:
                rating = fund_sc.get("rating", "—")
                r_color = {"ممتازة":"#00E676","جيدة":"#00C4FF","متوسطة":"#F4C430","ضعيفة":"#FF3D5A"}.get(rating, "#6B7A99")
                st.markdown(f"""
                <div style="background:#111827;border:1px solid #1A2540;border-radius:12px;padding:20px;text-align:center">
                    <div style="font-size:12px;color:#6B7A99;margin-bottom:4px">التقييم الأساسي</div>
                    <div style="font-size:32px;font-weight:900;color:{r_color}">{rating}</div>
                    <div style="font-size:20px;font-weight:700;color:#E8EDF5">{fund_sc.get('overall_score',0)}/100</div>
                </div>
                """, unsafe_allow_html=True)
                if fins.get("description"):
                    st.markdown("**عن الشركة**")
                    st.caption(fins["description"])

            with col2:
                section_header("💹 المؤشرات المالية")
                metrics = [
                    ("P/E الحالي",     fmt_number(fins.get("pe_ratio")),           "متوسط القطاع: " + str(fund_sc.get("sector_avgs",{}).get("pe","—"))),
                    ("P/E المستقبلي",  fmt_number(fins.get("forward_pe")),         ""),
                    ("P/B",            fmt_number(fins.get("pb_ratio")),            ""),
                    ("ROE",            pct(fins.get("roe")),                        f"قطاع: {fund_sc.get('sector_avgs',{}).get('roe','—')}%"),
                    ("ROA",            pct(fins.get("roa")),                        ""),
                    ("هامش الربح",     pct(fins.get("net_margin")),                 f"قطاع: {fund_sc.get('sector_avgs',{}).get('margin','—')}%"),
                    ("هامش التشغيل",   pct(fins.get("op_margin")),                 ""),
                    ("نمو الإيرادات",  pct(fins.get("rev_growth")),                ""),
                    ("نمو الأرباح",    pct(fins.get("earn_growth")),               ""),
                    ("الدين/حقوق",     fmt_number(fins.get("debt_to_equity")),      ""),
                    ("نسبة التداول",   fmt_number(fins.get("current_ratio")),       ""),
                    ("عائد التوزيعات", pct(fins.get("div_yield")),                  ""),
                    ("التدفق النقدي الحر", fmt_number(fins.get("free_cash_flow")), ""),
                    ("هدف المحللين",   fmt_number(fins.get("target_price")),        fins.get("analyst_rec","").upper()),
                ]
                for label, val, note in metrics:
                    st.markdown(
                        f'<div class="info-row">'
                        f'<span class="info-label">{label}</span>'
                        f'<span class="info-value">{val} <small style="color:#6B7A99">{note}</small></span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            col1, col2 = st.columns(2)
            with col1:
                section_header("✅ نقاط القوة")
                for s in fund_sc.get("strengths", []):
                    st.markdown(f"✓ {s}")
            with col2:
                section_header("⚠️ نقاط الضعف")
                for w in fund_sc.get("weaknesses", []):
                    st.markdown(f"⚠ {w}")

            if ai.get("fundamental_narrative"):
                section_header("🤖 تحليل أساسي تفصيلي")
                st.markdown(ai["fundamental_narrative"])

    # ── TAB 4: News ───────────────────────────────────────────────────────────
    with tab_news:
        col1, col2, col3 = st.columns(3)
        with col1: metric_card("المشاعر العامة", news_s.get("sentiment","—"),
                               "metric-green" if news_s.get("sentiment")=="إيجابي" else "metric-red" if news_s.get("sentiment")=="سلبي" else "metric-blue")
        with col2: metric_card("درجة الأخبار", f"{news_s.get('score',0)}/100", score_color(news_s.get("score",0)))
        with col3:
            pos = news_s.get("pos_count",0); neg = news_s.get("neg_count",0); neu = news_s.get("neu_count",0)
            metric_card("إيجابي/سلبي/محايد", f"{pos}/{neg}/{neu}", "metric-blue")

        section_header("📰 الأخبار والتحليل")
        analyzed = news_s.get("analyzed", [])
        if analyzed:
            for item in analyzed:
                sent  = item.get("sentiment","محايد")
                s_cls = "badge-green" if sent=="إيجابي" else "badge-red" if sent=="سلبي" else "badge-gray"
                imp   = item.get("impact","—")
                i_cls = "badge-red" if imp=="عالي" else "badge-yellow" if imp=="متوسط" else "badge-gray"
                st.markdown(
                    f'<div class="news-item">'
                    f'<div style="margin-bottom:6px">'
                    f'<span class="badge {s_cls}" style="margin-left:6px">{sent}</span>'
                    f'<span class="badge {i_cls}" style="margin-left:6px">{imp}</span>'
                    f'<strong style="color:#E8EDF5">{item.get("title","")}</strong>'
                    f'</div>'
                    f'<div style="font-size:11px;color:#6B7A99">{item.get("date","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.info("لا تتوفر أخبار حالياً")

        if ai.get("news_narrative"):
            section_header("🤖 تحليل الأخبار بالذكاء الاصطناعي")
            st.markdown(ai["news_narrative"])

    # ── TAB 5: Raw Data ───────────────────────────────────────────────────────
    with tab_raw:
        section_header("📦 البيانات الخام")
        st.markdown(f"""
        - **الرمز المطلوب:** `{r['symbol']}`
        - **رمز Yahoo Finance:** `{raw.get('yahoo_symbol','—')}`
        - **جودة البيانات:** `{raw.get('data_quality','—')}`
        - **وقت الجلب:** `{raw.get('fetched_at','—')}`
        - **الأخطاء:** `{', '.join(raw.get('errors',[])) or 'لا أخطاء'}`
        """)

        if raw.get("errors"):
            for err in raw["errors"]:
                st.warning(f"⚠️ {err}")

        with st.expander("📄 بيانات السعر الخام"):
            st.json(quote)
        with st.expander("📊 إحصائيات البيانات التاريخية"):
            chart = raw.get("chart") or {}
            st.json({
                "symbol": chart.get("symbol"),
                "bars_count": chart.get("count"),
                "date_range": f"{chart.get('dates',['—'])[0] if chart.get('dates') else '—'} → {chart.get('dates',['—'])[-1] if chart.get('dates') else '—'}",
                "last_close": chart.get("closes",["—"])[-1] if chart.get("closes") else "—",
            })
        with st.expander("🏦 البيانات المالية"):
            st.json(fins)


if __name__ == "__main__":
    main()
