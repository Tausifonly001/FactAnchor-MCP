# Evaluation Set

This is a **small, informal** eval used to sanity-check FactAnchor-MCP's
grounding behaviour. It is **not** a statistically rigorous benchmark — it
exists so the "up to ~80% fewer made-up facts" claim in the README is at
least reproducible by hand rather than pulled from thin air.

## How to use it

For each entry, run the `fetch_verified_context` tool (via your MCP client)
with the `query` and inspect the returned `<verified_context>`:

- `expect_grounded: true` → the verified context should contain the
  `expected_snippet` (proving the answer came from fetched text, not the
  model's memory).
- `expect_grounded: false` → the tool should *not* fabricate; it should fall
  back to the rate-limit/system note or "I cannot find a verified source".

## Caveats

- Results depend on DuckDuckGo availability and live web content, so a
  snippet may occasionally be phrased differently (e.g. "299,792,458 km/s").
  Treat the `expected_snippet` as a hint, not an exact match.
- The guardrail is a prompt directive, not a hard constraint — in very long
  conversations a model can still drift. This set only measures single-turn
  grounding quality.

To grow this into a real benchmark, add more queries and assert exact
substring matches in CI.
