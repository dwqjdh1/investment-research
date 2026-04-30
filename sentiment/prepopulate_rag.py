"""预填充 RAG 向量库 — 为热门股票采集并索引新闻"""
from sentiment.news_sources import fetch_all_sources
from sentiment.rag_store import get_rag_store


HOT_STOCKS = [
    # A股
    ("600519", "a_share", "贵州茅台"),
    ("002594", "a_share", "比亚迪"),
    ("300750", "a_share", "宁德时代"),
    ("600036", "a_share", "招商银行"),
    ("601318", "a_share", "中国平安"),
    ("688981", "a_share", "中芯国际"),
    # 港股
    ("00700", "hk_share", "腾讯控股"),
    ("01810", "hk_share", "小米集团"),
    ("03690", "hk_share", "美团"),
    ("09988", "hk_share", "阿里巴巴"),
    ("02015", "hk_share", "理想汽车"),
]


def prepopulate(max_per_stock: int = 10):
    store = get_rag_store()
    total = 0

    for code, market, name in HOT_STOCKS:
        existing = store.count(code)
        if existing >= max_per_stock:
            print(f"  {code} {name}: 已有 {existing} 条，跳过")
            continue

        print(f"  {code} {name}: 采集中...", end=" ", flush=True)
        articles = fetch_all_sources(code, market, max_per_stock)
        if articles:
            # 清旧存新（避免过期新闻累积）
            store.clear_stock(code)
            n = store.add_articles(code, articles)
            print(f"采集 {len(articles)} 条, 索引 {n} 条")
            total += n
        else:
            print(f"未采集到新闻")

    print(f"\n预填充完成：共索引 {total} 条新闻")
    for code, _, name in HOT_STOCKS:
        print(f"  {code} {name}: {store.count(code)} 条")


if __name__ == "__main__":
    prepopulate()
