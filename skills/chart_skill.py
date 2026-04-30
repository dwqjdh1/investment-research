from concurrent.futures import ThreadPoolExecutor
from skills.base import Skill
from visualizer import (
    create_price_chart,
    create_financial_trend_chart,
    create_profitability_chart,
    create_valuation_gauge,
    create_sentiment_gauge,
)


class ChartSkill(Skill):
    name = "chart"
    description = "生成所有可视化图表（价格、财务、估值、舆情）"
    input_schema = {
        "type": "object",
        "properties": {
            "data": {"type": "object", "description": "fetch_all_data 返回的数据"},
            "sentiment": {"type": "object", "description": "SentimentResult 或 None"},
        },
        "required": ["data"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "price_chart": {"type": "object"},
            "trend_chart": {"type": "object"},
            "profit_chart": {"type": "object"},
            "valuation_chart": {"type": "object"},
            "sentiment_chart": {"type": "object"},
        },
    }

    def execute(self, **kwargs):
        data = kwargs["data"]
        sentiment = kwargs.get("sentiment")

        info = data.get("info", {})
        financial = data.get("financial", {})
        valuation = data.get("valuation", {})
        prices = data.get("prices", {})
        stock_name = info.get("name", data.get("code", ""))

        with ThreadPoolExecutor(max_workers=5) as executor:
            f_price = executor.submit(create_price_chart, prices, stock_name)
            f_trend = executor.submit(create_financial_trend_chart, financial, stock_name)
            f_profit = executor.submit(create_profitability_chart, financial, stock_name)
            f_valuation = executor.submit(create_valuation_gauge, valuation, stock_name)
            f_sentiment = executor.submit(create_sentiment_gauge, sentiment, stock_name)

            return {
                "price_chart": f_price.result(),
                "trend_chart": f_trend.result(),
                "profit_chart": f_profit.result(),
                "valuation_chart": f_valuation.result(),
                "sentiment_chart": f_sentiment.result(),
            }
