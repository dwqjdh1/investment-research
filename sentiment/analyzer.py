import json
import re
from dataclasses import dataclass, field
from llm_client import LLMClient
from sentiment.news_fetcher import NewsFetcher

SENTIMENT_SYSTEM_PROMPT = """你是一位金融舆情分析师。分析给定新闻对股价的情感影响，输出严格JSON格式。"""

SENTIMENT_USER_PROMPT = """分析以下 {stock_code} 相关的 {count} 条新闻的情感倾向。

对每条新闻输出:
- sentiment: "positive"(利好) / "negative"(利空) / "neutral"(中性)
- confidence: 0.0~1.0 置信度
- reasoning: 一句话理由

新闻列表:
{news_text}

请严格以JSON数组格式返回，不要包含其他文字:
[{{"index": 0, "sentiment": "...", "confidence": 0.0, "reasoning": "..."}}, ...]

同时返回一个整体摘要（1-2句话）作为最后一个对象的 "summary" 字段。"""


@dataclass
class SentimentResult:
    score: float              # -1.0 (极度负面) ~ +1.0 (极度正面)
    label: str                # "积极" / "中性" / "消极"
    confidence: float         # 整体置信度 0.0 ~ 1.0
    articles: list[dict] = field(default_factory=list)
    summary: str = ""


class SentimentAnalyzer:
    """使用 LLM 分析股票新闻情感"""

    def __init__(self, llm_client: LLMClient = None, max_articles: int = 10):
        self.client = llm_client or LLMClient()
        self.news_fetcher = NewsFetcher(max_articles=max_articles)

    def analyze(self, code: str, market: str = None) -> SentimentResult:
        articles = self.news_fetcher.fetch(code, market)

        if not articles:
            return SentimentResult(
                score=0.0, label="中性", confidence=0.0,
                articles=[], summary="暂无相关新闻数据",
            )

        try:
            per_article = self._call_llm(code, articles)
        except Exception:
            return SentimentResult(
                score=0.0, label="中性", confidence=0.0,
                articles=articles, summary="LLM 情感分析调用失败",
            )

        if not per_article:
            return SentimentResult(
                score=0.0, label="中性", confidence=0.0,
                articles=articles, summary="无法解析情感分析结果",
            )

        score, label, confidence = self._aggregate(per_article)
        summary = self._extract_summary(per_article)

        enriched = []
        for art in per_article:
            idx = art.get("index", 0)
            if idx < len(articles):
                enriched.append({
                    "title": articles[idx]["title"],
                    "sentiment": art.get("sentiment", "neutral"),
                    "confidence": art.get("confidence", 0.5),
                    "reasoning": art.get("reasoning", ""),
                })

        result = SentimentResult(
            score=score, label=label, confidence=confidence,
            articles=enriched, summary=summary,
        )

        # 将已分析新闻写入 RAG 向量库（后台积累）
        try:
            self.news_fetcher.index_articles(code, articles)
        except Exception:
            pass

        return result

    def _call_llm(self, code: str, articles: list[dict]) -> list[dict]:
        news_lines = []
        for i, art in enumerate(articles):
            news_lines.append(f"[{i}] 标题: {art['title']}\n    内容: {art['content'][:300]}")

        prompt = SENTIMENT_USER_PROMPT.format(
            stock_code=code,
            count=len(articles),
            news_text="\n\n".join(news_lines),
        )

        messages = [
            {"role": "system", "content": SENTIMENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        response = self.client.chat(messages, temperature=0.1, max_tokens=1024)
        return self._parse_response(response)

    def _parse_response(self, response: str) -> list[dict]:
        # 尝试直接 JSON 解析
        try:
            data = json.loads(response)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "articles" in data:
                return data["articles"]
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 数组
        m = re.search(r'\[[\s\S]*\]', response)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass

        # 尝试逐个对象提取
        objs = re.findall(r'\{[^{}]*"index"[^{}]*\}', response)
        if objs:
            results = []
            for obj_str in objs:
                try:
                    results.append(json.loads(obj_str))
                except json.JSONDecodeError:
                    continue
            if results:
                return results

        return []

    def _aggregate(self, per_article: list[dict]) -> tuple[float, str, float]:
        total_weight = 0.0
        total_score = 0.0

        sentiment_map = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}

        for art in per_article:
            sent = art.get("sentiment", "neutral")
            conf = float(art.get("confidence", 0.5))
            s = sentiment_map.get(sent, 0.0)
            total_score += s * conf
            total_weight += conf

        if total_weight == 0:
            return 0.0, "中性", 0.0

        score = total_score / total_weight
        score = max(-1.0, min(1.0, score))

        if score > 0.2:
            label = "积极"
        elif score < -0.2:
            label = "消极"
        else:
            label = "中性"

        confidence = total_weight / len(per_article) if per_article else 0.0
        return score, label, confidence

    def _extract_summary(self, per_article: list[dict]) -> str:
        for art in per_article:
            if "summary" in art and art["summary"]:
                return art["summary"]
        return ""
