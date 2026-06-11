"""
Executable topology enforcement for Pathline sovereign domains.

Static only: uses Python ast + deterministic filesystem traversal.
No runtime imports of application modules.
"""

from __future__ import annotations

import ast
import warnings
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

PROJECT_ROOT = Path(__file__).parent.parent

_EXCLUDE_DIRS = frozenset({
    ".venv", ".git", "__pycache__", "pathline.egg-info",
    "tmp", "docs", ".ai", ".github", ".vscode", ".idea",
    ".pytest_cache", ".claude",
})

DOMAINS = frozenset({
    "runtime", "replay", "analyst", "agents",
    "governance", "infrastructure", "tests", "tools",
})

PRODUCTION_DOMAINS = DOMAINS - {"tests"}

_LEGACY_FRAGMENTS = [
    "ivr_assessor",
    "backend.python",
    ".ai.REPODOCK",
]

_FORBIDDEN_DIRS = [
    PROJECT_ROOT / "backend" / "python",
    PROJECT_ROOT / "src" / "ivr_assessor",
    PROJECT_ROOT / "IVRSuite",
    PROJECT_ROOT / "legacy_backend",
]

# Hard fail: these cross-domain edges must never exist.
_HARD_FORBIDDEN_EDGES = frozenset({
    ("governance", "runtime"),
    ("governance", "replay"),
    ("governance", "analyst"),
    ("governance", "agents"),
    ("agents", "replay"),
    ("agents", "analyst"),
    ("replay", "agents"),
})

# Temporarily tolerated edges with migration rationale.
# These are tracked and reported but do not cause test failure.
_TOLERATED_EDGES: dict[tuple[str, str], str] = {
    ("runtime", "replay"): (
        "MIGRATION: extract replay coordination out of runtime kernel; "
        "target: replay domain owns all replay state transitions"
    ),
    ("replay", "analyst"): (
        "MIGRATION: move path constants (EVENTS_DIR, SNAPSHOTS_DIR) to "
        "infrastructure.config.paths — replay must not depend on analyst"
    ),
    ("runtime", "analyst"): (
        "MIGRATION: move path constants (EVENTS_DIR, SNAPSHOT_INTERVAL) to "
        "infrastructure.config.paths — runtime must not depend on analyst"
    ),
    ("analyst", "runtime"): (
        "EXPECTED: analyst layer reads from runtime state, events, and kernel"
    ),
    ("analyst", "replay"): (
        "EXPECTED: analyst layer reads from replay timelines and verification"
    ),
    ("runtime", "agents"): (
        "MIGRATION: decouple prompt_intelligence from runtime core; "
        "target: runtime receives classification results, does not call agents directly"
    ),
    ("tests", "runtime"): "EXPECTED: test suite imports runtime modules",
    ("tests", "replay"): "EXPECTED: test suite imports replay modules",
    ("tests", "analyst"): "EXPECTED: test suite imports analyst modules",
    ("tests", "agents"): "EXPECTED: test suite imports agents modules",
    ("tests", "infrastructure"): "EXPECTED: test suite imports infrastructure config",
}

# Production→tests imports are now fully forbidden: the telecom validation
# framework (EvidenceManifest, TelecomTestRunner, etc.) was migrated out of
# tests/ into analyst/telecom/. This allow-list is intentionally empty —
# ANY production→tests import is now a hard failure.
_KNOWN_ANALYST_TEST_IMPORTS: dict[str, frozenset[str]] = {}


# ---------------------------------------------------------------------------
# AST helpers — no runtime imports of project code below this line
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Import:
    source_file: str   # relative to PROJECT_ROOT, forward-slash normalized
    source_domain: str
    module: str
    target_domain: str
    lineno: int


def _iter_py_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.py")):
        if any(part in _EXCLUDE_DIRS for part in path.parts):
            continue
        yield path


def _file_domain(path: Path) -> str | None:
    try:
        rel = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return None
    first = rel.parts[0] if rel.parts else None
    return first if first in DOMAINS else None


def _parse_imports(path: Path) -> list[tuple[str, int]]:
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                results.append((node.module, node.lineno))
    return results


def _module_domain(module: str) -> str | None:
    first = module.split(".")[0]
    return first if first in DOMAINS else None


