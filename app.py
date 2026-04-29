import streamlit as st
from data_fetcher import fetch_all_data, detect_market, search_stock, quick_resolve, warmup_market_data
from report_generator import ReportGenerator
from visualizer import (
    create_financial_trend_chart,
    create_profitability_chart,
    create_valuation_gauge,
    create_price_chart,
)
from config import config

report_gen = ReportGenerator()

HOT_STOCKS = [
    ("贵州茅台", "600519"), ("比亚迪", "002594"), ("宁德时代", "300750"),
    ("招商银行", "600036"), ("中国平安", "601318"), ("中芯国际", "688981"),
    ("腾讯控股", "00700"), ("小米集团", "01810"), ("美团", "03690"),
    ("阿里巴巴", "09988"), ("理想汽车", "02015"),
]

# ── Page config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="智能投研助手",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom theme CSS ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Global Reset and Base Styles */
    .stApp { 
        max-width: 1400px; 
        margin: 0 auto; 
        padding: 2rem 1.5rem; 
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    }
    
    /* Hero Banner - Optimized for WCAG Contrast */
    .hero {
        background: linear-gradient(135deg, #0c1625 0%, #1a2a43 50%, #0c1625 100%);
        border-radius: 24px;
        padding: 3.5rem 4rem;
        margin-bottom: 2.5rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 20px 50px -15px rgba(0, 0, 0, 0.3);
    }
    
    .hero::before {
        content: "";
        position: absolute;
        top: -50%; 
        right: -25%;
        width: 70%; 
        height: 150%;
        background: radial-gradient(circle at 30% 20%, rgba(59, 130, 246, 0.15) 0%, transparent 50%),
                    radial-gradient(circle at 70% 80%, rgba(129, 140, 248, 0.1) 0%, transparent 50%);
        animation: pulse 10s ease-in-out infinite;
    }
    
    .hero h1 { 
        color: #ffffff; 
        font-size: 2.75rem; 
        font-weight: 800; 
        margin: 0; 
        letter-spacing: -0.04em;
        position: relative;
        z-index: 1;
        line-height: 1.1;
    }
    
    .hero p { 
        color: #d1d5db; 
        margin: 1rem 0 0; 
        font-size: 1.15rem;
        font-weight: 400;
        position: relative;
        z-index: 1;
        line-height: 1.5;
    }
    
    .badge {
        display: inline-block; 
        margin-top: 1.5rem;
        background: rgba(59, 130, 246, 0.25); 
        color: #e0f2fe;
        font-size: 0.85rem; 
        font-weight: 700;
        padding: 0.6rem 1.5rem; 
        border-radius: 9999px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        position: relative;
        z-index: 1;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(59, 130, 246, 0.35);
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.7; transform: scale(1.03); }
    }
    
    /* Search Container */
    .search-container {
        background: #ffffff;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.08), 0 2px 8px -3px rgba(0, 0, 0, 0.06);
        border: 1px solid #f0f0f0;
        margin-bottom: 2.5rem;
    }
    
    /* Hot Stocks Container */
    .hotstocks-container {
        background: #ffffff;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.08), 0 2px 8px -3px rgba(0, 0, 0, 0.06);
        border: 1px solid #f0f0f0;
        margin-bottom: 2.5rem;
    }
    
    /* Result Container */
    .result-container {
        background: #ffffff;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.08), 0 2px 8px -3px rgba(0, 0, 0, 0.06);
        border: 1px solid #f0f0f0;
        margin-bottom: 2.5rem;
    }
    
    /* Output Container */
    .output-container {
        background: #ffffff;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.08), 0 2px 8px -3px rgba(0, 0, 0, 0.06);
        border: 1px solid #f0f0f0;
        margin-bottom: 2.5rem;
    }
    
    /* Buttons - WCAG Compliant */
    .stButton > button {
        border-radius: 14px;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        border: none;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        padding: 0.7rem 1.2rem;
        height: auto;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.25);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: #ffffff;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
    }
    
    /* Text Input - Enhanced Accessibility */
    .stTextInput > div > div > input {
        border-radius: 14px;
        border: 2px solid #e5e7eb;
        padding: 0.9rem 1.1rem;
        font-size: 1rem;
        transition: all 0.2s ease;
        background: #fafafa;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #2563eb;
        box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1);
        background: #ffffff;
    }
    
    /* Hot Stocks Section */
    .hot-label { 
        font-size: 0.85rem; 
        color: #374151; 
        font-weight: 700; 
        text-transform: uppercase; 
        letter-spacing: 0.15em; 
        margin-bottom: 1.25rem; 
        margin-top: 0.5rem;
    }
    
    /* Tabs - WCAG Contrast */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.75rem;
        margin-bottom: 1.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 16px 16px 0 0;
        padding: 1rem 1.75rem;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.2s ease;
        color: #4b5563;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: #ffffff;
    }
    
    /* Message Components - WCAG Compliant */
    .stInfo {
        border-radius: 16px;
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border-left: 5px solid #1e40af;
        padding: 1.25rem 1.5rem;
        color: #1e3a5f;
    }
    
    .stSuccess {
        border-radius: 16px;
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border-left: 5px solid #15803d;
        padding: 1.25rem 1.5rem;
        color: #14532d;
    }
    
    .stWarning {
        border-radius: 16px;
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border-left: 5px solid #b45309;
        padding: 1.25rem 1.5rem;
        color: #78350f;
    }
    
    .stError {
        border-radius: 16px;
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border-left: 5px solid #b91c1c;
        padding: 1.25rem 1.5rem;
        color: #7f1d1d;
    }
    
    /* Expander - Enhanced */
    .stExpander {
        border-radius: 20px;
        border: 2px solid #e5e7eb;
        overflow: hidden;
        transition: all 0.2s ease;
        background: #fafafa;
        margin-bottom: 2.5rem;
    }
    
    .stExpander:hover {
        border-color: #d1d5db;
        background: #fafafa;
    }
    
    .stExpander [data-testid="stExpanderHeader"] {
        padding: 1.1rem 1.5rem;
        font-weight: 600;
        font-size: 1rem;
    }
    
    /* Select Box */
    .stSelectbox > div > div {
        border-radius: 14px;
        border: 2px solid #e5e7eb;
        background: #fafafa;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: #2563eb;
        box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1);
        background: #ffffff;
    }
    
    /* Report Styling */
    .report h2 { 
        border-bottom: 4px solid #2563eb; 
        padding-bottom: 1rem;
        color: #111827;
        font-weight: 700;
        font-size: 1.75rem;
        margin-top: 0;
    }
    
    .report h3 { 
        border-left: 5px solid #2563eb; 
        padding-left: 1.25rem;
        color: #1f2937;
        font-weight: 600;
        font-size: 1.35rem;
    }
    
    .report blockquote { 
        border-left: 5px solid #2563eb; 
        background: linear-gradient(90deg, #eff6ff 0%, #ffffff 100%); 
        padding: 1.25rem 1.5rem; 
        border-radius: 0 16px 16px 0;
        margin: 1.25rem 0;
        color: #1e3a5f;
    }
    
    /* Animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(25px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Responsive Improvements */
    @media (max-width: 768px) {
        .stApp {
            padding: 1rem;
        }
        
        .hero {
            padding: 2.5rem 1.75rem;
            margin-bottom: 2rem;
        }
        
        .hero h1 {
            font-size: 2rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ── Init session state ───────────────────────────────────────────
if "report" not in st.session_state:
    st.session_state.report = None
if "price_chart" not in st.session_state:
    st.session_state.price_chart = None
if "trend_chart" not in st.session_state:
    st.session_state.trend_chart = None
if "profit_chart" not in st.session_state:
    st.session_state.profit_chart = None
if "valuation_chart" not in st.session_state:
    st.session_state.valuation_chart = None
if "stock_info" not in st.session_state:
    st.session_state.stock_info = ""


def _generate(code: str, name: str, market: str, base_url: str, api_key: str, model: str):
    """Core report generation (same logic as original _do_generate)."""
    if api_key:
        report_gen.update_llm_config(
            base_url=base_url.strip() if base_url else None,
            api_key=api_key.strip(),
            model=model.strip() if model else None,
        )

    with st.spinner("获取行情中..."):
        data = fetch_all_data(code.strip(), market if market else None)

    info = data.get("info", {})
    stock_name = info.get("name") or name or code
    market_label = "港股" if data.get("market") == "hk_share" else "A股"

    price = info.get("latest_price")
    change = info.get("change_pct")
    meta_parts = []
    if info.get("industry"):
        meta_parts.append(info["industry"])
    if price is not None:
        meta_parts.append(f"最新价 {price:.2f}")
    if change is not None:
        arrow = "▲" if change >= 0 else "▼"
        meta_parts.append(f"{arrow} {abs(change):.2f}%")

    meta_html = " · ".join(meta_parts) if meta_parts else ""

    with st.spinner("绘制图表中..."):
        financial = data.get("financial", {})
        valuation = data.get("valuation", {})
        prices = data.get("prices", {})

        fig_price = create_price_chart(prices, stock_name)
        fig_trend = create_financial_trend_chart(financial, stock_name)
        fig_profit = create_profitability_chart(financial, stock_name)
        fig_valuation = create_valuation_gauge(valuation, stock_name)

    with st.spinner("AI 撰写研报..."):
        report_text, error = report_gen.generate(data)

    if error:
        st.error(f"生成失败: {error}")
        return

    header = f"## {stock_name}  `{code}`  {market_label}\n"
    if meta_html:
        header += f"> *{meta_html}*\n\n---\n"

    st.session_state.report = header + report_text
    st.session_state.price_chart = fig_price
    st.session_state.trend_chart = fig_trend
    st.session_state.profit_chart = fig_profit
    st.session_state.valuation_chart = fig_valuation
    st.session_state.stock_info = f"已生成 {stock_name} ({code}) 的研报"


def _get_llm_config():
    """Return LLM config from session state, falling back to defaults."""
    return (
        st.session_state.get("base_url", config.LLM_BASE_URL),
        st.session_state.get("api_key", config.LLM_API_KEY),
        st.session_state.get("model", config.LLM_MODEL),
    )


def _resolve_and_generate(keyword: str, base_url: str, api_key: str, model: str):
    kw = keyword.strip()
    if not kw:
        return

    code = name = market = ""

    if kw.isdigit():
        resolved = quick_resolve(kw)
        if resolved:
            code, name, market = resolved["code"], resolved["name"], resolved["market"]
        else:
            code = kw
            market = detect_market(code)
    else:
        results = search_stock(kw)
        if results:
            r = results[0]
            code, name, market = r["code"], r["name"], r["market"]

    if not code:
        st.warning(f"无法识别「{kw}」")
        return

    _generate(code, name, market, base_url, api_key, model)


# ── Layout ───────────────────────────────────────────────────────

# Hero banner
st.markdown("""
<div class="hero">
    <h1>智能投研助手</h1>
    <p>输入 A股 / 港股代码或名称，AI 自动生成深度研究报告</p>
    <span class="badge">A 股 · 港股</span>
</div>
""", unsafe_allow_html=True)

# Search bar
search_container = st.container()
with search_container:
    col_search, col_btn1, col_btn2 = st.columns([6, 1.5, 1.5])
    with col_search:
        keyword = st.text_input(
            "搜索股票",
            placeholder="输入代码或公司名称，如 600519、00700、比亚迪、腾讯...",
            key="keyword_input",
            label_visibility="collapsed"
        )
    with col_btn1:
        search_clicked = st.button("🔍 搜索", use_container_width=True)
    with col_btn2:
        generate_clicked = st.button("📊 生成研报", type="primary", use_container_width=True)

# Hot stocks
hot_container = st.container()
with hot_container:
    st.markdown('<p class="hot-label">🔥 热门股票 · 点击即生成</p>', unsafe_allow_html=True)
    first_row = HOT_STOCKS[:6]
    second_row = HOT_STOCKS[6:]
    
    cols1 = st.columns(6)
    for i, (name, code) in enumerate(first_row):
        with cols1[i]:
            if st.button(name, key=f"hot_{code}", use_container_width=True):
                market = detect_market(code)
                base_url, api_key, model = _get_llm_config()
                _generate(code, name, market, base_url, api_key, model)
                st.rerun()
    
    if len(second_row) > 0:
        cols2 = st.columns(6)
        for i, (name, code) in enumerate(second_row):
            with cols2[i]:
                if st.button(name, key=f"hot2_{code}", use_container_width=True):
                    market = detect_market(code)
                    base_url, api_key, model = _get_llm_config()
                    _generate(code, name, market, base_url, api_key, model)
                    st.rerun()

# Search results
if search_clicked and keyword.strip():
    kw = keyword.strip()
    if kw.isdigit():
        resolved = quick_resolve(kw)
        if resolved:
            st.session_state.search_choices = [
                f"{resolved['market_label']} | {resolved['code']} | {resolved['name']}"
            ]
            st.session_state.search_codes = [resolved["code"]]
            st.session_state.search_names = [resolved["name"]]
            st.session_state.search_markets = [resolved["market"]]
            st.info(f"已定位到 {resolved['name']}")
        else:
            st.session_state.search_choices = []
            st.session_state.search_codes = []
            st.session_state.search_names = []
            st.session_state.search_markets = []
            st.warning(f"未找到「{kw}」")
    else:
        results = search_stock(kw)
        if results:
            st.session_state.search_choices = [
                f"{r['market_label']} | {r['code']} | {r['name']}" for r in results
            ]
            st.session_state.search_codes = [r["code"] for r in results]
            st.session_state.search_names = [r["name"] for r in results]
            st.session_state.search_markets = [r["market"] for r in results]
            st.info(f"找到 {len(results)} 只股票")
        else:
            st.session_state.search_choices = []
            st.session_state.search_codes = []
            st.session_state.search_names = []
            st.session_state.search_markets = []
            st.warning(f"未找到「{kw}」")

if generate_clicked and keyword.strip():
    base_url, api_key, model = _get_llm_config()
    _resolve_and_generate(keyword, base_url, api_key, model)
    st.rerun()

# Stock choice dropdown (from search)
search_choices = st.session_state.get("search_choices", [])
if search_choices:
    choice = st.selectbox("选择股票", search_choices, key="stock_select")
    if st.button("✅ 生成所选股票研报", type="primary", key="select_generate"):
        idx = search_choices.index(choice) if choice in search_choices else -1
        if idx >= 0:
            markets = st.session_state.get("search_markets", [])
            code = st.session_state.get("search_codes", [])[idx] if idx < len(st.session_state.get("search_codes", [])) else ""
            name = st.session_state.get("search_names", [])[idx] if idx < len(st.session_state.get("search_names", [])) else ""
            market = markets[idx] if idx < len(markets) else detect_market(code)
            base_url, api_key, model = _get_llm_config()
            _generate(code, name, market, base_url, api_key, model)
            st.rerun()

# API settings
with st.expander("⚙️ API 设置"):
    c1, c2 = st.columns(2)
    base_url_input = c1.text_input("Base URL", value=config.LLM_BASE_URL, key="base_url")
    model_input = c2.text_input("Model", value=config.LLM_MODEL, key="model")
    api_key_input = st.text_input("API Key", value=config.LLM_API_KEY, type="password", key="api_key")

# Status message
if st.session_state.stock_info:
    st.success(st.session_state.stock_info)

# Output tabs
if st.session_state.report:
    tab_report, tab_price, tab_finance = st.tabs(["📄 研报", "📈 走势图", "💹 财务图"])

    with tab_report:
        st.markdown(st.session_state.report)

    with tab_price:
        c1, c2 = st.columns(2)
        if st.session_state.price_chart:
            c1.plotly_chart(st.session_state.price_chart, use_container_width=True)
        if st.session_state.trend_chart:
            c2.plotly_chart(st.session_state.trend_chart, use_container_width=True)

    with tab_finance:
        c1, c2 = st.columns(2)
        if st.session_state.profit_chart:
            c1.plotly_chart(st.session_state.profit_chart, use_container_width=True)
        if st.session_state.valuation_chart:
            c2.plotly_chart(st.session_state.valuation_chart, use_container_width=True)
else:
    st.info("在搜索框输入股票代码或名称，点击 **📊 生成研报** 或从热门股票中选择")
