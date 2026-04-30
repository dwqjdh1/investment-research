from skills.base import Skill
from sentiment.analyzer import SentimentAnalyzer


class SentimentSkill(Skill):
    name = "sentiment"
    description = "抓取股票新闻并分析市场情感倾向"
    input_schema = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "股票代码"},
            "market": {"type": "string", "description": "市场: a_share / hk_share"},
        },
        "required": ["code"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "sentiment": {"type": "object", "description": "SentimentResult"},
        },
    }

    def __init__(self):
        self._analyzer = SentimentAnalyzer()

    def execute(self, **kwargs):
        code = kwargs["code"]
        market = kwargs.get("market")
        sentiment = self._analyzer.analyze(code, market)
        return {"sentiment": sentiment}
