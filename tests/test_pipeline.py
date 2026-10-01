from pathlib import Path

import numpy as np
import pytest

from skill_dedup import Status, Thresholds, check, seed
from skill_dedup.cli import main
from skill_dedup.embedders import HashingEmbedder
from skill_dedup.index import SkillIndex
from skill_dedup.judge import Verdict, build_prompt
from skill_dedup.skill import content_sha, discover, normalize_name

PDF = """---
name: pdf-tools
description: Extract text and tables from PDF files, merge and split PDF documents.
---
Use pypdf to read pages. To merge, append pages from each file into one writer.
To split, write each page range to its own file. Extract tables with pdfplumber.
"""

GIT = """---
name: git-commit-helper
description: Write conventional commit messages from the staged git diff.
---
Run git diff --staged, summarise the change, and format it as type(scope): subject.
"""


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel / "SKILL.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


@pytest.fixture
def env(tmp_path):
    good = tmp_path / "good"
    write(good, "pdf", PDF)
    write(good, "git", GIT)
    emb = HashingEmbedder()
    index = SkillIndex.load(tmp_path / "idx", emb.name, emb.dim)
    seed(index, emb, discover(good, "good"))
    return tmp_path, emb, index


def statuses(results):
    return {r.skill.id: r.status for r in results}


def test_normalization():
    assert normalize_name("PDF-Tools") == normalize_name("pdf_tools") == "pdftools"
    assert content_sha("a  \r\nb\n\n") == content_sha("a\nb")


def test_phase1_exact_copy_and_unchanged(env):
    tmp, emb, index = env
    incoming = tmp / "incoming"
    write(incoming, "copied", PDF.replace("\n", "\r\n"))  # same content, CRLF
    res = check(discover(incoming, "other"), index, emb)
    assert statuses(res) == {"other/pdftools": Status.EXACT_DUPLICATE}
    assert res[0].phase == 1

    # re-checking the baseline itself costs nothing
    res = check(discover(tmp / "good", "good"), index, emb)
    assert {r.status for r in res} == {Status.UNCHANGED}


def test_phase2_near_copy_flagged_without_llm(env):
    tmp, emb, index = env
    incoming = tmp / "incoming"
    write(incoming, "pdf2", PDF.replace("name: pdf-tools", "name: pdf-kit")
          .replace("own file", "own output file"))
    res = check(discover(incoming, "other"), index, emb)
    assert res[0].status is Status.DUPLICATE and res[0].phase == 2
    assert res[0].matches[0].id == "good/pdftools"


def test_unrelated_skill_is_unique_and_indexed(env):
    tmp, emb, index = env
    incoming = tmp / "incoming"
    write(incoming, "k8s", """---
name: k8s-debug
description: Diagnose crashing Kubernetes pods using kubectl logs and describe.
---
Check events, container restarts and OOMKilled reasons.
""")
    res = check(discover(incoming, "other"), index, emb)
    assert res[0].status is Status.UNIQUE
    assert "other/k8sdebug" in index.by_id()


def test_duplicates_within_same_batch(env):
    tmp, emb, index = env
    incoming = tmp / "incoming"
    body = """---
name: {n}
description: Generate SQL migrations for Postgres schema changes with rollback steps.
---
Write an up and a down migration. Wrap in a transaction. Never drop columns blindly.
"""
    write(incoming, "a", body.format(n="sql-migrate"))
    write(incoming, "b", body.format(n="sql-migrations"))
    res = check(discover(incoming, "other"), index, emb)
    # the first is indexed as it is checked, so the second one is caught against it
    assert res[0].status is Status.UNIQUE
    assert res[1].status in (Status.DUPLICATE, Status.NEEDS_REVIEW)
    assert res[1].matches[0].id == "other/sqlmigrate"


def test_updated_skill_not_matched_against_its_old_version(env):
    tmp, emb, index = env
    updated = tmp / "good_v2"
    write(updated, "pdf", PDF + "\nAlso supports encrypted PDFs.\n")
    res = check(discover(updated, "good"), index, emb)
    assert res[0].status is Status.UNIQUE  # re-embedded, replaces old vector
    assert len(index.meta) == 2


