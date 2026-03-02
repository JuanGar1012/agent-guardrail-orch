from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class DocSearchInput(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    top_k: int = Field(default=3, ge=1, le=10)


async def run_doc_search(data: DocSearchInput) -> dict[str, object]:
    corpus_dir = Path("data/corpus")
    query_terms = [term for term in data.query.lower().split() if term]
    hits: list[dict[str, object]] = []
    for path in sorted(corpus_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8").lower()
        score = sum(content.count(term) for term in query_terms)
        if score > 0:
            hits.append({"doc": path.name, "score": score})
    hits.sort(key=lambda x: int(x["score"]), reverse=True)
    return {"query": data.query, "matches": hits[: data.top_k], "match_count": len(hits)}
