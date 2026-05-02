"""预填充 RAG 向量库 — 为热门股票并行采集并索引新闻"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from sentiment.news_sources import fetch_all_sources
from sentiment.rag_store import get_rag_store


HOT_STOCKS = [
    ("600519", "a_share", "贵州茅台"),
    ("002594", "a_share", "比亚迪"),
    ("300750", "a_share", "宁德时代"),
    ("600036", "a_share", "招商银行"),
    ("601318", "a_share", "中国平安"),
    ("688981", "a_share", "中芯国际"),
    ("000333", "a_share", "美的集团"),
    ("00700", "hk_share", "腾讯控股"),
    ("01810", "hk_share", "小米集团"),
    ("03690", "hk_share", "美团"),
    ("09988", "hk_share", "阿里巴巴"),
    ("02015", "hk_share", "理想汽车"),
]


def prepopulate(max_per_stock: int = 10, max_workers: int = 6):
    store = get_rag_store()
    total = 0

    # 筛选需要采集的股票
    to_fetch = []
    for code, market, name in HOT_STOCKS:
        existing = store.count(code)
        if existing >= max_per_stock:
            print(f"  {code} {name}: 已有 {existing} 条，跳过")
        else:
            to_fetch.append((code, market, name))

    if not to_fetch:
        print("  所有股票新闻数据充足，无需预热")
        return

    # 并行采集新闻
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_all_sources, code, market, max_per_stock): code
            for code, market, _ in to_fetch
        }
        for future in as_completed(futures):
            code = futures[future]
            try:
                articles = future.result()
                results[code] = articles
            except Exception as e:
                print(f"  {code}: 采集失败 - {e}")
                results[code] = []

    # 顺序写入 ChromaDB（线程安全）
    for code, market, name in to_fetch:
        articles = results.get(code, [])
        if articles:
            store.clear_stock(code)
            n = store.add_articles(code, articles)
            print(f"  {code} {name}: 采集 {len(articles)} 条, 索引 {n} 条")
            total += n
        else:
            print(f"  {code} {name}: 未采集到新闻")

    print(f"\n预填充完成：共索引 {total} 条新闻")
    for code, _, name in HOT_STOCKS:
        print(f"  {code} {name}: {store.count(code)} 条")
