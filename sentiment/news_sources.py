"""多数据源新闻采集 — 聚合多个 AKShare 新闻接口，提高覆盖率"""
import akshare as ak
from datetime import datetime


def _safe_str(val) -> str:
    if val is None:
        return ""
    s = str(val)
    return "" if s in ("nan", "None") else s


def _extract_articles(df, max_articles: int) -> list[dict]:
    """从 DataFrame 提取新闻，自动识别列位置"""
    if df.empty:
        return []
    cols = list(df.columns)
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

    # 位置 fallback（大多数 AKShare 新闻接口列序一致）
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


# ── 各数据源适配器 ──

def fetch_eastmoney(code: str, max_articles: int = 10) -> list[dict]:
    """东方财富个股新闻（主数据源）"""
    try:
        df = ak.stock_news_em(symbol=code)
        return _extract_articles(df, max_articles)
    except Exception:
        return []


def fetch_sina_a(code: str, max_articles: int = 5) -> list[dict]:
    """新浪 A 股新闻"""
    try:
        df = ak.stock_zh_a_news(symbol=code)
        return _extract_articles(df, max_articles)
    except Exception:
        # stock_zh_a_news 可能不存在，尝试 stock_individual_news
        try:
            df = ak.stock_individual_news(symbol=code)
            return _extract_articles(df, max_articles)
        except Exception:
            return []


def fetch_hk_news(code: str, max_articles: int = 10) -> list[dict]:
    """港股新闻"""
    try:
        df = ak.stock_hk_news(symbol=code)
        return _extract_articles(df, max_articles)
    except Exception:
        return []


def fetch_announcements(code: str, max_articles: int = 5) -> list[dict]:
    """A股公司公告（可作为新闻补充）"""
    try:
        df = ak.stock_notice_report(symbol=code)
        if df.empty:
            return []
        articles = []
        for _, row in df.head(max_articles).iterrows():
            title = _safe_str(row.iloc[1]) if len(row) > 1 else ""
            if title:
                articles.append({
                    "title": title,
                    "content": title,
                    "source": "公司公告",
                    "publish_time": _safe_str(row.iloc[0]) if len(row) > 0 else "",
                })
        return articles
    except Exception:
        return []


# ── 聚合采集 ──

def fetch_all_sources(code: str, market: str = None, max_articles: int = 10) -> list[dict]:
    """从所有可用数据源聚合新闻，去重"""
    all_articles = []
    seen_titles = set()

    def add_unique(articles):
        for a in articles:
            key = a["title"][:60]
            if key not in seen_titles:
                seen_titles.add(key)
                all_articles.append(a)

    # 主数据源：东方财富（所有市场通用）
    add_unique(fetch_eastmoney(code, max_articles))

    # 按市场补充
    if market == "hk_share":
        add_unique(fetch_hk_news(code, max_articles))
    else:
        add_unique(fetch_sina_a(code, max_articles // 2))
        add_unique(fetch_announcements(code, max_articles // 2))

    return all_articles[:max_articles]
