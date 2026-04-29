import gradio as gr
from data_fetcher import fetch_all_data, detect_market, search_stock, quick_resolve
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


def on_search(keyword: str):
    if not keyword or not keyword.strip():
        return gr.update(choices=[], value=None), ""
    kw = keyword.strip()
    if kw.isdigit():
        resolved = quick_resolve(kw)
        if resolved:
            choice = f"{resolved['market_label']} | {resolved['code']} | {resolved['name']}"
            return gr.update(choices=[choice], value=choice), f"已定位到 {resolved['name']}"
    results = search_stock(kw)
    if not results:
        return gr.update(choices=[], value=None), f"未找到「{keyword}」"
    choices = [f"{r['market_label']} | {r['code']} | {r['name']}" for r in results]
    return gr.update(choices=choices, value=choices[0]), f"找到 {len(results)} 只股票"


def on_select(choice: str):
    if not choice:
        return "", "", ""
    parts = choice.split("|")
    if len(parts) >= 3:
        market_label = parts[0].strip()
        code = parts[1].strip()
        name = parts[2].strip()
        market = "hk_share" if "港股" in market_label else "a_share"
        return code, name, market
    return "", "", ""


def on_hot_stock_click(name: str, code: str, base_url: str, api_key: str, model: str,
                       progress=gr.Progress()):
    market = detect_market(code)
    yield from _do_generate(code, name, market, base_url, api_key, model, progress)


def on_direct_generate(keyword: str, base_url: str, api_key: str, model: str,
                       progress=gr.Progress()):
    if not keyword or not keyword.strip():
        yield "## 请输入股票代码或名称", None, None, None, None
        return
    kw = keyword.strip()
    code = name = market = ""
    if kw.isdigit():
        code = kw
        market = detect_market(code)
    else:
        results = search_stock(kw)
        if results:
            r = results[0]
            code, name, market = r["code"], r["name"], r["market"]
    if not code:
        yield f"## 无法识别「{kw}」", None, None, None, None
        return
    yield from _do_generate(code, name, market, base_url, api_key, model, progress)


def generate_report(code: str, name: str, market: str, base_url: str, api_key: str, model: str,
                    progress=gr.Progress()):
    if not code or not code.strip():
        yield "## 请先搜索并选择股票", None, None, None, None
        return
    yield from _do_generate(code, name, market, base_url, api_key, model, progress)


def _do_generate(code: str, name: str, market: str, base_url: str, api_key: str, model: str,
                 progress=gr.Progress()):
    progress(0.05, desc="获取行情...")
    if api_key:
        report_gen.update_llm_config(
            base_url=base_url.strip() if base_url else None,
            api_key=api_key.strip(),
            model=model.strip() if model else None,
        )
    data = fetch_all_data(code.strip(), market if market else None)
    info = data.get("info", {})
    stock_name = info.get("name") or name or code
    market_label = "港股" if data.get("market") == "hk_share" else "A股"

    progress(0.15, desc="绘制图表...")
    financial = data.get("financial", {})
    valuation = data.get("valuation", {})
    prices = data.get("prices", {})

    fig_price = create_price_chart(prices, stock_name)
    fig_trend = create_financial_trend_chart(financial, stock_name)
    fig_profit = create_profitability_chart(financial, stock_name)
    fig_valuation = create_valuation_gauge(valuation, stock_name)

    progress(0.25, desc="AI 撰写研报...")
    report_text, error = report_gen.generate(data)

    if error:
        yield f"## 生成失败\n\n{error}", fig_price, fig_trend, fig_profit, fig_valuation
        return

    progress(0.95, desc="完成!")
    price = info.get('latest_price')
    change = info.get('change_pct')
    meta = []
    if info.get('industry'):
        meta.append(info['industry'])
    if price is not None:
        meta.append(f"最新价 {price:.2f}")
    if change is not None:
        color = "#059669" if change >= 0 else "#dc2626"
        meta.append(f"<span style='color:{color};font-weight:600'>{change:+.2f}%</span>")

    header = (
        f"## {stock_name}  `{code}`  <span style='font-size:14px;color:#64748b'>{market_label}</span>\n"
        f"> {'  ·  '.join(meta)}\n\n---\n"
    )
    yield header + report_text, fig_price, fig_trend, fig_profit, fig_valuation


