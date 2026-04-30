"""RAG 向量存储 — 基于 ChromaDB 的新闻持久化与语义检索"""
import os
import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime


class NewsVectorStore:
    """股票新闻向量存储：持久化新闻嵌入，支持语义检索和历史回查"""

    def __init__(self, persist_dir: str = None):
        persist_dir = persist_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "chroma_db"
        )
        os.makedirs(persist_dir, exist_ok=True)

        self._client = chromadb.PersistentClient(path=persist_dir)
        self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self._get_or_create_collection()

    def _get_or_create_collection(self):
        try:
            self._collection = self._client.get_collection(
                name="stock_news",
                embedding_function=self._embedding_fn,
            )
        except Exception:
            self._collection = self._client.create_collection(
                name="stock_news",
                embedding_function=self._embedding_fn,
                metadata={"description": "股票新闻向量库"},
            )

    # ── 写入 ──

    def add_articles(self, code: str, articles: list[dict]) -> int:
        """将新闻文章写入向量库，返回实际写入数"""
        if not articles:
            return 0

        ids, docs, metadatas = [], [], []
        now_ts = datetime.now().isoformat()

        for i, art in enumerate(articles):
            doc_id = f"{code}_{now_ts}_{i}"
            text = f"{art.get('title', '')} {art.get('content', '')}"[:1000]

            ids.append(doc_id)
            docs.append(text)
            metadatas.append({
                "stock_code": code,
                "title": art.get("title", "")[:200],
                "source": art.get("source", ""),
                "publish_time": art.get("publish_time", ""),
                "indexed_at": now_ts,
            })

        self._collection.add(ids=ids, documents=docs, metadatas=metadatas)
        return len(ids)

    # ── 检索 ──

    def search(self, code: str, query: str = "", n: int = 10) -> list[dict]:
        """语义检索：按股票代码过滤 + 可选语义查询"""
        where = {"stock_code": code}
        try:
            if query:
                results = self._collection.query(
                    query_texts=[query],
                    n_results=n,
                    where=where,
                )
            else:
                # 无查询时返回最近索引的新闻
                results = self._collection.get(
                    where=where,
                    limit=n,
                )

            articles = []
            if results and results.get("metadatas") and results["metadatas"]:
                if query:
                    # query() 返回嵌套列表 [[...]]
                    meta_list = results["metadatas"][0] if results["metadatas"] else []
                    doc_list = results["documents"][0] if results.get("documents") else []
                    dist_list = results["distances"][0] if results.get("distances") else []
                else:
                    # get() 返回扁平列表 [...]
                    meta_list = results["metadatas"]
                    doc_list = results.get("documents", [])
                    dist_list = []

                for i, meta in enumerate(meta_list):
                    if isinstance(meta, dict):
                        articles.append({
                            "title": meta.get("title", ""),
                            "content": doc_list[i][:200] if i < len(doc_list) and doc_list[i] else "",
                            "source": meta.get("source", ""),
                            "publish_time": meta.get("publish_time", ""),
                            "_rag_score": round(dist_list[i], 3) if i < len(dist_list) else None,
                        })
            return articles[:n]
        except Exception:
            return []

    def get_recent(self, code: str, n: int = 10) -> list[dict]:
        """获取最近索引的股票新闻（不进行语义搜索）"""
        return self.search(code, query="", n=n)

    def count(self, code: str = None) -> int:
        """获取已索引新闻数量"""
        try:
            if code:
                result = self._collection.get(where={"stock_code": code})
                return len(result.get("ids", [])) if result else 0
            return self._collection.count()
        except Exception:
            return 0

    def clear_stock(self, code: str) -> int:
        """清除指定股票的新闻"""
        try:
            result = self._collection.get(where={"stock_code": code})
            ids = result.get("ids", []) if result else []
            if ids:
                self._collection.delete(ids=ids)
            return len(ids)
        except Exception:
            return 0


# 全局单例（懒加载）
_store: NewsVectorStore | None = None


def get_rag_store(persist_dir: str = None) -> NewsVectorStore:
    global _store
    if _store is None:
        _store = NewsVectorStore(persist_dir=persist_dir)
    return _store
