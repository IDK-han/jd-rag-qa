# JD 知识库问答（RAG Demo）

把多份实习 JD 切段 → 多语言句向量 + FAISS 检索 →（可选）DeepSeek / OpenAI 生成回答。  
含 **岗位页爬虫**、**Hit@k / MRR 评测** 与 **Gradio 本地 Demo**，适合写进简历的最小可运行 RAG。

作者：[韩承烨](https://github.com/IDK-han) · 仓库：[IDK-han/jd-rag-qa](https://github.com/IDK-han/jd-rag-qa)

## 流水线

```mermaid
flowchart LR
  C0[crawl.py 可选] --> A[data/jds/*.txt]
  A --> B[chunk.py]
  B --> C[chunks.jsonl]
  C --> D[build_index.py]
  D --> E[FAISS IndexFlatIP]
  E --> F[retrieve.py]
  F --> G[ask.py / eval.py / app.py]
  G --> H[可选 LLM 回答]
```

ASCII：

```
(可选 crawl) → JD txt → chunk → embeddings (MiniLM multilingual) → FAISS IP
                                         ↓
                             retrieve(top-k) → eval / Gradio / ask(+LLM)
```

## 功能

| 模块 | 作用 |
|------|------|
| `src/crawl.py` | 从**公开**岗位页抓取正文，写入 `data/jds/*.txt` |
| `src/chunk.py` | 按字符窗口切段，写出 `data/chunks.jsonl` |
| `src/build_index.py` | `paraphrase-multilingual-MiniLM-L12-v2` + FAISS `IndexFlatIP` |
| `src/retrieve.py` | 共享检索（懒加载模型，ask/eval/app 共用） |
| `src/ask.py` | CLI 问答；有 Key 则调 LLM，否则打印 Prompt |
| `src/eval.py` | Hit@1 / Hit@3 / MRR，写出 `data/eval_report.json` |
| `src/app.py` | Gradio 本地 UI |
| `src/pipeline.py` | 一键：crawl（可选）→ chunk → build_index |

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python src/chunk.py
python src/build_index.py
python src/ask.py "云体实习生需要什么技能？"
```

Windows PowerShell 可用 `py`：

```powershell
cd C:\Users\29346\jd-rag-qa
py src\chunk.py
py src\build_index.py
py src\ask.py "云体实习生需要什么技能？"
```

首次会下载句向量模型，需要一点网络与磁盘。

### 爬取公开岗位页（可选）

仓库已带若干样例 JD；也可用爬虫把**公开 HTML 岗位页**拉进 `data/jds/`：

```powershell
# 单页 / 多页（可重复 --url）
py src\crawl.py --url "https://jobs.lever.co/palantir/37964982-9b4c-471e-a1d8-fb8f45d7f116"

# 从 URL 列表文件
py src\crawl.py --urls-file data\seed_urls.txt

# Demo：读 data/seed_urls.txt；若网络失败则保留已有样例 JD 并提示
py src\crawl.py --demo

# 可选：限制页数与礼貌间隔（秒）
py src\crawl.py --demo --max-pages 5 --delay 2

# 一键：爬取 → 切分 → 建索引
py src\pipeline.py --demo
```

然后照常：

```powershell
py src\chunk.py
py src\build_index.py
py src\ask.py "Palantir intern 需要什么背景？"
```

**伦理与合规（请务必阅读）**

- 仅用于个人学习 / 简历 Demo；遵守目标站 **robots.txt** 与 **服务条款**。
- **不要**爬 LinkedIn、智联招聘、Boss直聘、拉勾等需登录或明确禁止爬虫的站点（脚本也会拒绝这些域名）。
- 优先：你自己提供的 URL、公司公开 careers 页、RSS/Atom、或 Lever 等可无登录打开的岗位页。
- 控制频率：默认请求间隔 `--delay 1.5`，并设 `--max-pages`；不要对同一站点高频轰炸。
- 只保存纯文本 `.txt`（含 source URL 与抓取时间），不存 Cookie / 账号信息。

### 接真实大模型（可选）

```bash
# Linux / macOS
export DEEPSEEK_API_KEY=sk-...
# Windows PowerShell
# $env:DEEPSEEK_API_KEY="sk-..."
# 或把 Key 写在本地 .env（勿提交 Git）

python src/ask.py "云体实习生需要什么技能？"
# 只要检索、不要 LLM：
python src/ask.py "云体实习生需要什么技能？" --no-llm
```

也可设 `OPENAI_API_KEY`（默认模型 `gpt-4o-mini`）。  
默认 DeepSeek：`https://api.deepseek.com` + `deepseek-chat`。  
参考 `.env.example`（请勿把真实 Key 提交进 Git）。

### 检索评测

```bash
python src/eval.py
```

示例指标（本仓库 5 份 JD、8 条中文/英文问题，本机跑通结果；详见 `data/eval_report.json`）：

| Metric | Score |
|--------|-------|
| Hit@1  | **0.88** |
| Hit@3  | **1.00** |
| MRR    | **0.92** |

短问「云体实习生需要什么技能？」时 Top-1 可能落到同类 Agent 岗（美因特），带公司名的问题 Hit@1=1；Hit@3 全中。

### Gradio Demo

```bash
python src/app.py
# 浏览器打开 http://127.0.0.1:7860
```

## 目录

- `data/jds/*.txt` — 原始岗位说明（样例 + 爬虫产出）
- `data/seed_urls.txt` — Demo / 批量爬取用的公开 URL 列表
- `data/eval_queries.json` — 评测问题与期望来源
- `data/eval_report.json` — 最近一次评测报告（可提交样例）
- `src/` — 爬取、切分、建索引、检索、问答、评测、UI、pipeline

## 简历可写点

- 基于 **多语言 Sentence-Transformers** 与 **FAISS 内积检索**，实现实习 JD 的切分 → 向量索引 → Top-K 检索闭环。
- 自建 **Hit@k / MRR** 评测集，用可量化指标验证检索质量，而非只做 Demo。
- 可选接入 **DeepSeek / OpenAI** 生成回答，并提供 **Gradio** 本地交互界面，便于面试现场演示。
- 增加 **礼貌爬虫**：User-Agent 标识、延时与页数上限、域名黑名单，将公开岗位页纳入同一 RAG 流水线。

## 说明

当前规模是「入门可演示」级别（少量 JD、Flat 索引），重点展示 RAG 工程链路与评测习惯；扩展真实语料、混合检索或 Agent 工具调用可在此基础上迭代。
