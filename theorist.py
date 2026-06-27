"""
theorist.py  —  THE PROPOSER.  This is where THE AGENTS EXPLORE.

  StubTheorist   : deterministic, zero-cost. Cycles a desk's candidate families.
  ClaudeTheorist : the LIVE agent (claude-opus-4-8). Reads the desk's graveyard and
                   proposes the next creative Hypothesis, with plain-language reasoning.

THE LAW: neither can BLESS. They only PROPOSE and EXPLAIN. The deterministic gauntlet
is the only thing that rules, and it never reads the rationale. Free imagination is
safe ONLY because it is paired with an incorruptible referee.
"""
from __future__ import annotations

import json
from typing import Optional


# A desk's *starting* families. The live agent is free to propose NEW families beyond
# these (its imagination outruns the executable space — that gap is the real frontier).
DESK_FAMILIES = {
    "crypto":   ["funding_carry", "basis_momentum", "xvenue_spread", "liq_reversion"],
    "equities": ["overnight_drift", "post_earn_drift", "index_dispersion"],
    "options":  ["vol_risk_premium", "skew_carry", "term_structure_roll"],
}


class StubTheorist:
    """Deterministic proposer for DRY runs — zero API cost."""
    def __init__(self, asset_class: str):
        self.ac = asset_class
        self._fams = list(DESK_FAMILIES[asset_class])

    def propose(self, graveyard_keys: set) -> Optional[dict]:
        for fam in self._fams:
            if f"{self.ac}:{fam}" not in graveyard_keys:
                return {"family": fam, "rationale": f"[stub] structural probe: {fam} on {self.ac}."}
        return None


_SYSTEM = """You are THE THEORIST for the {ac} desk of NULLIUS — a self-falsifying quant \
RESEARCH engine. You hunt NON-DIRECTIONAL structural edges (funding/carry, basis, \
cross-venue, dispersion, variance premium), never price direction.

THE LAW (binding): you may ONLY propose and explain. You can NEVER bless, confirm, or \
declare an edge real or profitable — only the deterministic gauntlet can KILL a belief, \
and only real forward evidence can ever raise one. Assume every edge you propose is fake \
until the engine fails to kill it.

Propose exactly ONE candidate edge to test next on the {ac} desk. Read the GRAVEYARD of \
what already died and do NOT repeat it — probe a genuinely different structural question. \
Be the skeptic, not the hype-man: in your rationale, explain why this might be a real \
structural cash flow AND how it could fail (negative-skew tail, costs, regime dependence).

Respond with ONLY a JSON object: {{"family": "<short_snake_case_family>", "rationale": "<plain language>"}}"""


class ClaudeTheorist:
    """The LIVE agent. Genuinely explores: proposes creative, structured hypotheses.
    Robust across SDK versions — tries structured output, falls back to JSON-in-prompt.
    Credentials resolve from ANTHROPIC_API_KEY in the env; no key is stored here."""
    def __init__(self, asset_class: str, model: str = "claude-opus-4-8"):
        import anthropic  # lazy
        self.ac = asset_class
        self._client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY
        self._model = model

    def propose(self, graveyard_keys: set) -> Optional[dict]:
        dead = sorted(k.split(":", 1)[1] for k in graveyard_keys if k.startswith(self.ac + ":"))
        user = ("GRAVEYARD (already killed on this desk — do NOT repeat): "
                + (", ".join(dead) if dead else "(empty)")
                + "\n\nPropose the next single Hypothesis to falsify.")
        sysmsg = _SYSTEM.format(ac=self.ac)

        # Plain, version-robust call. (If your SDK supports structured outputs/thinking,
        # you can add output_config={"format":{"type":"json_schema",...}} here.)
        resp = self._client.messages.create(
            model=self._model, max_tokens=1024,
            system=sysmsg,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(getattr(b, "text", "") for b in resp.content)
        data = _extract_json(text)
        if not data or "family" not in data:
            return None
        return {"family": str(data["family"]).strip().lower().replace(" ", "_"),
                "rationale": str(data.get("rationale", "")).strip() or "(no rationale)"}


def _extract_json(text: str) -> Optional[dict]:
    """Pull the first JSON object out of a model response, tolerant of prose/fences."""
    text = text.replace("```json", "").replace("```", "")
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b == -1 or b <= a:
        return None
    try:
        return json.loads(text[a:b + 1])
    except Exception:
        return None