def _rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def _collect_cross_domain_imports(
    source_domains: frozenset[str] | None = None,
) -> list[Import]:
    results: list[Import] = []
    for path in _iter_py_files(PROJECT_ROOT):
        src = _file_domain(path)
        if src is None:
            continue
        if source_domains is not None and src not in source_domains:
            continue
        rel = _rel(path)
        for module, lineno in _parse_imports(path):
            tgt = _module_domain(module)
            if tgt and tgt != src:
                results.append(Import(rel, src, module, tgt, lineno))
    return results


def _find_domain_cycles(graph: dict[str, set[str]]) -> list[tuple[str, ...]]:
    """Return all simple domain-level cycles. Deduplicated by canonical rotation."""
    seen: set[tuple[str, ...]] = set()
    cycles: list[tuple[str, ...]] = []
    all_nodes = set(graph) | {v for vals in graph.values() for v in vals}

    def dfs(start: str, node: str, path: list[str], visited: set[str]) -> None:
        for neighbor in sorted(graph.get(node, [])):
            if neighbor == start and len(path) > 1:
                cycle = tuple(path)
                min_i = min(range(len(cycle)), key=lambda i: cycle[i])
                normalized = cycle[min_i:] + cycle[:min_i]
                if normalized not in seen:
                    seen.add(normalized)
                    cycles.append(normalized)
            elif neighbor not in visited:
                dfs(start, neighbor, path + [neighbor], visited | {neighbor})

    for start in sorted(all_nodes):
        dfs(start, start, [start], {start})

    return cycles


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_no_forbidden_directory_resurrection() -> None:
    """Legacy directories must not exist on disk."""
    found = [str(d) for d in _FORBIDDEN_DIRS if d.exists()]
    assert not found, "Forbidden legacy directories exist:\n" + "\n".join(found)


def test_no_legacy_namespace_imports() -> None:
    """No file may import a legacy namespace fragment."""
    violations: list[str] = []
    for path in _iter_py_files(PROJECT_ROOT):
        for module, lineno in _parse_imports(path):
            for frag in _LEGACY_FRAGMENTS:
                if frag in module:
                    violations.append(
                        f"  {_rel(path)}:{lineno}: '{module}' matches legacy pattern '{frag}'"
                    )
    assert not violations, "Legacy namespace imports found:\n" + "\n".join(violations)


def test_no_production_imports_tests_domain() -> None:
    """
    Production code must not import from the tests domain.

    The telecom validation framework (EvidenceManifest, TelecomTestRunner, etc.)
    was migrated from tests/ to analyst/telecom/, so the previously-tracked
    exception is gone. Hard fail on ANY production→tests import.
    """
    violations: list[str] = []
    for imp in _collect_cross_domain_imports(PRODUCTION_DOMAINS):
        if imp.target_domain != "tests":
            continue
        known = _KNOWN_ANALYST_TEST_IMPORTS.get(imp.source_file, frozenset())
        if imp.module in known:
            continue
        violations.append(
            f"  {imp.source_file}:{imp.lineno}\n"
            f"    {imp.source_domain} → tests: imports '{imp.module}'"
        )
    assert not violations, (
        "Production code imports from tests domain (HARD FAIL):\n"
        + "\n".join(violations)
        + "\n\nMIGRATION: move test utilities to the appropriate production domain."
    )


def test_hard_forbidden_cross_domain_imports() -> None:
    """Hard-forbidden cross-domain edges must not exist."""
    violations: list[str] = []
    for imp in _collect_cross_domain_imports():
        edge = (imp.source_domain, imp.target_domain)
        if edge in _HARD_FORBIDDEN_EDGES:
            violations.append(
                f"  {imp.source_file}:{imp.lineno}\n"
                f"    {imp.source_domain} → {imp.target_domain}: '{imp.module}'"
            )
    assert not violations, (
        "Hard-forbidden cross-domain imports found:\n" + "\n".join(violations)
    )


