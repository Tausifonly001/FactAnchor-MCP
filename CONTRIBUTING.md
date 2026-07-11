# Contributing to FactAnchor-MCP

Thanks for wanting to make AI less hallucinatory! 🛡️

## Ways to help
- 🐛 Report bugs or rate-limit issues ([Issues](../../issues))
- 💡 Suggest features or new zero-cost sources
- 🔧 Submit pull requests

## Dev setup
```bash
git clone https://github.com/your-username/FactAnchor-MCP.git
cd FactAnchor-MCP
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Guidelines
1. Keep it **zero-cost** — no paid API keys required.
2. Stay **local-first** — no cloud calls except free public search.
3. Run `python -c "import server"` and a quick tool test before opening a PR.
4. Update the README if behavior changes.

## Code style
- Plain, readable Python (PEP 8).
- No comments unless non-obvious (per project convention).
- Prefer graceful degradation over crashing on network errors.
