from agents.base import Agent
from sentiment.analyzer import SentimentAnalyzer


class SentimentAgent(Agent):
    name = "sentiment"
    description = "抓取新闻并分析舆情情感"
    input_keys = ["code"]
    output_keys = ["sentiment"]

    def __init__(self):
        super().__init__()
        self._analyzer = SentimentAnalyzer()

    def execute(self, context: dict) -> dict:
        code = context["code"]
        market = context.get("market")
        sentiment = self._analyzer.analyze(code, market)
        return {"sentiment": sentiment}
