"""把 chunks.jsonl 做成向量索引 data/index.faiss + data/meta.json"""
from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data" / "chunks.jsonl"
INDEX = ROOT / "data" / "index.faiss"
META = ROOT / "data" / "meta.json"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def main() -> None:
    rows = []
    with CHUNKS.open(encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    if not rows:
        raise SystemExit("No chunks. Run: python src/chunk.py")

    texts = [r["text"] for r in rows]
    print(f"Loading model {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)
    emb = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    emb = np.asarray(emb, dtype="float32")

    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    faiss.write_index(index, str(INDEX))
    META.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexed {len(rows)} chunks -> {INDEX}")


if __name__ == "__main__":
    main()
