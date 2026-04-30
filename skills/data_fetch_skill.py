from skills.base import Skill
from data_fetcher import fetch_all_data, detect_market


class DataFetchSkill(Skill):
    name = "data_fetch"
    description = "获取股票基本面、财务、行情、估值数据"
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
            "data": {"type": "object", "description": "fetch_all_data 返回的完整数据"},
        },
    }

    def execute(self, **kwargs):
        code = kwargs["code"]
        market = kwargs.get("market") or detect_market(code)
        data = fetch_all_data(code, market)
        return {"data": data}
