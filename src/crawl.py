"""Crawl public job / internship pages into data/jds/*.txt (UTF-8).

Polite, personal-use crawler: user-supplied URLs, seed file, or --demo.
Does NOT target LinkedIn / 智联 / Boss直聘 / 拉勾 or other login-walled boards.
Respect robots.txt / site ToS; keep --max-pages and --delay modest.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "jds"
DEFAULT_SEEDS = ROOT / "data" / "seed_urls.txt"

USER_AGENT = (
    "jd-rag-qa/1.0 (+https://github.com/IDK-han/jd-rag-qa; "
    "personal research crawler; contact via GitHub issues)"
)

# Hard deny: login-walled / ToS-hostile job boards (substring match on host).
BLOCKED_HOST_PARTS = (
    "linkedin.com",
    "zhilianshebao",  # keep short aliases below
    "zhaopin.com",
    "zhipin.com",
    "bosszhipin",
    "lagou.com",
    "liepin.com",
    "51job.com",
    "indeed.com",  # often ToS-restrictive / JS-heavy
)

BLOCKED_HINTS = ("linkedin", "智联", "boss直聘", "拉勾", "猎聘")


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_blocked(url: str) -> str | None:
    """Return a short reason if URL should not be fetched, else None."""
    host = _host(url)
    low = url.lower()
    for part in BLOCKED_HOST_PARTS:
        if part in host:
            return f"blocked host ({part})"
    for hint in BLOCKED_HINTS:
        if hint in low:
            return f"blocked site hint ({hint})"
    return None


def slug_from_url(url: str, max_len: int = 80) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "page").replace("www.", "")
    path = (parsed.path or "").strip("/")
    raw = f"{host}_{path}" if path else host
    raw = re.sub(r"[^\w\-]+", "_", raw, flags=re.UNICODE)
    raw = re.sub(r"_+", "_", raw).strip("_").lower()
    if not raw:
        raw = "job"
    return raw[:max_len]


def extract_main_text(html: str, url: str = "") -> str:
    """Strip chrome; prefer article/main/job containers; collapse whitespace."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "template"]):
        tag.decompose()
    for tag in soup.find_all(["nav", "footer", "header", "aside"]):
        # Keep header if it looks like the job title area on Lever
        classes = " ".join(tag.get("class") or []).lower()
        if tag.name == "header" and any(k in classes for k in ("posting", "job", "opening")):
            continue
        tag.decompose()

    candidates = []
    selectors = [
        ".posting-page",
        ".posting",
        "#content",
        ".job-post",
        ".job__description",
        "[data-testid='job-description']",
        "article",
        "main",
        "[role='main']",
        ".content",
    ]
    for sel in selectors:
        for el in soup.select(sel):
            text = el.get_text("\n", strip=True)
            if len(text) >= 200:
                candidates.append(text)

    if not candidates and soup.body:
        candidates.append(soup.body.get_text("\n", strip=True))

    if not candidates:
        return ""

    # Prefer the longest plausible block (usually the JD body).
    text = max(candidates, key=len)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text).strip()

    # Drop very short / error pages
    if len(text) < 120:
        return ""
    low = text.lower()
    if "couldn't find anything here" in low or "404 error" in low:
        return ""
    return text


def fetch_url(client: httpx.Client, url: str, timeout: float = 25.0) -> tuple[str, str]:
    """Return (final_url, html). Raises on HTTP errors."""
    reason = is_blocked(url)
    if reason:
        raise ValueError(f"refusing to fetch: {reason}: {url}")
    resp = client.get(url, timeout=timeout, follow_redirects=True)
    # Re-check after redirects
    final = str(resp.url)
    reason = is_blocked(final)
    if reason:
        raise ValueError(f"refusing redirected URL: {reason}: {final}")
    resp.raise_for_status()
    ctype = (resp.headers.get("content-type") or "").lower()
    if "html" not in ctype and "text/" not in ctype and "xml" not in ctype:
        raise ValueError(f"unsupported content-type {ctype!r} for {final}")
    return final, resp.text