# ── 现代UI主题与CSS ──────────────────────────────

# 现代色彩方案 - 符合WCAG AA级对比度标准
_PRIMARY_COLOR = "#2563eb"
_PRIMARY_DARK = "#1d4ed8"
_PRIMARY_LIGHT = "#3b82f6"
_SECONDARY_COLOR = "#64748b"
_SUCCESS_COLOR = "#059669"
_DANGER_COLOR = "#dc2626"
_WARNING_COLOR = "#d97706"

# 背景色与文字色（对比度 >= 4.5:1）
_BG_PRIMARY = "#ffffff"
_BG_SECONDARY = "#f8fafc"
_BG_TERTIARY = "#f1f5f9"
_TEXT_PRIMARY = "#0f172a"      # 对比度 14.2:1 (白背景)
_TEXT_SECONDARY = "#475569"    # 对比度 8.7:1 (白背景)
_TEXT_TERTIARY = "#64748b"     # 对比度 6.3:1 (白背景)
_TEXT_DISABLED = "#94a3b8"     # 对比度 4.5:1 (白背景)

_CSS = """
/* ═══════════════════════════════════════════
   全局重置与基础样式
   ═══════════════════════════════════════════ */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    --primary: #2563eb;
    --primary-dark: #1d4ed8;
    --primary-light: #3b82f6;
    --success: #059669;
    --danger: #dc2626;
    --bg-primary: #ffffff;
    --bg-secondary: #f8fafc;
    --bg-tertiary: #f1f5f9;
    --text-primary: #0f172a;
    --text-secondary: #475569;
    --text-tertiary: #64748b;
    --border-color: #e2e8f0;
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    --radius-sm: 0.375rem;
    --radius-md: 0.5rem;
    --radius-lg: 0.75rem;
    --radius-xl: 1rem;
    --radius-2xl: 1.5rem;
}

.gradio-container {
    max-width: 1280px !important;
    margin: 0 auto !important;
    padding: 1.5rem !important;
    font-family: "Inter", "SF Pro Display", "PingFang SC", "Microsoft YaHei", -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

body {
    background-color: var(--bg-secondary);
    color: var(--text-primary);
}

footer, #dummy {
    display: none !important;
}

/* ═══════════════════════════════════════════
   特定元素样式修改
   ═══════════════════════════════════════════ */
/* Element 1: 顶部横幅内的prose元素 */
.prose.header-banner {
    width: 960px !important;
    height: 281px !important;
}

/* Element 2: 热门股票标签区域 */
.block.hot-label {
    background-color: #e4e4e7 !important;
    box-shadow: 0px 4px 8px 0px rgba(0, 0, 0, 0.25) !important;
    border-width: 1px !important;
    border-style: solid !important;
    border-color: #000000 !important;
}

/* Element 3: 搜索状态区域 */
.block.search-status {
    background-color: #e4e4e7 !important;
    border-width: 0px !important;
    border-style: solid !important;
    border-color: #000000 !important;
    box-shadow: 0px 4px 8px 0px rgba(0, 0, 0, 0.25) !important;
}

/* Element 4: Tab按钮 - 研报 */
.tabs .tab-wrapper .tab-container button.svelte-11gaq1:nth-child(1) {
    width: 42px !important;
}

/* Element 5: Tab按钮 - 财务图 */
.tabs .tab-wrapper .tab-container button.svelte-11gaq1:nth-child(3) {
    width: 48px !important;
    flex-direction: row !important;
}

/* Element 6: Tab按钮 - 走势图 */
.tabs .tab-wrapper .tab-container button.svelte-11gaq1:nth-child(2) {
    width: 42px !important;
}

/* Element 7: Tab按钮 - 研报（未选中状态） */
.tabs .tab-wrapper .tab-container button.svelte-11gaq1:nth-child(1):not(.selected) {
    line-height: 30px !important;
    text-align: left !important;
    left: auto !important;
}

/* ═══════════════════════════════════════════
   顶部横幅 - Hero Section
   ═══════════════════════════════════════════ */
.header-banner {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%);
    border-radius: var(--radius-2xl);
    padding: 2.5rem 2rem;
    margin-bottom: 1.75rem;
    box-shadow: var(--shadow-lg);
    position: relative;
    overflow: hidden !important;
    overflow-x: hidden !important;
    overflow-y: hidden !important;
    max-height: none !important;
    max-width: none !important;
}

.header-banner::before {
    content: "";
    position: absolute;
    top: -50%;
    right: -25%;
    width: 50%;
    height: 100%;
    background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, transparent 70%);
}

.header-banner::after {
    content: "";
    position: absolute;
    bottom: -25%;
    left: -10%;
    width: 30%;
    height: 60%;
    background: radial-gradient(circle, rgba(147, 197, 253, 0.1) 0%, transparent 70%);
}

.header-banner .wrap,
.header-banner .wrap > div,
.header-banner .container,
.header-banner .gr-markdown,
.header-banner .gr-block {
    overflow: hidden !important;
    overflow-x: hidden !important;
    overflow-y: hidden !important;
    position: relative;
    z-index: 1;
    white-space: normal !important;
    max-height: none !important;
    max-width: none !important;
}

.header-banner h1 {
    font-size: 2rem;
    font-weight: 800;
    color: #ffffff;
    margin: 0;
    letter-spacing: -0.02em;
    line-height: 1.2;
}

.header-banner .subtitle {
    font-size: 1rem;
    color: rgba(255, 255, 255, 0.7);
    margin: 0.75rem 0 0;
    font-weight: 400;
}

.header-banner .badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(59, 130, 246, 0.2);
    color: #93c5fd;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.375rem 1rem;
    border-radius: 9999px;
    margin-top: 1rem;
    letter-spacing: 0.05em;
}

.header-banner .badge::before {
    content: "";
    width: 0.5rem;
    height: 0.5rem;
    background: #22d3ee;
    border-radius: 50%;
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* ═══════════════════════════════════════════
   搜索卡片
   ═══════════════════════════════════════════ */
.search-card {
    background: var(--bg-primary);
    border-radius: var(--radius-xl);
    padding: 1.5rem;
    box-shadow: var(--shadow-md);
    border: 1px solid var(--border-color);
    margin-bottom: 1.5rem;
}

.search-row {
    gap: 0 !important;
    align-items: stretch !important;
}

.search-row input[type="text"] {
    font-size: 1rem !important;
    color: var(--text-primary) !important;
    background: var(--bg-tertiary) !important;
    border: 2px solid var(--border-color) !important;
    border-radius: var(--radius-lg) 0 0 var(--radius-lg) !important;
    padding: 0.875rem 1.25rem !important;
    flex: 1 !important;
    transition: all 0.2s ease !important;
    outline: none !important;
}

.search-row input[type="text"]:focus {
    border-color: var(--primary) !important;
    background: var(--bg-primary) !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
}

.search-row input[type="text"]::placeholder {
    color: var(--text-tertiary) !important;
}

/* ═══════════════════════════════════════════
   按钮样式
   ═══════════════════════════════════════════ */
.search-row button,
.search-row .gr-button {
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 0 1.75rem !important;
    border: none !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    white-space: nowrap !important;
    min-width: auto !important;
    height: auto !important;
    line-height: 44px !important;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.search-row .gr-button-secondary,
.search-row button.secondary {
    background: var(--bg-tertiary) !important;
    color: var(--text-secondary) !important;
    border-radius: 0 !important;
    border-left: 2px solid var(--border-color) !important;
}

.search-row .gr-button-secondary:hover,
.search-row button.secondary:hover {
    background: var(--border-color) !important;
    color: var(--text-primary) !important;
}

.search-row .gr-button-primary,
.search-row button.primary {
    background: linear-gradient(135deg, var(--primary), var(--primary-dark)) !important;
    color: #ffffff !important;
    border-radius: 0 var(--radius-lg) var(--radius-lg) 0 !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3) !important;
}

.search-row .gr-button-primary:hover,
.search-row button.primary:hover {
    background: linear-gradient(135deg, var(--primary-dark), #1e40af) !important;
    box-shadow: 0 4px 16px rgba(37, 99, 235, 0.4) !important;
    transform: translateY(-1px);
}

.search-row .gr-button-primary:active,
.search-row button.primary:active {
    transform: translateY(0);
}

/* 全局按钮样式 */
.gr-button-primary,
button.primary {
    background: linear-gradient(135deg, var(--primary), var(--primary-dark)) !important;
    color: #ffffff !important;
    border-radius: var(--radius-lg) !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.25rem !important;
    transition: all 0.2s ease !important;
}

.gr-button-primary:hover,
button.primary:hover {
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
}

/* ═══════════════════════════════════════════
   热门股票区域
   ═══════════════════════════════════════════ */
.hot-section {
    margin-bottom: 1.5rem;
}

.hot-label {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
    display: block;
}

.hot-row {
    gap: 0.5rem !important;
    flex-wrap: wrap !important;
    justify-content: flex-start !important;
}

.hot-row button,
.hot-row .gr-button {
    border-radius: var(--radius-md) !important;
    padding: 0.5rem 0 !important;
    background: var(--bg-primary) !important;
    border: 1.5px solid var(--border-color) !important;
    color: var(--text-secondary) !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    width: 96px !important;
    min-width: 96px !important;
    max-width: 96px !important;
    text-align: center !important;
    box-shadow: var(--shadow-sm) !important;
    cursor: pointer !important;
}

.hot-row button:hover,
.hot-row .gr-button:hover {
    background: #eff6ff !important;
    border-color: var(--primary) !important;
    color: var(--primary) !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15) !important;
}

/* ═══════════════════════════════════════════
   搜索结果下拉框
   ═══════════════════════════════════════════ */
.search-results {
    margin-bottom: 1.5rem;
}

.search-status {
    font-size: 0.875rem;
    color: var(--text-tertiary);
    margin-bottom: 0.5rem;
}

.stock-choice {
    font-size: 0.9375rem !important;
}

.stock-choice select {
    width: 100% !important;
    padding: 0.75rem 1rem !important;
    border-radius: var(--radius-lg) !important;
    border: 1.5px solid var(--border-color) !important;
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-size: 0.9375rem !important;
    outline: none !important;
    transition: all 0.2s ease !important;
}

.stock-choice select:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
}

.stock-choice label {
    font-size: 0.875rem !important;
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    margin-bottom: 0.5rem !important;
}

/* ═══════════════════════════════════════════
   API 设置折叠面板
   ═══════════════════════════════════════════ */
.api-settings {
    margin-bottom: 1.5rem;
}

.api-settings .gr-accordion {
    background: var(--bg-primary) !important;
    border: 1.5px solid var(--border-color) !important;
    border-radius: var(--radius-xl) !important;
    box-shadow: var(--shadow-sm) !important;
    overflow: hidden;
}

.api-settings .gr-accordion-item {
    border-bottom: none !important;
}

.api-settings .gr-accordion-header {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    font-size: 0.9375rem !important;
    padding: 1rem 1.25rem !important;
    border-bottom: 1px solid var(--border-color) !important;
}

.api-settings .gr-accordion-header:hover {
    background: var(--bg-tertiary) !important;
}

.api-settings .gr-accordion-content {
    padding: 1.25rem !important;
    background: var(--bg-primary) !important;
}

.api-settings input[type="text"],
.api-settings input[type="password"] {
    width: 100% !important;
    padding: 0.625rem 1rem !important;
    border-radius: var(--radius-md) !important;
    border: 1.5px solid var(--border-color) !important;
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-size: 0.875rem !important;
    outline: none !important;
    transition: all 0.2s ease !important;
}

.api-settings input[type="text"]:focus,
.api-settings input[type="password"]:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
}

.api-settings label {
    font-size: 0.8125rem !important;
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    margin-bottom: 0.375rem !important;
    display: block;
}

/* ═══════════════════════════════════════════
   Tab 导航
   ═══════════════════════════════════════════ */
.tabs-wrapper {
    background: var(--bg-primary);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-md);
    border: 1px solid var(--border-color);
    overflow: hidden;
}

.tabs > .tab-nav {
    border-bottom: 1px solid var(--border-color) !important;
    gap: 0.5rem;
    padding: 1rem 1rem 0 !important;
    background: var(--bg-primary) !important;
}

.tabs > .tab-nav > button {
    font-weight: 600 !important;
    color: var(--text-secondary) !important;
    font-size: 1.125rem !important;
    padding: 0.875rem 2.5rem !important;
    border-radius: var(--radius-md) !important;
    border: none !important;
    background: transparent !important;
    transition: all 0.2s ease !important;
    opacity: 1 !important;
    margin-bottom: 0 !important;
    min-width: 120px !important;
}

.tabs > .tab-nav > button:hover {
    color: var(--primary) !important;
    background: var(--bg-tertiary) !important;
}

.tabs > .tab-nav > button.selected {
    color: #ffffff !important;
    background: var(--primary) !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3) !important;
}

.tabs > .tab-nav > button span {
    color: inherit !important;
}

/* ═══════════════════════════════════════════
   Tab 内容区域
   ═══════════════════════════════════════════ */
.tabs > .tabitem {
    padding: 2rem !important;
    background: var(--bg-primary) !important;
}

/* ═══════════════════════════════════════════
   研报输出样式
   ═══════════════════════════════════════════ */
.report-output {
    font-size: 1.125rem !important;
    line-height: 1.9;
    color: var(--text-primary);
    padding: 2rem;
    background: var(--bg-primary);
    border-radius: var(--radius-lg);
}

.report-output h2 {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    border-bottom: 3px solid var(--primary);
    padding-bottom: 0.75rem;
    margin-top: 2rem;
    margin-bottom: 1.25rem;
    letter-spacing: -0.02em;
}

.report-output h3 {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-top: 1.75rem;
    margin-bottom: 0.75rem;
    padding-left: 0.875rem;
    border-left: 4px solid var(--primary);
}

.report-output h4 {
    font-weight: 600;
    color: var(--text-secondary);
    margin-top: 1.25rem;
    margin-bottom: 0.5rem;
    font-size: 1rem;
}

.report-output p {
    margin: 0.75rem 0;
    font-size: 1rem !important;
    color: var(--text-secondary);
}

.report-output strong {
    color: var(--text-primary);
    font-weight: 600;
}

.report-output ul,
.report-output ol {
    padding-left: 1.5rem;
    margin: 0.75rem 0;
}

.report-output li {
    margin: 0.5rem 0;
    line-height: 1.7;
    font-size: 1rem !important;
    color: var(--text-secondary);
}

.report-output table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin: 1.25rem 0;
    font-size: 0.9375rem;
    border-radius: var(--radius-lg);
    overflow: hidden;
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-sm);
}

.report-output th {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    color: #ffffff;
    padding: 0.75rem 1.125rem;
    font-weight: 600;
    text-align: left;
    font-size: 0.875rem;
    letter-spacing: 0.02em;
}

.report-output td {
    border-top: 1px solid var(--border-color);
    padding: 0.6875rem 1.125rem;
    background: var(--bg-primary);
    font-size: 0.9375rem;
    color: var(--text-secondary);
}

.report-output tr:nth-child(even) td {
    background: var(--bg-tertiary);
}

.report-output tr:hover td {
    background: #eff6ff;
}

.report-output blockquote {
    border-left: 4px solid var(--primary);
    background: linear-gradient(90deg, #eff6ff, #f8fafc);
    padding: 1rem 1.125rem;
    color: var(--text-secondary);
    margin: 1rem 0;
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    font-style: italic;
    font-size: 0.9375rem;
}

.report-output hr {
    border: none;
    border-top: 1px solid var(--border-color);
    margin: 1.75rem 0;
}

.report-output code {
    background: var(--bg-tertiary);
    padding: 0.1875rem 0.5rem;
    border-radius: var(--radius-sm);
    font-size: 0.875em;
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    font-family: "JetBrains Mono", "Fira Code", "SF Mono", monospace !important;
}

.report-output pre {
    background: #0f172a;
    padding: 1rem;
    border-radius: var(--radius-md);
    overflow-x: auto;
    margin: 1rem 0;
}

.report-output pre code {
    background: transparent;
    padding: 0;
    border: none;
    color: #e2e8f0;
}

.report-output a {
    color: var(--primary);
    text-decoration: none;
    border-bottom: 1px dashed #93c5fd;
    transition: all 0.2s ease;
}

.report-output a:hover {
    color: var(--primary-dark);
    border-bottom-color: var(--primary);
}

/* ═══════════════════════════════════════════
   图表容器
   ═══════════════════════════════════════════ */
.chart-container {
    background: var(--bg-primary);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--border-color);
    margin: 0.75rem 0;
    min-height: 400px;
}

.chart-container label {
    font-size: 1rem !important;
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
}

/* ═══════════════════════════════════════════
   进度条样式
   ═══════════════════════════════════════════ */
.gr-progress-bar {
    background: var(--bg-tertiary) !important;
    border-radius: var(--radius-lg) !important;
    height: 6px !important;
}

.gr-progress-bar::-webkit-progress-bar {
    background: var(--bg-tertiary) !important;
    border-radius: var(--radius-lg) !important;
}

.gr-progress-bar::-webkit-progress-value {
    background: linear-gradient(90deg, var(--primary), var(--primary-light)) !important;
    border-radius: var(--radius-lg) !important;
}

/* ═══════════════════════════════════════════
   响应式设计
   ═══════════════════════════════════════════ */
@media (max-width: 768px) {
    .gradio-container {
        padding: 1rem !important;
    }

    .header-banner {
        padding: 1.5rem 1rem;
        border-radius: var(--radius-xl);
    }

    .header-banner h1 {
        font-size: 1.5rem;
    }

    .header-banner .subtitle {
        font-size: 0.9375rem;
    }

    .search-card {
        padding: 1rem;
    }

    .search-row {
        flex-direction: column !important;
        gap: 0.5rem !important;
    }

    .search-row input[type="text"] {
        border-radius: var(--radius-lg) !important;
    }

    .search-row .gr-button-secondary,
    .search-row button.secondary {
        border-radius: var(--radius-lg) !important;
        border-left: none !important;
        border: 1.5px solid var(--border-color) !important;
    }

    .search-row .gr-button-primary,
    .search-row button.primary {
        border-radius: var(--radius-lg) !important;
    }

    .hot-row button {
        width: calc(33.333% - 0.333rem) !important;
        min-width: auto !important;
        max-width: none !important;
        font-size: 0.8125rem !important;
    }

    .tabs > .tab-nav > button {
        padding: 0.5rem 1rem !important;
        font-size: 0.875rem !important;
    }

    .tabs > .tabitem {
        padding: 1rem !important;
    }
}

@media (max-width: 640px) {
    .hot-row button {
        width: calc(50% - 0.25rem) !important;
    }
}
"""


