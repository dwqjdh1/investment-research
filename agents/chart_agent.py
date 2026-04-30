from concurrent.futures import ThreadPoolExecutor
from agents.base import Agent
from visualizer import (
    create_price_chart,
    create_financial_trend_chart,
    create_profitability_chart,
    create_valuation_gauge,
    create_sentiment_gauge,
)


class ChartAgent(Agent):
    name = "charts"
    description = "生成所有可视化图表"
    input_keys = ["data"]
    output_keys = ["price_chart", "trend_chart", "profit_chart", "valuation_chart", "sentiment_chart"]

    def execute(self, context: dict) -> dict:
        data = context["data"]
        sentiment = context.get("sentiment")

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
