"""Retrieval eval: Hit@1, Hit@3, MRR over data/eval_queries.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from retrieve import ensure_index, retrieve

ROOT = Path(__file__).resolve().parents[1]
QUERIES = ROOT / "data" / "eval_queries.json"
REPORT = ROOT / "data" / "eval_report.json"


def hit_at_k(ranked_sources: list[str], expected: list[str], k: int) -> float:
    top = ranked_sources[:k]
    return 1.0 if any(s in expected for s in top) else 0.0


def reciprocal_rank(ranked_sources: list[str], expected: list[str]) -> float:
    for i, s in enumerate(ranked_sources, start=1):
        if s in expected:
            return 1.0 / i
    return 0.0


def main() -> None:
    ensure_index()
    queries = json.loads(QUERIES.read_text(encoding="utf-8"))
    rows = []
    hit1s, hit3s, mrrs = [], [], []

    for q in queries:
        question = q["question"]
        expected = q["expected_sources"]
        hits = retrieve(question, top_k=5)
        ranked = [h["source"] for h in hits]
        # unique order-preserving sources for metrics
        seen: list[str] = []
        for s in ranked:
            if s not in seen:
                seen.append(s)
        h1 = hit_at_k(seen, expected, 1)
        h3 = hit_at_k(seen, expected, 3)
        mrr = reciprocal_rank(seen, expected)
        hit1s.append(h1)
        hit3s.append(h3)
        mrrs.append(mrr)
        rows.append(
            {
                "question": question,
                "expected_sources": expected,
                "ranked_sources": seen,
                "top_scores": [round(h["score"], 4) for h in hits[:3]],
                "hit@1": h1,
                "hit@3": h3,
                "mrr": round(mrr, 4),
            }
        )

    n = len(queries) or 1
    summary = {
        "n_queries": len(queries),
        "hit@1": round(sum(hit1s) / n, 4),
        "hit@3": round(sum(hit3s) / n, 4),
        "mrr": round(sum(mrrs) / n, 4),
        "details": rows,
    }
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'Question':<36} {'Hit@1':>6} {'Hit@3':>6} {'MRR':>6}  Top1")
    print("-" * 72)
    for r in rows:
        q_short = r["question"][:34]
        top1 = r["ranked_sources"][0] if r["ranked_sources"] else "-"
        print(
            f"{q_short:<36} {r['hit@1']:>6.0f} {r['hit@3']:>6.0f} {r['mrr']:>6.2f}  {top1}"
        )
    print("-" * 72)
    print(
        f"{'MEAN':<36} {summary['hit@1']:>6.2f} {summary['hit@3']:>6.2f} {summary['mrr']:>6.2f}"
    )
    print(f"\nWrote {REPORT}")


if __name__ == "__main__":
    main()
