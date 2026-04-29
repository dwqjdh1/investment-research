from openai import OpenAI
from config import config


class LLMClient:
    """OpenAI 兼容接口的 LLM 客户端"""

    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        self.base_url = base_url or config.LLM_BASE_URL
        self.api_key = api_key or config.LLM_API_KEY
        self.model = model or config.LLM_MODEL
        self._client = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        return self._client

    def chat(self, messages: list[dict], temperature: float = None, max_tokens: int = None) -> str:
        """发送对话请求并返回文本响应"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or config.TEMPERATURE,
            max_tokens=max_tokens or config.MAX_TOKENS,
        )
        return response.choices[0].message.content

    def generate_report(self, system_prompt: str, user_prompt: str) -> str:
        """生成研报"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.chat(messages)

    def update_config(self, base_url: str = None, api_key: str = None, model: str = None):
        """动态更新配置"""
        if base_url:
            self.base_url = base_url
        if api_key:
            self.api_key = api_key
        if model:
            self.model = model
        self._client = None  # 重置客户端以使用新配置


# 全局单例
llm_client = LLMClient()
