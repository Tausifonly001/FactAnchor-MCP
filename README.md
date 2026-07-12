# 🔗 FactAnchor-MCP

> **Reduce AI Hallucinations by up to ~80% (informal estimate) using Local Context Anchoring.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org)
[![Zero Cost](https://img.shields.io/badge/cost-%E2%82%B90-2ea44f.svg)](https://modelcontextprotocol.io)
[![MCP](https://img.shields.io/badge/MCP-ready-orange.svg)](https://modelcontextprotocol.io)

**FactAnchor-MCP** is a **zero-cost, fully local** [Model Context Protocol](https://modelcontextprotocol.io) server that grounds your AI assistant (Claude Desktop, Cursor, VS Code, Claude Code) in real, fetched web text — and forces it to answer **only** from that text.

- 💸 **₹0 Hosting Cost** — runs entirely on your machine. No cloud, no paid API keys.
- 🛡️ **Strict Guardrails** — the LLM must cite sources or say *"I cannot find a verified source for this information."*
- 🔎 **Hybrid Search** — Tavily → Serper → DuckDuckGo fallback (free by default, optionally faster with API keys).
- 🧠 **Smart Chunking** — BM25 semantic relevance scoring keeps only the most useful paragraphs.
- 💾 **Persistent Cache** — SQLite disk cache (`~/.factanchor/cache.db`) survives server restarts.
- ⚡ **Zero-config setup** — `pip install -e .` + connect your MCP client. Browser auto-installs on first start.

> ⭐ **If FactAnchor-MCP helps you ship more reliable, hallucination-free AI, please consider [starring the repository](https://github.com/Tausifonly001/FactAnchor-MCP).** It takes one click and helps more developers discover a truly zero-cost way to ground their agents. Thank you! 🙏

---

## 🔑 Optional API Keys (for faster search)

FactAnchor-MCP works out-of-the-box with **free DuckDuckGo search**. For faster, more reliable results, you can optionally provide commercial search API keys:

| Env Variable | Provider | Free Tier | Setup |
|-------------|----------|-----------|-------|
| `TAVILY_API_KEY` | [Tavily](https://tavily.com) | 1000 searches/month | Sign up → copy API key |
| `SERPER_API_KEY` | [Serper](https://serper.dev) | 2500 searches/month | Sign up → copy API key |
| *(none needed)* | DuckDuckGo | Unlimited | Works by default |

**Priority order:** Tavily → Serper → DuckDuckGo. If no keys are set, DuckDuckGo is used automatically.

Set keys in your environment:
```bash
# Windows (PowerShell)
$env:TAVILY_API_KEY = "tvly-..."

# macOS / Linux
export TAVILY_API_KEY="tvly-..."
```

Or add them to your MCP client config:
```json
{
  "mcpServers": {
    "FactAnchor-MCP": {
      "command": "factanchor-mcp",
      "env": {
        "TAVILY_API_KEY": "tvly-..."
      }
    }
  }
}
```

---

## 🚀 1-Minute Quick Start

### Option A — Recommended (cross-platform, no path editing)

```bash
git clone https://github.com/Tausifonly001/FactAnchor-MCP.git
cd FactAnchor-MCP
pip install -e .          # installs the `factanchor-mcp` command
```

Then add this to your `claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "FactAnchor-MCP": {
      "command": "factanchor-mcp"
    }
  }
}
```

### Option B — Simple (use the script path directly)

```bash
git clone https://github.com/Tausifonly001/FactAnchor-MCP.git
cd FactAnchor-MCP
pip install -r requirements.txt
```

Add the **absolute path** to `server.py`:

```json
{
  "mcpServers": {
    "FactAnchor-MCP": {
      "command": "python",
      "args": ["/absolute/path/to/FactAnchor-MCP/server.py"]
    }
  }
}
```

<details>
<summary>📂 Per-OS path examples</summary>

- **Windows:** `"C:\\Users\\you\\FactAnchor-MCP\\server.py"`
- **macOS / Linux:** `"/Users/you/FactAnchor-MCP/server.py"` or `"/home/you/FactAnchor-MCP/server.py"`

</details>

### 3. Restart your client
You'll now see the **`fetch_verified_context`** tool available. Ask a factual question and watch the assistant ground its answer in live, cited sources.

> ✅ **Zero-config:** on first launch, FactAnchor silently installs the Playwright Chromium browser in the background. No `crawl4ai-setup` or manual browser commands required.
>
> 💡 Want `uv` instead of pip? `uv pip install -e .` works identically, and the `factanchor-mcp` command lands on your PATH.

---

## 🧩 Supported Clients (drop-in configs)

FactAnchor-MCP is a **standard MCP server**, so it works with **any MCP-compatible client**. Below are ready-to-paste configs. Every client uses the same two shapes:

- **Option A (recommended):** `"command": "factanchor-mcp"` — needs `pip install -e .` (so the command is on your PATH).
- **Option B (path-based):** `"command": "python"` + `"args": ["/abs/path/server.py"]` — use this if the `factanchor-mcp` command isn't found.

<details open>
<summary>💬 Claude Desktop</summary>

File: `claude_desktop_config.json` (Settings → Developer → Edit Config)

```json
{
  "mcpServers": {
    "FactAnchor-MCP": { "command": "factanchor-mcp" }
  }
}
```
Restart Claude Desktop. Tool appears in the tools list.

</details>

<details open>
<summary>🖥️ opencode</summary>

File: `.opencode.jsonc` (project root)

```jsonc
{
  "mcpServers": {
    "FactAnchor-MCP": { "command": "factanchor-mcp" }
  }
}
```
Verify with `/mcp` — `fetch_verified_context` should be listed.

</details>

<details open>
<summary>⌨️ Claude Code / Kimi Code / Qwen Code / Cline / Roo Code</summary>

These are Claude-Code-style clients. Use a project `.mcp.json`:

```json
{
  "mcpServers": {
    "FactAnchor-MCP": { "command": "factanchor-mcp" }
  }
}
```

Or add it from the CLI (runs the same server):

```bash
claude mcp add factanchor -- factanchor-mcp
# Kimi/Qwen/Cline equivalents use the same `mcp add` subcommand
```

</details>

<details open>
<summary>🌀 Cursor</summary>

File: `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project)

```json
{
  "mcpServers": {
    "FactAnchor-MCP": { "command": "factanchor-mcp" }
  }
}
```
Enable it in **Settings → MCP** and restart Cursor.

</details>

<details open>
<summary>📝 VS Code (Copilot / MCP extension)</summary>

File: `.vscode/mcp.json` (note: VS Code uses a `"servers"` key)

```json
{
  "servers": {
    "FactAnchor-MCP": {
      "type": "stdio",
      "command": "factanchor-mcp"
    }
  }
}
```
Open the Command Palette → **MCP: List Servers** to confirm it's connected.

</details>

<details open>
<summary>🌟 Gemini CLI / Antigravity (Google)</summary>

File: `.gemini/settings.json`

```json
{
  "mcpServers": {
    "FactAnchor-MCP": { "command": "factanchor-mcp" }
  }
}
```
Or: `gemini mcp add factanchor -- factanchor-mcp`

</details>

<details open>
<summary>🔧 Generic MCP client (path-based fallback)</summary>

If the `factanchor-mcp` command isn't on your PATH, use the absolute path to `server.py` on every client above:

```json
{
  "mcpServers": {
    "FactAnchor-MCP": {
      "command": "python",
      "args": ["/absolute/path/to/FactAnchor-MCP/server.py"]
    }
  }
}
```

Per-OS path examples:
- **Windows:** `"C:\\Users\\you\\FactAnchor-MCP\\server.py"`
- **macOS:** `"/Users/you/FactAnchor-MCP/server.py"`
- **Linux:** `"/home/you/FactAnchor-MCP/server.py"`

</details>

---

## 🛠️ How It Works

```
[Claude Desktop / Cursor / VS Code]
       │ (Asks a factual query)
       ▼
[FactAnchor MCP Server]
       │
       ├──► [Hybrid Search: Tavily → Serper → DuckDuckGo] (URL Discovery)
       │
       ├──► [Persistent Cache: ~/.factanchor/cache.db] (Fast Repeat Queries)
       │
       ├──► [Crawl4AI in Isolated Subprocess] (Page Scraping)
       │
       ├──► [BM25 Semantic Chunking] (Smart Paragraph Selection)
       │
       └──► [Strict Guardrail Injection] (Verified Context Block)
              │
              ▼
[Assistant answers ONLY from verified context → ~0% Hallucination]
```

1. **Hybrid Search** — `fetch_verified_context(query)` tries Tavily (if `TAVILY_API_KEY` set), then Serper (if `SERPER_API_KEY` set), then falls back to free DuckDuckGo search to discover URLs.
2. **Persistent Caching** — results are cached in `~/.factanchor/cache.db` (SQLite) for 24 hours, so repeat queries return instantly even after server restarts.
3. **Page Scraping** — **Crawl4AI** runs in an isolated subprocess (`crawl_worker.py`) to scrape discovered URLs into clean, LLM-optimized Markdown (navbars, ads, and footers auto-stripped).
4. **Semantic Chunking** — BM25 relevance scoring extracts only the paragraphs most relevant to your query, maximizing information density within the context window.
5. **Guardrail Injection** — the fetched text is wrapped in a strict directive (see `guardrail.py`):
   - Answer **only** from `<verified_context>`.
   - If unanswerable, reply exactly: *"I cannot find a verified source for this information."*
   - Cite every claim in brackets like `[Source: ...]`.
   - Never fall back to pre-trained knowledge.
6. **Local-Only** — the server uses the `stdio` transport, so all processing stays on your machine.

---

## 📦 Project Structure

| File | Purpose |
|------|---------|
| `server.py` | The MCP server + `fetch_verified_context` tool (FastMCP). |
| `crawl_worker.py` | Headless-scrape worker (Crawl4AI) run in an isolated subprocess for robust MCP stdio. |
| `search_backends.py` | Hybrid search: Tavily → Serper → DuckDuckGo fallback. |
| `disk_cache.py` | Persistent SQLite cache (`~/.factanchor/cache.db`) for repeat queries. |
| `semantic_chunker.py` | BM25 relevance scoring to extract the most useful paragraphs. |
| `guardrail.py` | The strict fact-anchoring prompt template. |
| `text_cleaner.py` | Markdown cleaning + truncation for Crawl4AI output. |
| `pyproject.toml` | Packaging + `factanchor-mcp` console command. |
| `requirements.txt` | Dependencies (`mcp`, `ddgs`/`duckduckgo_search`, `crawl4ai`). |
| `claude_desktop_config.example.json` | Copy-paste config snippet. |

---

## 🧰 Requirements

- Python **3.10+**
- Internet access (for the free search/scrape)

## 🔧 Tool Reference

```
fetch_verified_context(query: str, max_results: int = 3) -> str
```

| Param | Default | Notes |
|-------|---------|-------|
| `query` | — | The factual topic or question to ground. |
| `max_results` | `3` | Sources to pull (clamped 1–5). |

---

## 🐛 Troubleshooting

- **`command not found: factanchor-mcp`** → you used Option A but didn't `pip install -e .`, or your venv isn't on PATH. Use Option B (script path) instead.
- **Pages return only short snippets (first run)** → Chromium is still installing in the background. Wait ~1–2 minutes and retry; subsequent runs are instant.
- **"Browser executable doesn't exist" on Linux** → install OS deps once: `sudo playwright install-deps chromium` (or `sudo apt install libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 libasound2`).
- **Rate-limit system note from the tool** → DuckDuckGo is throttling free search. Wait a few minutes and retry. The server never crashes; it returns a clean system note for the LLM.
- **Tool not appearing in client** → restart the client fully after editing the config, and check its MCP/Developer panel for errors.

---

## 📈 Virality Strategy

- **Before vs After video** (X/Twitter & LinkedIn): show the assistant hallucinating a fake npm feature, then enable FactAnchor-MCP and watch it correctly say *"I cannot find a verified source for this information."* Tag `@AnthropicAI` with `#MCP` and `#AI`.
- **Open-source launch**: submit to the [official MCP servers list](https://github.com/modelcontextprotocol/servers) and `awesome-mcp` collections.

---

## 📊 Evaluation

The "~80%" figure is an **informal estimate**. A small, hand-runnable eval
set lives in [`eval/sample_queries.json`](eval/sample_queries.json) — see
[`eval/README.md`](eval/README.md) for how to reproduce it. Contributions of
more queries (or a CI assertion) are very welcome.

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Keep it **zero-cost** and **local-first**.

## 📋 Success Metrics (v1.0)

> ⚠️ **Honesty note:** The "~80% reduction" is an **informal estimate** from manual testing against a small set of factual queries (see [`eval/sample_queries.json`](eval/sample_queries.json)) — it is **not** a benchmarked or statistically validated result. The guardrail is a *prompt directive*, not a hard infrastructure constraint, so an LLM can occasionally drift from it in long conversations. FactAnchor reduces hallucination but does not eliminate it; always verify critical claims against the cited sources.

- 🧪 **Up to ~80%** fewer made-up facts observed in informal test queries.
- ✅ **<3 min** user setup time (clone → install → config).
- ✅ **₹0.00** server maintenance bill.

## 📜 License

[MIT](LICENSE) © FactAnchor-MCP contributors.
