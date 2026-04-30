import akshare as ak
from datetime import datetime

_NEWS_CACHE: dict[str, tuple[list[dict], float]] = {}
_NEWS_CACHE_TTL = 300


def _safe_str(val) -> str:
    if val is None:
        return ""
    s = str(val)
    return "" if s in ("nan", "None") else s


def _extract_articles(df, max_articles: int) -> list[dict]:
    """从 DataFrame 中提取新闻，自动识别列位置"""
    cols = list(df.columns)
    # 按列名关键词定位：标题、内容、来源、时间
    col_map = {}
    for i, c in enumerate(cols):
        cstr = str(c)
        if "标题" in cstr or "title" in cstr.lower():
            col_map.setdefault("title", i)
        elif "内容" in cstr or "content" in cstr.lower():
            col_map.setdefault("content", i)
        elif "来源" in cstr or "source" in cstr.lower():
            col_map.setdefault("source", i)
        elif "时间" in cstr or "time" in cstr.lower() or "date" in cstr.lower():
            col_map.setdefault("time", i)

    # 基于位置的 fallback（stock_news_em 固定顺序：关键词/标题/内容/时间/来源/链接）
    if "title" not in col_map and len(cols) >= 2:
        col_map["title"] = 1
    if "content" not in col_map and len(cols) >= 3:
        col_map["content"] = 2
    if "time" not in col_map and len(cols) >= 4:
        col_map["time"] = 3
    if "source" not in col_map and len(cols) >= 5:
        col_map["source"] = 4

    articles = []
    for _, row in df.head(max_articles).iterrows():
        title = _safe_str(row.iloc[col_map["title"]]) if "title" in col_map else ""
        content = _safe_str(row.iloc[col_map["content"]]) if "content" in col_map else title
        source = _safe_str(row.iloc[col_map["source"]]) if "source" in col_map else ""
        pub_time = _safe_str(row.iloc[col_map["time"]]) if "time" in col_map else ""
        if title or content:
            articles.append({
                "title": title,
                "content": content[:500] if content else title[:500],
                "source": source,
                "publish_time": pub_time,
            })
    return articles


class NewsFetcher:
    """从 AKShare 获取股票相关新闻，带 TTL 缓存"""

    def __init__(self, max_articles: int = 10):
        self.max_articles = max_articles

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
        # 主数据源：东方财富个股新闻
        try:
            df = ak.stock_news_em(symbol=code)
            if not df.empty:
                articles = _extract_articles(df, self.max_articles)
                if articles:
                    return articles
        except Exception:
            pass

        # 港股额外数据源
        if market == "hk_share":
            try:
                df = ak.stock_hk_news(symbol=code)
                if not df.empty:
                    return _extract_articles(df, self.max_articles)
            except Exception:
                pass

        return []
