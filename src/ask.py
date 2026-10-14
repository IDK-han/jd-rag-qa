"""对 JD 知识库提问：检索相关段落；若配置了 API Key 则调用大模型生成回答。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python src/ask.py` without installing as package
sys.path.insert(0, str(Path(__file__).resolve().parent))

from retrieve import build_prompt, call_llm, ensure_index, retrieve


def main() -> None:
    parser = argparse.ArgumentParser(description="JD RAG 问答")
    parser.add_argument("question", help="你的问题，例如：云体实习要什么技能？")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="只检索并打印 Prompt，不调用大模型",
    )
    args = parser.parse_args()

    ensure_index()
    hits = retrieve(args.question, top_k=args.top_k)
    print("=== 检索结果 ===")
    for h in hits:
        preview = h["text"][:120].replace("\n", " ")
        print(f"[{h['score']:.3f}] {h['source']} :: {preview}...")

    prompt = build_prompt(args.question, hits)

    if args.no_llm:
        print("\n=== 可粘贴给大模型的上下文 / 提示词 ===\n")
        print(prompt)
        return

    answer = call_llm(prompt)
    if answer is None:
        print("\n=== 可粘贴给大模型的上下文 / 提示词 ===\n")
        print(prompt)
        print(
            "\n提示: 设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 后可自动生成回答"
            "（也可加 --no-llm 只看检索）。"
        )
    else:
        print("\n=== 大模型回答 ===\n")
        print(answer)


if __name__ == "__main__":
    main()
