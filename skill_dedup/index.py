"""On-disk store of approved skills: metadata (JSON) + one vector per skill (NumPy).

Only approved ("good") skills live here. Phase 1 reads the hashes and names,
phase 2 reads the vectors. Nothing is ever re-embedded unless its content hash changes.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .skill import Skill


class SkillIndex:
    def __init__(self, root: Path, embedder_name: str, dim: int):
        self.root = Path(root)
        self.embedder_name = embedder_name
        self.dim = dim
        self.meta: list[dict] = []
        self.vecs = np.zeros((0, dim), dtype=np.float32)

    # ---- persistence -------------------------------------------------
    @classmethod
    def load(cls, root: Path, embedder_name: str, dim: int) -> "SkillIndex":
        idx = cls(root, embedder_name, dim)
        meta_file, vec_file = idx.root / "skills.json", idx.root / "vectors.npy"
        if not meta_file.exists():
            return idx
        data = json.loads(meta_file.read_text())
        if data["embedder"] != embedder_name:
            raise ValueError(
                f"index at {root} was built with embedder {data['embedder']!r}, "
                f"not {embedder_name!r}; rebuild it or pass the same --embedder"
            )
        idx.meta = data["skills"]
        idx.vecs = np.load(vec_file).astype(np.float32)
        assert len(idx.meta) == len(idx.vecs), "index metadata and vectors out of sync"
        return idx

    def save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        np.save(self.root / "vectors.npy", self.vecs)
        payload = {"embedder": self.embedder_name, "dim": self.dim, "skills": self.meta}
        (self.root / "skills.json").write_text(json.dumps(payload, indent=2))

    # ---- lookups used by phase 1 --------------------------------------
    def by_sha(self) -> dict[str, dict]:
        return {m["sha"]: m for m in self.meta}

    def by_id(self) -> dict[str, dict]:
        return {m["id"]: m for m in self.meta}

    def by_norm_name(self) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for m in self.meta:
            out.setdefault(m["norm_name"], []).append(m)
        return out

    # ---- phase 2 search -----------------------------------------------
    def nearest(self, vec: np.ndarray, k: int, exclude_id: str | None = None):
        """Top-k (meta, cosine) pairs. Vectors are unit-normalized, so dot == cosine."""
        if not len(self.vecs):
            return []
        sims = self.vecs @ vec
        order = np.argsort(-sims)
        out = []
        for i in order:
            if self.meta[i]["id"] == exclude_id:
                continue  # an updated skill must not match its own old version
            out.append((self.meta[i], float(sims[i])))
            if len(out) == k:
                break
        return out

    # ---- mutation -----------------------------------------------------
    def upsert(self, skill: Skill, vec: np.ndarray) -> None:
        record = {k: v for k, v in asdict(skill).items() if k != "body"}
        record["norm_name"] = skill.norm_name
        record["body_excerpt"] = skill.body[:4000]
        for i, m in enumerate(self.meta):
            if m["id"] == skill.id:
                self.meta[i], self.vecs[i] = record, vec
                return
        self.meta.append(record)
        self.vecs = np.vstack([self.vecs, vec[None, :].astype(np.float32)])
