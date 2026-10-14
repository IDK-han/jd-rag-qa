"""Gradio local demo: question → top-k hits + optional LLM answer."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gradio as gr

from retrieve import build_context, build_prompt, call_llm, ensure_index, retrieve


def answer(question: str, top_k: int = 4):
    question = (question or "").strip()
    if not question:
        return "请输入问题。", ""
    ensure_index()
    hits = retrieve(question, top_k=int(top_k))
    lines = []
    for i, h in enumerate(hits, 1):
        lines.append(
            f"### [{i}] {h['source']}  (score={h['score']:.3f})\n\n{h['text']}"
        )
    hits_md = "\n\n---\n\n".join(lines) if lines else "无命中"
    prompt = build_prompt(question, hits)
    llm = call_llm(prompt)
    if llm is None:
        answer_md = (
            "**未配置 API Key**（设置 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY` 可生成回答）\n\n"
            "#### 检索上下文\n\n"
            + build_context(hits)
        )
    else:
        answer_md = llm
    return hits_md, answer_md


def main() -> None:
    ensure_index()
    demo = gr.Interface(
        fn=answer,
        inputs=[
            gr.Textbox(
                label="问题",
                placeholder="例如：云体实习生需要什么技能？",
                lines=2,
            ),
            gr.Slider(1, 8, value=4, step=1, label="Top-K"),
        ],
        outputs=[
            gr.Markdown(label="检索结果"),
            gr.Markdown(label="回答 / 上下文"),
        ],
        title="JD RAG 问答 Demo",
        description="多语言句向量 + FAISS 检索实习 JD；配置 DeepSeek/OpenAI Key 可生成回答。",
        examples=[
            ["云体实习生需要什么技能？", 4],
            ["有哪些全远程的 AI Agent 实习？", 4],
            ["拓端数据分析师要会什么？", 4],
            ["Venturseed internship requirements", 4],
        ],
    )
    demo.launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    main()
