"""把 data/jds 下的 JD 文本切成小段，写出 data/chunks.jsonl"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JD_DIR = ROOT / "data" / "jds"
OUT = ROOT / "data" / "chunks.jsonl"


def chunk_text(text: str, max_chars: int = 280, overlap: int = 40) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def main() -> None:
    JD_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted(JD_DIR.glob("*.txt")):
        raw = path.read_text(encoding="utf-8")
        for i, chunk in enumerate(chunk_text(raw)):
            records.append(
                {
                    "id": f"{path.stem}_{i}",
                    "source": path.name,
                    "text": chunk,
                }
            )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} chunks -> {OUT}")


if __name__ == "__main__":
    main()
