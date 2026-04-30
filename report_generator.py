from llm_client import LLMClient
from prompts import SYSTEM_PROMPT, COMPREHENSIVE_REPORT_PROMPT


def _format_basic_info(info: dict) -> str:
    lines = []
    if info.get("name"):
        lines.append(f"- 公司：{info['name']}")
    if info.get("code"):
        lines.append(f"- 代码：{info['code']}")
    if info.get("industry"):
        lines.append(f"- 行业：{info['industry']}")
    if info.get("total_market_cap"):
        lines.append(f"- 总市值：{info['total_market_cap']}")
    if info.get("latest_price") is not None:
        lines.append(f"- 最新价：{info['latest_price']:.2f}元")
    if info.get("change_pct") is not None:
        lines.append(f"- 涨跌幅：{info['change_pct']:.2f}%")
    return "\n".join(lines) if lines else "暂无"


def _format_financial_data(financial: dict) -> str:
    if financial.get("error"):
        return f"数据异常：{financial['error']}"

    lines = [f"报告期：{financial.get('latest_quarter', '未知')}", ""]

    items = [
        ("revenue", "营业总收入", 1e8, "亿"),
        ("net_profit", "净利润", 1e8, "亿"),
        ("eps", "每股收益", 1, "元"),
        ("bps", "每股净资产", 1, "元"),
        ("roe", "ROE", 1, "%"),
        ("gross_margin", "毛利率", 1, "%"),
        ("net_margin", "净利率", 1, "%"),
        ("debt_ratio", "资产负债率", 1, "%"),
    ]
    for key, label, div, unit in items:
        val = financial.get(key)
        if val is not None:
            lines.append(f"- {label}：{val / div:.2f}{unit}")

    # 只保留最近1个季度趋势（削减prompt大小）
    history = financial.get("history", [])
    if history:
        lines.append("")
        lines.append("最新季度趋势：")
        for h in history[:1]:
            parts = [h.get("quarter", "")]
            if h.get("roe") is not None:
                parts.append(f"ROE={h['roe']:.1f}%")
            if h.get("revenue") is not None:
                parts.append(f"营收={h['revenue']/1e8:.1f}亿")
            lines.append(" | ".join(parts))

    return "\n".join(lines)


def _format_valuation_data(valuation: dict) -> str:
    lines = []
    if valuation.get("pe_current") is not None:
        lines.append(f"- PE(TTM)：{valuation['pe_current']:.2f}倍")
    if valuation.get("pb_current") is not None:
        lines.append(f"- PB：{valuation['pb_current']:.2f}倍")
    if valuation.get("change_1m") is not None:
        lines.append(f"- 近1月涨跌：{valuation['change_1m']:.2f}%")
    if valuation.get("change_1y") is not None:
        lines.append(f"- 近1年涨跌：{valuation['change_1y']:.2f}%")
    if valuation.get("price_high_1y"):
        lines.append(f"- 近1年价格区间：{valuation.get('price_low_1y', 0):.2f} - {valuation['price_high_1y']:.2f}元")
    return "\n".join(lines) if lines else "暂无"


def _format_sentiment_data(sentiment) -> str:
    if sentiment is None:
        return "暂无舆情数据"
    lines = [
        f"- 情感倾向：{sentiment.label}",
        f"- 综合得分：{sentiment.score:.2f}（-1极度负面 ~ +1极度正面）",
        f"- 置信度：{sentiment.confidence:.0%}",
        f"- 分析新闻数：{len(sentiment.articles)}条",
    ]
    if sentiment.summary:
        lines.append(f"- 摘要：{sentiment.summary}")
    return "\n".join(lines)


class ReportGenerator:
    def __init__(self, client: LLMClient = None):
        self.client = client or LLMClient()

    def generate(self, data: dict, sentiment_data=None) -> tuple[str, str]:
        name = (data.get("info") or {}).get("name") or data.get("code", "未知")
        prompt = COMPREHENSIVE_REPORT_PROMPT.format(
            stock_name=name,
            stock_code=data.get("code", ""),
            basic_info=_format_basic_info(data.get("info", {})),
            financial_data=_format_financial_data(data.get("financial", {})),
            valuation_data=_format_valuation_data(data.get("valuation", {})),
            sentiment_data=_format_sentiment_data(sentiment_data),
        )
        try:
            report = self.client.generate_report(SYSTEM_PROMPT, prompt)
            return report, ""
        except Exception as e:
            return "", f"LLM调用失败：{str(e)}"

    def generate_stream(self, data: dict, sentiment_data=None):
        """流式生成研报，逐步返回文本块"""
        name = (data.get("info") or {}).get("name") or data.get("code", "未知")
        prompt = COMPREHENSIVE_REPORT_PROMPT.format(
            stock_name=name,
            stock_code=data.get("code", ""),
            basic_info=_format_basic_info(data.get("info", {})),
            financial_data=_format_financial_data(data.get("financial", {})),
            valuation_data=_format_valuation_data(data.get("valuation", {})),
            sentiment_data=_format_sentiment_data(sentiment_data),
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        for chunk in self.client.chat_stream(messages):
            yield chunk

    def update_llm_config(self, base_url: str = None, api_key: str = None, model: str = None):
        self.client.update_config(base_url, api_key, model)
