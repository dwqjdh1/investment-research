"""多数据源新闻采集 — 直接请求 API + AKShare 备用"""
import json
import re
from datetime import datetime
import akshare as ak

# 优先使用 curl_cffi（绕过 TLS 指纹检测），降级到普通 requests
try:
    from curl_cffi import requests as cffi_requests
    HTTP_CLIENT = cffi_requests
    CFFI_AVAILABLE = True
except ImportError:
    import requests as cffi_requests
    HTTP_CLIENT = cffi_requests
    CFFI_AVAILABLE = False


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


# ── 直接 API 请求（绕过 akshare bug）──

def fetch_eastmoney_direct(code: str, max_articles: int = 10) -> list[dict]:
    """直接请求东方财富新闻 API（绕过 akshare 正则 bug）"""
    try:
        # 东方财富搜索 API（与 akshare 内部使用同一接口）
        url = "https://search-api-web.eastmoney.com/search/jsonp"
        inner_param = {
            "uid": "",
            "keyword": code,
            "type": ["cmsArticleWebOld"],
            "client": "web",
            "clientType": "web",
            "clientVersion": "curr",
            "param": {
                "cmsArticleWebOld": {
                    "searchScope": "default",
                    "sort": "default",
                    "pageIndex": 1,
                    "pageSize": max_articles,
                    "preTag": "<em>",
                    "postTag": "</em>",
                }
            },
        }
        params = {
            "cb": "jQuery_callback",
            "param": json.dumps(inner_param, ensure_ascii=False),
            "_": "1",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://so.eastmoney.com/news/s",
            "Accept": "*/*",
        }
        # curl_cffi 支持 impersonate 参数模拟浏览器 TLS 指纹
        if CFFI_AVAILABLE:
            resp = HTTP_CLIENT.get(url, params=params, headers=headers, timeout=10, impersonate="chrome120")
        else:
            resp = HTTP_CLIENT.get(url, params=params, headers=headers, timeout=10)
        text = resp.text

        # 提取 JSONP 回调中的 JSON 数据
        start = text.find("(") + 1
        end = text.rfind(")")
        if start <= 0 or end <= start:
            return []
        data = json.loads(text[start:end])

        articles = []
        items = data.get("result", {}).get("cmsArticleWebOld", []) or []
        for item in items[:max_articles]:
            title = item.get("title", "")
            content = item.get("content", "")
            # 清理 HTML 标签和特殊字符
            title = re.sub(r"<em>|</em>", "", title)
            content = re.sub(r"<em>|</em>", "", content)
            content = content.replace("　", "").replace("\r\n", " ")
            source = item.get("mediaName", "")
            pub_time = item.get("date", "")
            if title:
                articles.append({
                    "title": title,
                    "content": content[:500] if content else title[:500],
                    "source": source,
                    "publish_time": pub_time,
                })
        return articles
    except Exception as e:
        print(f"[News] 东方财富 API 请求失败: {e}")
        return []


def fetch_eastmoney(code: str, max_articles: int = 10) -> list[dict]:
    """东方财富个股新闻（优先直接 API，失败则 akshare 备用）"""
    # 优先直接请求 API
    articles = fetch_eastmoney_direct(code, max_articles)
    if articles:
        return articles

    # 备用：akshare（某些环境可能有问题）
    try:
        df = ak.stock_news_em(symbol=code)
        return _extract_articles(df, max_articles)
    except Exception as e:
        print(f"[News] akshare 备用失败: {e}")
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