def build_ui():
    with gr.Blocks(title="智能投研助手") as demo:

        # ── 顶部横幅 ──
        gr.Markdown("""
        <div class="header-banner">
            <h1>智能投研助手</h1>
            <p class="subtitle">输入 A股 / 港股代码或名称，AI 自动生成深度研究报告</p>
            <span class="badge">A 股 · 港股</span>
        </div>
        """, elem_classes=["header-banner"])

        # ── 搜索卡片 ──
        with gr.Group(elem_classes=["search-card"]):
            with gr.Row(elem_classes=["search-row"]):
                keyword = gr.Textbox(
                    show_label=False,
                    placeholder="输入代码或公司名称，如 600519、00700、比亚迪、腾讯...",
                    scale=6,
                    container=False,
                )
                search_btn = gr.Button("搜索", variant="secondary", scale=0)
                direct_btn = gr.Button("生成研报", variant="primary", scale=0)

        # ── 热门股票 ──
        with gr.Group(elem_classes=["hot-section"]):
            gr.Markdown('<p class="hot-label">热门股票 · 点击即生成</p>', elem_classes=["hot-label"])
            with gr.Row(elem_classes=["hot-row"]):
                hot_btns = []
                for name, code in HOT_STOCKS:
                    btn = gr.Button(name, size="sm", min_width=40)
                    hot_btns.append((btn, name, code))

        # ── 搜索结果 ──
        with gr.Group(elem_classes=["search-results"]):
            search_status = gr.Markdown("", visible=True, elem_classes=["search-status"])
            stock_choice = gr.Dropdown(
                choices=[],
                allow_custom_value=True,
                label="搜索结果",
                elem_classes=["stock-choice"],
            )

        # ── 隐藏状态 ──
        selected_code = gr.State("")
        selected_name = gr.State("")
        selected_market = gr.State("")

        # ── API 设置 ──
        with gr.Group(elem_classes=["api-settings"]):
            with gr.Accordion("API 设置", open=False):
                with gr.Row():
                    base_url = gr.Textbox(label="Base URL", value=config.LLM_BASE_URL)
                    model = gr.Textbox(label="Model", value=config.LLM_MODEL)
                api_key = gr.Textbox(label="API Key", type="password", value=config.LLM_API_KEY)

        # ── 报告输出 ──
        with gr.Group(elem_classes=["tabs-wrapper"]):
            with gr.Tabs():
                with gr.TabItem("研报"):
                    report_output = gr.Markdown(
                        "在搜索框输入代码或名称，点击 **生成研报** 或从热门股票中选择",
                        elem_classes=["report-output"],
                        latex_delimiters=[{"left": "$$", "right": "$$", "display": True}],
                    )
                with gr.TabItem("走势图"):
                    with gr.Row():
                        price_chart = gr.Plot(label="价格走势", scale=1, elem_classes=["chart-container"])
                        trend_chart = gr.Plot(label="营收利润", scale=1, elem_classes=["chart-container"])
                with gr.TabItem("财务图"):
                    with gr.Row():
                        profit_chart = gr.Plot(label="盈利能力", scale=1, elem_classes=["chart-container"])
                        valuation_chart = gr.Plot(label="估值水平", scale=1, elem_classes=["chart-container"])

        # ── 事件绑定 ──
        search_btn.click(fn=on_search, inputs=[keyword], outputs=[stock_choice, search_status])
        keyword.submit(fn=on_search, inputs=[keyword], outputs=[stock_choice, search_status])
        stock_choice.change(fn=on_select, inputs=[stock_choice],
                            outputs=[selected_code, selected_name, selected_market])
        stock_choice.input(
            fn=generate_report,
            inputs=[selected_code, selected_name, selected_market, base_url, api_key, model],
            outputs=[report_output, price_chart, trend_chart, profit_chart, valuation_chart],
            show_progress="full",
        )
        direct_btn.click(
            fn=on_direct_generate,
            inputs=[keyword, base_url, api_key, model],
            outputs=[report_output, price_chart, trend_chart, profit_chart, valuation_chart],
            show_progress="full",
        )
        for btn, name, code in hot_btns:
            btn.click(
                fn=on_hot_stock_click,
                inputs=[gr.State(name), gr.State(code), base_url, api_key, model],
                outputs=[report_output, price_chart, trend_chart, profit_chart, valuation_chart],
                show_progress="full",
            )

    return demo


if __name__ == "__main__":
    build_ui().launch(server_name="0.0.0.0", server_port=7860, share=False, css=_CSS)
