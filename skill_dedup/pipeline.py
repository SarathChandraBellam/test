"""Runs the three phases over a batch of incoming skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from .embedders import Embedder, embed_skills
from .index import SkillIndex
from .judge import Judge
from .skill import Skill


class Status(str, Enum):
    UNCHANGED = "unchanged"              # phase 1: same id, same hash as the indexed version
    EXACT_DUPLICATE = "exact_duplicate"  # phase 1: identical content under another id
    DUPLICATE = "duplicate"              # phase 2 (high similarity) or phase 3 (LLM verdict)
    NEEDS_REVIEW = "needs_review"        # ambiguous and no judge, or judge said "overlapping"
    UNIQUE = "unique"


@dataclass
class Thresholds:
    high: float = 0.92  # cosine at/above which phase 2 calls it a duplicate on its own
    low: float = 0.80   # cosine below which a candidate is ignored
    k: int = 5          # neighbours fetched per skill


@dataclass
class Match:
    id: str
    path: str
    score: float | None = None     # cosine similarity (phase 2)
    relation: str | None = None    # LLM verdict (phase 3)
    reason: str = ""


@dataclass
class Result:
    skill: Skill
    status: Status
    phase: int
    matches: list[Match] = field(default_factory=list)
    note: str = ""
    vector: np.ndarray | None = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            "id": self.skill.id,
            "path": self.skill.path,
            "status": self.status.value,
            "phase": self.phase,
            "note": self.note,
            "matches": [m.__dict__ for m in self.matches],
        }


def seed(index: SkillIndex, embedder: Embedder, skills: list[Skill]) -> int:
    """Add trusted skills to the index without checks. Skips ones already indexed unchanged."""
    current = index.by_id()
    todo = [s for s in skills if current.get(s.id, {}).get("sha") != s.sha]
    for s, v in zip(todo, embed_skills(embedder, todo)):
        index.upsert(s, v)
    return len(todo)


def check(
    skills: list[Skill],
    index: SkillIndex,
    embedder: Embedder,
    judge: Judge | None = None,
    th: Thresholds = Thresholds(),
) -> list[Result]:
    """Classify incoming skills. Skills found UNIQUE are upserted into `index` in memory
    (so later skills in the same batch are compared against them); call index.save()
    to persist."""
    results: dict[str, Result] = {}
    order = [s.id for s in skills]

    # ---- Phase 1: hash + name lookups, no model involved ---------------
    by_sha, by_id = index.by_sha(), index.by_id()
    batch_sha: dict[str, Skill] = {}
    pending: list[Skill] = []
    for s in skills:
        prev = by_id.get(s.id)
        if prev and prev["sha"] == s.sha:
            results[s.id] = Result(s, Status.UNCHANGED, 1)
        elif (hit := by_sha.get(s.sha)) and hit["id"] != s.id:
            results[s.id] = Result(s, Status.EXACT_DUPLICATE, 1, [Match(hit["id"], hit["path"], 1.0)])
        elif dup := batch_sha.get(s.sha):
            results[s.id] = Result(s, Status.EXACT_DUPLICATE, 1, [Match(dup.id, dup.path, 1.0)],
                                   note="identical to another skill in this batch")
        else:
            batch_sha[s.sha] = s
            pending.append(s)

    # ---- Phase 2: embed only new/updated skills, one batched call -------
    vectors = embed_skills(embedder, pending)
    ambiguous: list[tuple[Skill, np.ndarray, list[dict], dict[str, float]]] = []
    for s, v in zip(pending, vectors):
        near = index.nearest(v, th.k, exclude_id=s.id)
        if near and near[0][1] >= th.high:
            matches = [Match(m["id"], m["path"], round(sim, 4)) for m, sim in near if sim >= th.high]
            results[s.id] = Result(s, Status.DUPLICATE, 2, matches, vector=v)
            continue

        scores = {m["id"]: sim for m, sim in near}
        cands = [m for m, sim in near if sim >= th.low]
        # Same normalized name in another source is always worth a look.
        for m in index.by_norm_name().get(s.norm_name, []):
            if m["id"] != s.id and m["id"] not in {c["id"] for c in cands}:
                cands.append(m)
        if not cands:
            results[s.id] = Result(s, Status.UNIQUE, 2, vector=v)
            index.upsert(s, v)
        else:
            ambiguous.append((s, v, cands, scores))

    # ---- Phase 3: LLM only for the ambiguous ones ------------------------
    for s, v, cands, scores in ambiguous:
        if judge is None:
            matches = [Match(c["id"], c["path"], _score(scores, c)) for c in cands]
            results[s.id] = Result(s, Status.NEEDS_REVIEW, 2, matches,
                                   note="similar candidates found; LLM judge disabled", vector=v)
            continue
        verdicts = {vd.candidate_id: vd for vd in judge.judge(s, cands)}
        matches = []
        for c in cands:
            vd = verdicts.get(c["id"])
            if vd and vd.relation != "distinct":
                matches.append(Match(c["id"], c["path"], _score(scores, c), vd.relation, vd.reason))
        relations = {m.relation for m in matches}
        if "duplicate" in relations:
            status = Status.DUPLICATE
        elif "overlapping" in relations:
            status = Status.NEEDS_REVIEW
        else:
            status = Status.UNIQUE
            index.upsert(s, v)
        results[s.id] = Result(s, status, 3, matches, vector=v)

    return [results[i] for i in order]


def _score(scores: dict[str, float], cand: dict) -> float | None:
    sim = scores.get(cand["id"])
    return None if sim is None else round(sim, 4)


def add_to_index(results: list[Result], index: SkillIndex, accept_review: bool = False) -> int:
    """After check(): optionally also index skills a human cleared from NEEDS_REVIEW."""
    added = 0
    if accept_review:
        for r in results:
            if r.status is Status.NEEDS_REVIEW and r.vector is not None:
                index.upsert(r.skill, r.vector)
                added += 1
    return added
