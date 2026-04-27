import uuid
import re
import chromadb
from chromadb.config import Settings
from app.config import settings
from app.services.llm import get_embedding


def _clean_chunk(text: str) -> str:
    """去除chunk中的重复前缀模板"""
    text = text.strip()
    pattern = r"^(该(?:政策)?(?:文件)?(?:《[^》]+》)?(?:的?补贴对象(?:主要包括以下几类主体)?)?)+"
    cleaned = re.sub(pattern, "", text)
    if not cleaned or len(cleaned) < 10:
        return text
    return cleaned


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="policy_chunks",
            metadata={"description": "政策文档分块向量库"}
        )

    def add_chunks(self, policy_id: str, policy_name: str, chunks: list[dict]):
        for chunk in chunks:
            doc_id = f"{policy_id}_chunk_{chunk['index']}"
            embedding = get_embedding(chunk["content"])
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[chunk["content"]],
                metadatas=[{
                    "policy_id": policy_id,
                    "policy_name": policy_name,
                    "chunk_index": chunk["index"],
                    "source": f"政策:{policy_name} 第{chunk['index']+1}段"
                }]
            )

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        query_embedding = get_embedding(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, 8)
        )

        hits = []
        seen = set()
        for i in range(len(results["ids"][0])):
            raw_content = results["documents"][0][i]
            cleaned = _clean_chunk(raw_content)
            content_preview = cleaned[:120]

            if content_preview in seen:
                continue
            seen.add(content_preview)

            hits.append({
                "chunk_id": results["ids"][0][i],
                "content": cleaned,
                "policy_id": results["metadatas"][0][i]["policy_id"],
                "policy_name": results["metadatas"][0][i]["policy_name"],
                "chunk_index": results["metadatas"][0][i]["chunk_index"],
                "distance": results["distances"][0][i] if "distances" in results else 0
            })
        return hits

    def delete_by_policy(self, policy_id: str):
        try:
            results = self.collection.get(where={"policy_id": policy_id})
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
        except Exception:
            pass

    def count(self) -> int:
        return self.collection.count()
