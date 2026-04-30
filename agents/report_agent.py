from agents.base import Agent
from report_generator import ReportGenerator


class ReportAgent(Agent):
    name = "report"
    description = "调用LLM生成投资研报"
    input_keys = ["data"]
    output_keys = ["report_text"]

    def __init__(self):
        super().__init__()
        self._generator = ReportGenerator()

    def execute(self, context: dict) -> dict:
        data = context["data"]
        sentiment = context.get("sentiment")
        report, error = self._generator.generate(data, sentiment_data=sentiment)
        return {"report_text": report, "report_error": error}