def write_jd(
    out_dir: Path,
    url: str,
    text: str,
    fetched_at: datetime | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = slug_from_url(url)
    path = out_dir / f"{slug}.txt"
    # Avoid clobbering unrelated samples: if exists and different source, suffix.
    if path.exists():
        existing = path.read_text(encoding="utf-8", errors="ignore")
        if url not in existing.splitlines()[:5]:
            n = 2
            while True:
                alt = out_dir / f"{slug}_{n}.txt"
                if not alt.exists():
                    path = alt
                    break
                n += 1

    when = (fetched_at or datetime.now(timezone.utc)).astimezone().strftime(
        "%Y-%m-%d %H:%M:%S %Z"
    )
    body = (
        f"source: {url}\n"
        f"fetched_at: {when}\n"
        f"\n"
        f"{text.strip()}\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


def load_urls_file(path: Path) -> list[str]:
    if not path.is_file():
        return []
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def crawl_urls(
    urls: list[str],
    out_dir: Path,
    *,
    max_pages: int = 10,
    delay: float = 1.5,
) -> list[Path]:
    written: list[Path] = []
    if not urls:
        return written

    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    with httpx.Client(headers=headers, http2=False) as client:
        for i, url in enumerate(urls[: max(0, max_pages)]):
            url = url.strip()
            if not url:
                continue
            try:
                final, html = fetch_url(client, url)
                text = extract_main_text(html, final)
                if not text:
                    print(f"[skip] no usable text: {url}", file=sys.stderr)
                else:
                    path = write_jd(out_dir, final, text)
                    written.append(path)
                    print(f"[ok] {path.name} <- {final} ({len(text)} chars)")
            except Exception as exc:
                print(f"[fail] {url}: {exc}", file=sys.stderr)
            if i + 1 < min(len(urls), max_pages) and delay > 0:
                time.sleep(delay)
    return written


def demo_fallback_message(out_dir: Path) -> None:
    existing = sorted(out_dir.glob("*.txt")) if out_dir.is_dir() else []
    print(
        "\n[demo] Network crawl failed or returned nothing. "
        "Keeping / using existing sample JDs under data/jds/ "
        f"({len(existing)} file(s)). "
        "You can still run: py src/chunk.py && py src/build_index.py",
        file=sys.stderr,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Crawl public job/internship pages into data/jds/*.txt. "
            "Prefer user URLs or seed_urls.txt; avoid login-walled boards."
        )
    )
    p.add_argument(
        "--url",
        action="append",
        default=[],
        help="Job page URL (repeatable)",
    )
    p.add_argument(
        "--urls-file",
        type=Path,
        default=None,
        help=f"Text file with one URL per line (default for --demo: {DEFAULT_SEEDS})",
    )
    p.add_argument(
        "--demo",
        action="store_true",
        help="Fetch URLs from data/seed_urls.txt; on failure keep bundled sample JDs",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT,
        help="Output directory for .txt JDs (default: data/jds)",
    )
    p.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Max pages to fetch (default: 10)",
    )
    p.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Seconds to sleep between requests (default: 1.5)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    urls: list[str] = list(args.url or [])
    if args.urls_file is not None:
        path = args.urls_file if args.urls_file.is_absolute() else ROOT / args.urls_file
        urls.extend(load_urls_file(path))
    if args.demo:
        seeds = DEFAULT_SEEDS
        if args.urls_file is None:
            urls.extend(load_urls_file(seeds))
        if not urls:
            print(
                f"[demo] No URLs in {seeds}; using existing sample JDs only.",
                file=sys.stderr,
            )
            demo_fallback_message(out_dir)
            return 0

    # Deduplicate preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    urls = uniq

    if not urls:
        print(
            "No URLs given. Use --url, --urls-file, or --demo.",
            file=sys.stderr,
        )
        return 2

    written = crawl_urls(
        urls,
        out_dir,
        max_pages=args.max_pages,
        delay=args.delay,
    )

    if args.demo and not written:
        demo_fallback_message(out_dir)
        return 0

    print(f"Done. Wrote {len(written)} file(s) -> {out_dir}")
    return 0 if written or args.demo else 1


if __name__ == "__main__":
    raise SystemExit(main())
