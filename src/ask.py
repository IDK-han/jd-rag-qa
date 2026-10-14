"""对 JD 知识库提问：先检索相关段落，再拼成可给大模型用的上下文。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "index.faiss"
META = ROOT / "data" / "meta.json"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def retrieve(question: str, top_k: int = 4) -> list[dict]:
    rows = json.loads(META.read_text(encoding="utf-8"))
    index = faiss.read_index(str(INDEX))
    model = SentenceTransformer(MODEL_NAME)
    q = model.encode([question], normalize_embeddings=True)
    q = np.asarray(q, dtype="float32")
    scores, idxs = index.search(q, top_k)
    hits = []
    for score, i in zip(scores[0], idxs[0]):
        if int(i) < 0:
            continue
        row = rows[int(i)]
        hits.append({**row, "score": float(score)})
    return hits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question", help="你的问题，例如：云体实习要什么技能？")
    parser.add_argument("--top-k", type=int, default=4)
    args = parser.parse_args()

    if not INDEX.exists() or not META.exists():
        raise SystemExit("Missing index. Run: python src/chunk.py && python src/build_index.py")

    hits = retrieve(args.question, top_k=args.top_k)
    print("=== 检索结果 ===")
    for h in hits:
        print(f"[{h['score']:.3f}] {h['source']} :: {h['text'][:120].replace(chr(10), ' ')}...")
    context = "\n\n".join(f"来源:{h['source']}\n{h['text']}" for h in hits)
    print("\n=== 可粘贴给大模型的上下文 ===\n")
    print(context)
    print("\n=== 提示词示例 ===\n")
    print(
        "你是求职助手。只根据下列 JD 片段回答，不知道就说不知道。\n\n"
        f"问题：{args.question}\n\n材料：\n{context}"
    )


if __name__ == "__main__":
    main()
