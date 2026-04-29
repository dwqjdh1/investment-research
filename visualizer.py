import plotly.graph_objects as go
from plotly.subplots import make_subplots

COLORS = {
    "primary": "#3b82f6",
    "primary_light": "rgba(59,130,246,0.12)",
    "secondary": "#f59e0b",
    "accent": "#10b981",
    "danger": "#ef4444",
    "grid": "#f1f5f9",
    "text": "#475569",
    "text_light": "#94a3b8",
}

COMMON_LAYOUT = dict(
    template="plotly_white",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=12)),
    margin=dict(l=50, r=30, t=55, b=45),
    font=dict(family="Inter, system-ui, sans-serif", size=12, color=COLORS["text"]),
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
    xaxis=dict(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"]),
    yaxis=dict(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"]),
)


def _style_figure(fig):
    """统一应用样式到所有 figure"""
    fig.update_layout(COMMON_LAYOUT)


def create_financial_trend_chart(financial: dict, stock_name: str) -> go.Figure:
    """营收/净利润趋势图"""
    history = financial.get("history", [])
    if not history:
        fig = go.Figure()
        fig.add_annotation(text="财务历史数据不足", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                           font=dict(size=14, color=COLORS["text_light"]))
        fig.update_layout(**COMMON_LAYOUT)
        return fig

    history = list(reversed(history))
    quarters = [h["quarter"] for h in history]
    revenues = [(h.get("revenue") or 0) / 1e8 for h in history]
    profits = [(h.get("net_profit") or 0) / 1e8 for h in history]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(name="营业总收入(亿)", x=quarters, y=revenues,
               marker_color=COLORS["primary"], marker_line_width=0, opacity=0.85),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(name="净利润(亿)", x=quarters, y=profits, mode="lines+markers",
                   marker_color=COLORS["secondary"], marker_size=8, line_width=2.5),
        secondary_y=True,
    )
    fig.update_layout(
        title=dict(text=f"{stock_name}  ·  营收与净利润趋势", font=dict(size=14, weight=600, color="#1e293b")),
        **COMMON_LAYOUT,
    )
    fig.update_yaxes(title_text="营业总收入(亿)", secondary_y=False, gridcolor=COLORS["grid"])
    fig.update_yaxes(title_text="净利润(亿)", secondary_y=True, gridcolor=COLORS["grid"])
    fig.update_xaxes(gridcolor=COLORS["grid"])
    return fig


def create_profitability_chart(financial: dict, stock_name: str) -> go.Figure:
    """ROE / 毛利率 / 净利率趋势"""
    history = financial.get("history", [])
    if not history:
        fig = go.Figure()
        fig.add_annotation(text="数据不足", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                           font=dict(size=14, color=COLORS["text_light"]))
        fig.update_layout(**COMMON_LAYOUT)
        return fig

    history = list(reversed(history))
    quarters = [h["quarter"] for h in history]
    roe = [h.get("roe") for h in history]
    gross = [h.get("gross_margin") for h in history]
    net = [h.get("net_margin") for h in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        name="ROE(%)", x=quarters, y=roe, mode="lines+markers",
        marker_size=7, line_width=2.5, line_color=COLORS["primary"],
    ))
    fig.add_trace(go.Scatter(
        name="毛利率(%)", x=quarters, y=gross, mode="lines+markers",
        marker_size=7, line_width=2.5, line_color=COLORS["accent"],
    ))
    fig.add_trace(go.Scatter(
        name="净利率(%)", x=quarters, y=net, mode="lines+markers",
        marker_size=7, line_width=2.5, line_color=COLORS["secondary"],
    ))

    fig.update_layout(
        title=dict(text=f"{stock_name}  ·  盈利能力趋势", font=dict(size=14, weight=600, color="#1e293b")),
        **COMMON_LAYOUT,
    )
    fig.update_yaxes(title_text="百分比(%)", gridcolor=COLORS["grid"])
    fig.update_xaxes(gridcolor=COLORS["grid"])
    return fig


def create_valuation_gauge(valuation: dict, stock_name: str) -> go.Figure:
    """PE/PB 估值仪表"""
    pe = valuation.get("pe_current")
    pb = valuation.get("pb_current")
    price = valuation.get("price_latest")

    if pe is None and pb is None:
        fig = go.Figure()
        fig.add_annotation(text="估值数据不足", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                           font=dict(size=14, color=COLORS["text_light"]))
        fig.update_layout(**COMMON_LAYOUT)
        return fig

    fig = go.Figure()

    if pe is not None:
        fig.add_trace(go.Indicator(
            mode="number",
            value=pe,
            title={"text": f"{stock_name}", "font": {"size": 16, "color": "#64748b"}},
            number={"suffix": " 倍 (PE)", "font": {"size": 40, "color": COLORS["primary"], "family": "Inter"}},
        ))
        suffix_parts = []
        if pb is not None:
            suffix_parts.append(f"PB = {pb:.2f}倍")
        if price is not None:
            suffix_parts.append(f"股价 = {price:.2f}元")
        if suffix_parts:
            fig.add_annotation(
                text="  |  ".join(suffix_parts),
                xref="paper", yref="paper", x=0.5, y=-0.08, showarrow=False,
                font=dict(size=13, color=COLORS["text_light"]),
            )
    elif pb is not None:
        fig.add_trace(go.Indicator(
            mode="number",
            value=pb,
            title={"text": f"{stock_name}", "font": {"size": 16, "color": "#64748b"}},
            number={"suffix": " 倍 (PB)", "font": {"size": 40, "color": COLORS["secondary"], "family": "Inter"}},
        ))
        if price is not None:
            fig.add_annotation(
                text=f"股价 = {price:.2f}元  |  PE 暂无数据",
                xref="paper", yref="paper", x=0.5, y=-0.08, showarrow=False,
                font=dict(size=13, color=COLORS["text_light"]),
            )

    fig.update_layout(**COMMON_LAYOUT)
    fig.update_layout(margin=dict(l=40, r=40, t=70, b=50))
    return fig


def create_price_chart(prices: dict, stock_name: str) -> go.Figure:
    """历史价格走势"""
    dates = prices.get("dates", [])
    close = prices.get("close", [])
    if not dates or not close:
        fig = go.Figure()
        fig.add_annotation(text="价格数据不足", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                           font=dict(size=14, color=COLORS["text_light"]))
        fig.update_layout(**COMMON_LAYOUT)
        return fig

    fig = go.Figure()
    dates = dates[-250:]
    close = close[-250:]

    fig.add_trace(go.Scatter(
        name="收盘价", x=dates, y=close,
        mode="lines", line_color=COLORS["primary"], line_width=2,
        fill="tozeroy", fillcolor=COLORS["primary_light"],
    ))
    import pandas as pd
    if len(close) >= 20:
        ma20 = pd.Series(close).rolling(20).mean().tolist()
        fig.add_trace(go.Scatter(
            name="20日均线", x=dates, y=ma20, mode="lines",
            line=dict(color=COLORS["secondary"], width=1.5, dash="dash"),
        ))

    fig.update_layout(
        title=dict(text=f"{stock_name}  ·  历史价格走势", font=dict(size=14, weight=600, color="#1e293b")),
        **COMMON_LAYOUT,
    )
    fig.update_yaxes(title_text="价格(元)", gridcolor=COLORS["grid"])
    fig.update_xaxes(gridcolor=COLORS["grid"])
    return fig