class FakeJudge:
    def __init__(self, relation):
        self.relation, self.calls = relation, 0

    def judge(self, skill, candidates):
        self.calls += 1
        return [Verdict(c["id"], self.relation, "fake") for c in candidates]


@pytest.mark.parametrize("relation,expected", [
    ("duplicate", Status.DUPLICATE),
    ("overlapping", Status.NEEDS_REVIEW),
    ("distinct", Status.UNIQUE),
])
def test_phase3_only_for_ambiguous(env, relation, expected):
    tmp, emb, index = env
    incoming = tmp / "incoming"
    # Same normalized name as the baseline but different wording -> goes to the judge.
    write(incoming, "pdf", """---
name: PDF_Tools
description: Fill in PDF form fields and flatten them.
---
Use pypdf form APIs to set field values, then flatten.
""")
    write(incoming, "far", """---
name: weather
description: Fetch the weather forecast for a city.
---
Call the forecast API.
""")
    judge = FakeJudge(relation)
    res = check(discover(incoming, "other"), index, emb, judge, Thresholds())
    by = {r.skill.id: r for r in res}
    assert judge.calls == 1  # the unrelated skill never reaches the LLM
    assert by["other/pdftools"].status is expected and by["other/pdftools"].phase == 3
    assert by["other/weather"].status is Status.UNIQUE


def test_judge_prompt_contains_candidates(env):
    tmp, emb, index = env
    skill = discover(tmp / "good", "x")[0]
    prompt = build_prompt(skill, index.meta)
    assert '"good/pdftools"' in prompt and '"good/gitcommithelper"' in prompt


def test_cli_seed_check_add(tmp_path, capsys):
    write(tmp_path / "good", "pdf", PDF)
    write(tmp_path / "new", "copy", PDF)
    idx = ["--index", str(tmp_path / "idx"), "--embedder", "hashing", "--no-llm"]
    assert main(["seed", str(tmp_path / "good"), *idx]) == 0
    assert main(["check", str(tmp_path / "new"), *idx]) == 1
    assert "exact_duplicate" in capsys.readouterr().out

    write(tmp_path / "new2", "git", GIT)
    assert main(["add", str(tmp_path / "new2"), *idx]) == 0
    reloaded = SkillIndex.load(tmp_path / "idx", "hashing:1024", 1024)
    assert len(reloaded.meta) == 2 and reloaded.vecs.shape == (2, 1024)
    assert np.allclose(np.linalg.norm(reloaded.vecs, axis=1), 1.0, atol=1e-5)


def test_index_rejects_other_embedder(tmp_path):
    write(tmp_path / "good", "pdf", PDF)
    assert main(["seed", str(tmp_path / "good"), "--index", str(tmp_path / "idx"),
                 "--embedder", "hashing"]) == 0
    with pytest.raises(ValueError, match="embedder"):
        SkillIndex.load(tmp_path / "idx", "st:other", 384)


def test_claude_judge_parses_structured_output(env):
    import json
    from types import SimpleNamespace

    from skill_dedup.judge import ClaudeJudge

    tmp, emb, index = env
    payload = {"verdicts": [
        {"candidate_id": "good/pdftools", "relation": "duplicate", "reason": "same job"},
        {"candidate_id": "made/up", "relation": "duplicate", "reason": "hallucinated id"},
    ]}
    sent = {}

    def create(**kw):
        sent.update(kw)
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text=json.dumps(payload))])

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))
    skill = discover(tmp / "good", "x")[0]
    verdicts = ClaudeJudge(client=client).judge(skill, index.meta)
    assert [(v.candidate_id, v.relation) for v in verdicts] == [("good/pdftools", "duplicate")]
    assert sent["output_config"]["format"]["type"] == "json_schema"
    assert sent["fallbacks"] == "default"
