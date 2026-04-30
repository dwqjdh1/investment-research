"""新闻采集器 — 多数据源聚合 + RAG 向量库回退"""
from datetime import datetime
from sentiment.news_sources import fetch_all_sources, fetch_eastmoney

_NEWS_CACHE: dict[str, tuple[list[dict], float]] = {}
_NEWS_CACHE_TTL = 300


class NewsFetcher:
    """聚合多数据源 + RAG 回退的新闻采集器"""

    def __init__(self, max_articles: int = 10, use_rag: bool = True):
        self.max_articles = max_articles
        self.use_rag = use_rag
        self._rag_store = None

    @property
    def rag_store(self):
        if self._rag_store is None and self.use_rag:
            try:
                from sentiment.rag_store import get_rag_store
                self._rag_store = get_rag_store()
            except Exception:
                self.use_rag = False  # RAG 不可用时降级，不影响主流程
                self._rag_store = None
        return self._rag_store

    def fetch(self, code: str, market: str = None) -> list[dict]:
        cache_key = f"{market or 'auto'}_{code}"
        now = datetime.now().timestamp()
        if cache_key in _NEWS_CACHE:
            cached, ts = _NEWS_CACHE[cache_key]
            if (now - ts) < _NEWS_CACHE_TTL:
                return cached

        articles = self._do_fetch(code, market)
        _NEWS_CACHE[cache_key] = (articles, now)
        return articles

    def _do_fetch(self, code: str, market: str = None) -> list[dict]:
        # 1. 实时多数据源聚合
        articles = fetch_all_sources(code, market, self.max_articles)

        # 2. 实时源不足时，RAG 向量库补充
        if len(articles) < 3 and self.rag_store:
            try:
                rag_articles = self.rag_store.get_recent(code, self.max_articles)
                # 去重合并
                existing_titles = {a["title"][:60] for a in articles}
                for ra in rag_articles:
                    if ra["title"][:60] not in existing_titles:
                        existing_titles.add(ra["title"][:60])
                        articles.append(ra)
            except Exception:
                pass

        return articles[:self.max_articles]

    def index_articles(self, code: str, articles: list[dict]) -> int:
        """将已分析的新闻写入 RAG 向量库"""
        if not articles or not self.rag_store:
            return 0
        try:
            return self.rag_store.add_articles(code, articles)
        except Exception:
            return 0
