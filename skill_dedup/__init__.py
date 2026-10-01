"""Three-phase duplicate detection for Claude Code skills across plugin marketplaces.

Phase 1  exact:      content SHA-256 + normalized-name lookup (free)
Phase 2  embeddings: new/updated skills vs. an index of approved skill vectors (cheap)
Phase 3  LLM judge:  only the ambiguous candidates from phase 2 (a few calls)
"""

from .pipeline import Status, Thresholds, add_to_index, check, seed

__all__ = ["Status", "Thresholds", "add_to_index", "check", "seed"]
