"""python -m skill_dedup {seed,check,add} ...

  seed  <dir> [--source S]   index trusted skills as the approved baseline (no checks)
  check <dir> [--source S]   run phases 1-3 and report; never writes the index
  add   <dir> [--source S]   run phases 1-3, then save every UNIQUE skill to the index

Exit code for check/add: 0 when nothing was flagged, 1 when any skill is a duplicate
or needs review (so CI can block the PR).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .embedders import make_embedder
from .index import SkillIndex
from .judge import DEFAULT_MODEL, ClaudeJudge
from .pipeline import Status, Thresholds, add_to_index, check, seed
from .skill import discover

FLAGGED = {Status.EXACT_DUPLICATE, Status.DUPLICATE, Status.NEEDS_REVIEW}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="skill_dedup", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["seed", "check", "add"])
    p.add_argument("path", type=Path, help="directory to scan for SKILL.md files")
    p.add_argument("--source", help="name for this repo/marketplace (default: directory name)")
    p.add_argument("--index", type=Path, default=Path(".skill-index"), help="index directory")
    p.add_argument("--embedder", default="st", help="'st', 'st:<model>' or 'hashing' (default: st)")
    p.add_argument("--high", type=float, default=Thresholds.high)
    p.add_argument("--low", type=float, default=Thresholds.low)
    p.add_argument("-k", type=int, default=Thresholds.k)
    p.add_argument("--no-llm", action="store_true", help="skip phase 3; ambiguous -> needs_review")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"phase 3 model (default: {DEFAULT_MODEL})")
    p.add_argument("--accept-review", action="store_true", help="add: also index needs_review skills")
    p.add_argument("--json", action="store_true", help="print results as JSON")
    a = p.parse_args(argv)

    embedder = make_embedder(a.embedder)
    index = SkillIndex.load(a.index, embedder.name, embedder.dim)
    skills = discover(a.path, a.source)
    if not skills:
        print(f"no SKILL.md files under {a.path}", file=sys.stderr)
        return 0

    if a.command == "seed":
        n = seed(index, embedder, skills)
        index.save()
        print(f"indexed {n} new/updated skills ({len(skills) - n} unchanged); "
              f"index now holds {len(index.meta)}")
        return 0

    judge = None if a.no_llm else ClaudeJudge(a.model)
    results = check(skills, index, embedder, judge, Thresholds(a.high, a.low, a.k))

    if a.command == "add":
        add_to_index(results, index, a.accept_review)
        index.save()

    if a.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        _print_report(results)
    return 1 if any(r.status in FLAGGED for r in results) else 0


def _print_report(results) -> None:
    counts: dict[str, int] = {}
    for r in results:
        counts[r.status.value] = counts.get(r.status.value, 0) + 1
        if r.status in (Status.UNCHANGED, Status.UNIQUE):
            continue
        print(f"[{r.status.value}] {r.skill.id}  (phase {r.phase})  {r.skill.path}")
        for m in r.matches:
            score = f"cos={m.score:.3f}" if m.score is not None else ""
            rel = f"llm={m.relation}" if m.relation else ""
            print(f"    ~ {m.id}  {score} {rel}  {m.path}")
            if m.reason:
                print(f"      {m.reason}")
        if r.note:
            print(f"    note: {r.note}")
    print("summary: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
