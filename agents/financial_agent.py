from agents.base import Agent
from data_fetcher import fetch_all_data, detect_market


class FinancialDataAgent(Agent):
    name = "financial_data"
    description = "获取股票基本面、财务、行情、估值数据"
    input_keys = ["code"]
    output_keys = ["data"]

    def execute(self, context: dict) -> dict:
        code = context["code"]
        market = context.get("market") or detect_market(code)
        data = fetch_all_data(code, market)
        return {"data": data}
