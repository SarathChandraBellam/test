# skill_dedup

Finds duplicate skills (`SKILL.md`) across plugin marketplaces without comparing every
skill against every other one.

```
incoming repo ──► Phase 1: exact         sha256(normalized SKILL.md) + normalized name
                     │  unchanged / exact copy → done (free)
                     ▼
                  Phase 2: embeddings    embed ONLY new or updated skills (one batch),
                     │                   top-k against the index of approved skills
                     │  cos ≥ 0.92 → duplicate      cos < 0.80 → unique
                     ▼
                  Phase 3: LLM judge     only the 0.80–0.92 band (and same-name hits):
                                         one call per skill with ≤ k candidates
```

Approved ("good") skills live in `.skill-index/` as `skills.json` (hash, name,
description, excerpt) and `vectors.npy` (one unit vector per skill). A skill is
re-embedded only when its content hash changes, and an updated skill is never matched
against its own previous version.

## Install

```bash
pip install -r requirements.txt
```

## Use

```bash
# 1. Build the baseline from the marketplaces you already trust (no checks).
python -m skill_dedup seed path/to/official-marketplace --source official

# 2. Check a repo someone wants to add (read-only; exit 1 if anything is flagged).
python -m skill_dedup check path/to/new-repo --source acme-skills

# 3. Accept it: same checks, then unique skills are written to the index.
python -m skill_dedup add path/to/new-repo --source acme-skills
```

Options:

| Flag | Default | |
|---|---|---|
| `--embedder` | `st` | `st` = local `BAAI/bge-small-en-v1.5`, `st:<model>` for another sentence-transformers model, `hashing` = lexical, no download (tests/CI) |
| `--high` / `--low` | `0.92` / `0.80` | phase 2 bands; calibrate on known pairs from your own catalog |
| `-k` | `5` | neighbours fetched per skill |
| `--no-llm` | off | skip phase 3; ambiguous skills are reported as `needs_review` |
| `--model` | `claude-opus-5-5` | phase 3 model, e.g. `--model claude-haiku-4-5` for cheaper calls |
| `--accept-review` | off | with `add`, also index `needs_review` skills a human has cleared |
| `--json` | off | machine-readable output |

Phase 3 needs `ANTHROPIC_API_KEY` (or an `ant auth login` profile).

## Statuses

| Status | Phase | Meaning |
|---|---|---|
| `unchanged` | 1 | same skill id and same hash as the indexed version |
| `exact_duplicate` | 1 | identical content already indexed, or earlier in the same batch |
| `duplicate` | 2 / 3 | cosine ≥ `--high`, or the LLM said "duplicate" |
| `needs_review` | 2 / 3 | ambiguous with no LLM, or the LLM said "overlapping" |
| `unique` | 2 / 3 | nothing close; indexed on `add` |

Skills found unique are added to the in-memory index as they are checked, so two
copies inside the same incoming repo are caught against each other.

## Cost

For an index of N approved skills and a repo with m skills:

* Phase 1: dictionary lookups.
* Phase 2: m embeddings (local model: free) + m matrix-vector products against N vectors.
* Phase 3: one LLM request per ambiguous skill, usually a small fraction of m.

Past ~50k skills, swap the NumPy scan in `SkillIndex.nearest` for FAISS or sqlite-vec.

## Tests

```bash
python -m pytest -q
```
