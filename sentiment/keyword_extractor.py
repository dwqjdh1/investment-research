"""舆情关键词抽取 — 基于 jieba TF-IDF"""
import jieba.analyse


def extract_keywords(articles: list[dict], top_k: int = 10) -> list[tuple[str, float]]:
    """从新闻列表抽取 TF-IDF 关键词。

    Args:
        articles: 新闻列表，每条至少包含 title / content 字段
        top_k: 返回的关键词数量

    Returns:
        [(关键词, 权重), ...] 按 TF-IDF 权重降序
    """
    if not articles:
        return []

    text_parts: list[str] = []
    for art in articles:
        title = (art.get("title") or "").strip()
        content = (art.get("content") or "").strip()
        if title:
            text_parts.append(title)
        if content:
            text_parts.append(content)

    if not text_parts:
        return []

    text = " ".join(text_parts)

    # 只保留名词、动词、形容词类，过滤助词/代词等噪声
    allow_pos = ("n", "nr", "ns", "nt", "nz", "v", "vn", "a", "ad", "an")

    try:
        keywords = jieba.analyse.extract_tags(
            text, topK=top_k, withWeight=True, allowPOS=allow_pos
        )
    except Exception:
        # POS 标注失败时退化到无词性过滤
        keywords = jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)

    return [(kw, round(float(w), 4)) for kw, w in keywords]


def format_keywords(keywords: list[tuple[str, float]]) -> str:
    """把关键词格式化为人类可读字符串。"""
    if not keywords:
        return "暂无关键词"
    return "、".join(f"{kw}({w:.2f})" for kw, w in keywords)
