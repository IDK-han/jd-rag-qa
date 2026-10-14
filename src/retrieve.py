"""Shared retrieve: lazy-load ST model + FAISS once for ask / eval / app."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "data" / "index.faiss"
META_PATH = ROOT / "data" / "meta.json"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_model = None
_index = None
_rows: list[dict[str, Any]] | None = None


def ensure_index() -> None:
    if not INDEX_PATH.exists() or not META_PATH.exists():
        raise SystemExit(
            "Missing index. Run: python src/chunk.py && python src/build_index.py"
        )


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def get_index():
    global _index
    ensure_index()
    if _index is None:
        _index = faiss.read_index(str(INDEX_PATH))
    return _index


def get_rows() -> list[dict[str, Any]]:
    global _rows
    ensure_index()
    if _rows is None:
        _rows = json.loads(META_PATH.read_text(encoding="utf-8"))
    return _rows


def retrieve(question: str, top_k: int = 4) -> list[dict[str, Any]]:
    """Return top_k hits with score, source, text, id."""
    rows = get_rows()
    index = get_index()
    model = get_model()
    q = model.encode([question], normalize_embeddings=True)
    q = np.asarray(q, dtype="float32")
    scores, idxs = index.search(q, top_k)
    hits: list[dict[str, Any]] = []
    for score, i in zip(scores[0], idxs[0]):
        if int(i) < 0:
            continue
        row = rows[int(i)]
        hits.append({**row, "score": float(score)})
    return hits


def build_context(hits: list[dict[str, Any]]) -> str:
    return "\n\n".join(f"来源:{h['source']}\n{h['text']}" for h in hits)


def build_prompt(question: str, hits: list[dict[str, Any]]) -> str:
    context = build_context(hits)
    return (
        "你是求职助手。只根据下列 JD 片段回答，不知道就说不知道。\n\n"
        f"问题：{question}\n\n材料：\n{context}"
    )


def _load_dotenv() -> None:
    """Load KEY=VALUE from project .env into os.environ if not already set."""
    import os

    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def call_llm(prompt: str) -> str | None:
    """Call OpenAI-compatible chat API if API key is set. Returns answer or None."""
    import os

    _load_dotenv()
    deepseek = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not deepseek and not openai_key:
        return None

    try:
        from openai import OpenAI
    except ImportError as e:
        raise SystemExit("Install openai: pip install openai") from e

    if deepseek:
        client = OpenAI(api_key=deepseek, base_url="https://api.deepseek.com")
        model = os.environ.get("LLM_MODEL", "deepseek-chat")
    else:
        client = OpenAI(api_key=openai_key)
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "你是求职助手。只根据用户提供的 JD 材料回答，不知道就说不知道。",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()