def test_no_hard_forbidden_cycles() -> None:
    """Cycles involving governance or agents are forbidden."""
    graph: dict[str, set[str]] = defaultdict(set)
    for imp in _collect_cross_domain_imports():
        if "tests" in (imp.source_domain, imp.target_domain):
            continue
        graph[imp.source_domain].add(imp.target_domain)

    hard_nodes = {"governance", "agents"}
    violations: list[str] = []
    for cycle in _find_domain_cycles(dict(graph)):
        if set(cycle) & hard_nodes:
            violations.append(" → ".join(cycle) + f" → {cycle[0]}")

    assert not violations, (
        "Hard-forbidden cycles detected (governance or agents in cycle):\n"
        + "\n".join(violations)
    )


def test_tolerated_violations_are_bounded() -> None:
    """
    Known tolerated cross-domain violations are tracked and reported.
    Does NOT fail — these are documented migration targets.
    Any edge NOT in _TOLERATED_EDGES and NOT in _HARD_FORBIDDEN_EDGES is implicitly new
    and will surface here as a warning.
    """
    all_imports = _collect_cross_domain_imports()
    by_edge: dict[tuple[str, str], list[Import]] = defaultdict(list)

    for imp in all_imports:
        edge = (imp.source_domain, imp.target_domain)
        if edge in _TOLERATED_EDGES or edge in _HARD_FORBIDDEN_EDGES:
            by_edge[edge].append(imp)

    for edge in sorted(_TOLERATED_EDGES):
        imps = by_edge.get(edge, [])
        if not imps:
            continue
        note = _TOLERATED_EDGES[edge]
        detail = "\n".join(
            f"    {i.source_file}:{i.lineno}: {i.module}"
            for i in sorted(imps, key=lambda x: (x.source_file, x.lineno))
        )
        warnings.warn(
            f"[TOLERATED] {edge[0]} → {edge[1]} ({len(imps)} import(s))\n"
            f"  {note}\n{detail}",
            stacklevel=2,
        )

    # Check for soft cycles (runtime/replay/analyst) and report them.
    graph: dict[str, set[str]] = defaultdict(set)
    for imp in all_imports:
        if "tests" in (imp.source_domain, imp.target_domain):
            continue
        graph[imp.source_domain].add(imp.target_domain)

    soft_nodes = {"runtime", "replay", "analyst"}
    for cycle in _find_domain_cycles(dict(graph)):
        if set(cycle) & soft_nodes:
            warnings.warn(
                f"[SOFT CYCLE] {' → '.join(cycle)} → {cycle[0]}\n"
                "  MIGRATION: incrementally decouple these domains",
                stacklevel=2,
            )


def test_known_analyst_test_imports_are_bounded() -> None:
    """
    Verify the analyst→tests telecom-framework imports have not grown beyond
    _KNOWN_ANALYST_TEST_IMPORTS. Any new analyst→tests import fails immediately.
    """
    violations: list[str] = []
    for imp in _collect_cross_domain_imports(frozenset({"analyst"})):
        if imp.target_domain != "tests":
            continue
        known = _KNOWN_ANALYST_TEST_IMPORTS.get(imp.source_file, frozenset())
        if imp.module not in known:
            violations.append(
                f"  {imp.source_file}:{imp.lineno}: new analyst→tests import '{imp.module}'\n"
                f"  MIGRATION: move this module to analyst/telecom/ "
                f"(see _KNOWN_ANALYST_TEST_IMPORTS for existing tracked violations)"
            )
    assert not violations, (
        "New analyst→tests imports detected (HARD FAIL — boundary must not grow):\n"
        + "\n".join(violations)
    )


def test_infrastructure_path_migration_report() -> None:
    """
    Identify non-analyst production code importing path constants from
    analyst.backend.ui.ui_state. These should move to infrastructure.config.paths.
    Warns but does not fail.
    """
    targets = {"analyst.backend.ui.ui_state", "analyst.backend.ui"}
    offenders: list[str] = []
    for imp in _collect_cross_domain_imports():
        if imp.source_domain in {"analyst", "tests"}:
            continue
        if any(imp.module == t or imp.module.startswith(t + ".") for t in targets):
            offenders.append(
                f"  {imp.source_file}:{imp.lineno}: {imp.source_domain} imports "
                f"path constants from '{imp.module}'"
            )
    if offenders:
        warnings.warn(
            "[PATH MIGRATION] These production files import path constants from "
            "analyst.backend.ui.ui_state.\n"
            "  Target: migrate path constants to infrastructure/config/paths.py\n"
            + "\n".join(offenders),
            stacklevel=2,
        )
