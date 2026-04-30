from skills.base import Skill
from llm_client import LLMClient


class LLMSkill(Skill):
    name = "llm"
    description = "调用 LLM 进行对话或文本生成"
    input_schema = {
        "type": "object",
        "properties": {
            "system_prompt": {"type": "string"},
            "user_prompt": {"type": "string"},
            "temperature": {"type": "number"},
            "stream": {"type": "boolean"},
        },
        "required": ["user_prompt"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "response": {"type": "string"},
        },
    }

    def __init__(self, client: LLMClient = None):
        self.client = client or LLMClient()

    def execute(self, **kwargs):
        system_prompt = kwargs.get("system_prompt", "")
        user_prompt = kwargs["user_prompt"]
        temperature = kwargs.get("temperature")
        stream = kwargs.get("stream", False)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        if stream:
            return {"response_stream": self.client.chat_stream(messages, temperature=temperature)}

        response = self.client.chat(messages, temperature=temperature)
        return {"response": response}
