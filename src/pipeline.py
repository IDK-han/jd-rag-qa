"""One-shot: crawl (optional) → chunk → build_index.

Examples:
  python src/pipeline.py
  python src/pipeline.py --demo
  python src/pipeline.py --url https://jobs.lever.co/.../...
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=ROOT)


def main() -> int:
    p = argparse.ArgumentParser(description="crawl → chunk → build_index")
    p.add_argument("--url", action="append", default=[], help="Pass through to crawl.py")
    p.add_argument("--urls-file", type=str, default=None)
    p.add_argument("--demo", action="store_true", help="Crawl seed_urls.txt first")
    p.add_argument("--skip-crawl", action="store_true", help="Only chunk + index")
    p.add_argument("--max-pages", type=int, default=10)
    p.add_argument("--delay", type=float, default=1.5)
    args = p.parse_args()

    py = sys.executable
    if not args.skip_crawl and (args.demo or args.url or args.urls_file):
        crawl_cmd = [py, str(ROOT / "src" / "crawl.py"), "--max-pages", str(args.max_pages), "--delay", str(args.delay)]
        if args.demo:
            crawl_cmd.append("--demo")
        for u in args.url:
            crawl_cmd.extend(["--url", u])
        if args.urls_file:
            crawl_cmd.extend(["--urls-file", args.urls_file])
        run(crawl_cmd)
    elif not args.skip_crawl:
        print("No crawl flags; skipping crawl (use --demo / --url / --urls-file).")

    run([py, str(ROOT / "src" / "chunk.py")])
    run([py, str(ROOT / "src" / "build_index.py")])
    print("Pipeline finished. Try: python src/ask.py \"你的问题\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
