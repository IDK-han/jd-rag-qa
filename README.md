# JD 知识库问答（RAG Demo）

把多份实习 JD 切段、向量检索，再拼成可交给大模型的上下文。适合写进简历的最小可运行 RAG。

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python src/chunk.py
python src/build_index.py
python src/ask.py "云体实习生需要什么技能？"
```

首次运行会下载多语言句向量模型，需要一点网络时间。

## 目录

- `data/jds/*.txt`：原始岗位说明
- `src/chunk.py`：切段
- `src/build_index.py`：建 FAISS 索引
- `src/ask.py`：检索并输出 Prompt 上下文

## 说明

当前版本完成 **检索增强** 闭环；生成答案可把 `ask.py` 打印的提示词粘到任意大模型对话框，或自行接 API。
