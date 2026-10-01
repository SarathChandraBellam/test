"""Parsing SKILL.md files into Skill records."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


@dataclass(frozen=True)
class Skill:
    id: str           # "<source>/<name>", stable across versions of the same skill
    source: str       # repo / marketplace the skill came from
    name: str
    description: str
    body: str
    sha: str          # hash of the normalized file content
    path: str

    @property
    def norm_name(self) -> str:
        return normalize_name(self.name)


def normalize_name(name: str) -> str:
    """'PDF-Tools', 'pdf_tools' and 'pdf tools' all become 'pdftools'."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def content_sha(text: str) -> str:
    """Hash that ignores line endings, trailing whitespace and blank-line padding."""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    normalized = "\n".join(lines).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def parse_skill(path: Path, source: str) -> Skill:
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    if m := _FRONTMATTER.match(text):
        meta = yaml.safe_load(m.group(1)) or {}
        body = m.group(2)
    name = str(meta.get("name") or path.parent.name)
    return Skill(
        id=f"{source}/{normalize_name(name)}",
        source=source,
        name=name,
        description=str(meta.get("description") or "").strip(),
        body=body.strip(),
        sha=content_sha(text),
        path=str(path),
    )


def discover(root: Path, source: str | None = None) -> list[Skill]:
    """Find every SKILL.md under root. source defaults to the directory name."""
    root = Path(root)
    source = source or root.resolve().name
    return [parse_skill(p, source) for p in sorted(root.rglob("SKILL.md"))]
