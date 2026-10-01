"""Phase 3: ask Claude whether a skill duplicates its nearest candidates.

Called only for skills phase 2 could not decide, with at most k candidates each,
so a whole repo typically costs a handful of requests.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from .skill import Skill

DEFAULT_MODEL = "claude-opus-5-5"
BODY_CHARS = 4000

SYSTEM = """You review skills submitted to a plugin marketplace. A skill is a SKILL.md \
file: its `description` decides when an agent loads it, and its body tells the agent \
what to do.

Compare the NEW skill with each CANDIDATE and classify the pair:
- "duplicate": they serve the same purpose for the same trigger; an agent would not \
need both, and installing both would make them compete for the same requests.
- "overlapping": a real shared core, but each covers something the other does not.
- "distinct": different jobs, even if they share a domain or vocabulary.

Judge by what the skill does and when it triggers, not by wording. Bodies may be \
excerpts of longer files."""

SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "string"},
                    "relation": {"type": "string", "enum": ["duplicate", "overlapping", "distinct"]},
                    "reason": {"type": "string"},
                },
                "required": ["candidate_id", "relation", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}


@dataclass
class Verdict:
    candidate_id: str
    relation: str  # duplicate | overlapping | distinct
    reason: str


class Judge(Protocol):
    def judge(self, skill: Skill, candidates: list[dict]) -> list[Verdict]: ...


def _render(label: str, ident: str, name: str, desc: str, body: str) -> str:
    return (
        f"<{label} id={json.dumps(ident)}>\n"
        f"name: {name}\ndescription: {desc}\n\n{body[:BODY_CHARS]}\n</{label}>"
    )


def build_prompt(skill: Skill, candidates: list[dict]) -> str:
    parts = [_render("new_skill", skill.id, skill.name, skill.description, skill.body)]
    for c in candidates:
        parts.append(_render("candidate", c["id"], c["name"], c["description"], c.get("body_excerpt", "")))
    parts.append("Return one verdict per candidate, using the candidate's id.")
    return "\n\n".join(parts)


class ClaudeJudge:
    def __init__(self, model: str = DEFAULT_MODEL, client=None):
        import anthropic

        self.model = model
        self.client = client or anthropic.Anthropic()

    def judge(self, skill: Skill, candidates: list[dict]) -> list[Verdict]:
        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=4000,
            system=SYSTEM,
            messages=[{"role": "user", "content": build_prompt(skill, candidates)}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            # Re-run on Anthropic's recommended fallback model if a safety classifier declines.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            raise RuntimeError(f"judge declined to compare {skill.id}")
        if response.stop_reason == "max_tokens":
            raise RuntimeError(f"judge output truncated for {skill.id}")
        text = next(b.text for b in response.content if b.type == "text")
        known = {c["id"] for c in candidates}
        return [
            Verdict(v["candidate_id"], v["relation"], v["reason"])
            for v in json.loads(text)["verdicts"]
            if v["candidate_id"] in known
        ]
