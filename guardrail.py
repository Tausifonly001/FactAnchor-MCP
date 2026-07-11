GUARDRAIL_TEMPLATE = """[CRITICAL DIRECTIVE: FACT-ANCHORING ACTIVATED]
You must answer the user's query ONLY using the provided text below.

<verified_context>
{context}
</verified_context>

STRICT RULES:
1. If the answer cannot be directly derived from the <verified_context>, reply exactly with: "I cannot find a verified source for this information." Do not guess.
2. For every factual claim you make, append the specific phrase or source from the context in brackets, like [Source: Text snippet].
3. Do not use your internal pre-trained knowledge to supplement missing information.
Use code with caution."""


def build_guardrail(fetched_text: str) -> str:
    """Wrap fetched, verified text inside the strict guardrail directive."""
    return GUARDRAIL_TEMPLATE.format(context=fetched_text.strip())
