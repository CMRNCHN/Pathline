"""Persistent storage for IVR maps, keyed by target phone number."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def _store_dir() -> Path:
    d = Path.home() / ".ivr_maps"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_filename(target: str) -> str:
    return re.sub(r"[^0-9a-zA-Z+]", "_", target) + ".json"


def _path_for(target: str) -> Path:
    return _store_dir() / _safe_filename(target)


def save_map(target: str, graph: dict[str, Any], extra: dict[str, Any] | None = None) -> Path:
    payload = {
        "target": target,
        "saved_at": datetime.utcnow().isoformat() + "Z",
        "graph": graph,
        **(extra or {}),
    }
    path = _path_for(target)
    # Merge with existing if present so manual edits and prior runs accumulate
    if path.exists():
        try:
            existing = json.loads(path.read_text())
            payload["created_at"] = existing.get("created_at", payload["saved_at"])
            payload["session_count"] = existing.get("session_count", 0) + 1
        except Exception:
            payload["created_at"] = payload["saved_at"]
            payload["session_count"] = 1
    else:
        payload["created_at"] = payload["saved_at"]
        payload["session_count"] = 1
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return path


def load_map(target: str) -> dict[str, Any] | None:
    path = _path_for(target)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def list_maps() -> list[dict[str, Any]]:
    out = []
    for path in _store_dir().glob("*.json"):
        try:
            data = json.loads(path.read_text())
            graph = data.get("graph", {})
            out.append({
                "target": data.get("target", path.stem),
                "saved_at": data.get("saved_at", ""),
                "created_at": data.get("created_at", ""),
                "session_count": data.get("session_count", 0),
                "node_count": len(graph),
                "branch_count": sum(len(n.get("branches", {})) for n in graph.values()),
            })
        except Exception:
            continue
    out.sort(key=lambda m: m.get("saved_at", ""), reverse=True)
    return out


def delete_map(target: str) -> bool:
    path = _path_for(target)
    if path.exists():
        path.unlink()
        return True
    return False


def edit_node(target: str, old_prompt: str, new_prompt: str | None) -> bool:
    """Rename a node (new_prompt set) or delete it (new_prompt=None) in the saved map."""
    data = load_map(target)
    if not data:
        return False
    graph = data.get("graph", {})
    if old_prompt not in graph:
        return False
    node = graph.pop(old_prompt)
    if new_prompt:
        if "prompt" in node:
            node["prompt"] = new_prompt
        for other in graph.values():
            for branch in other.get("branches", {}).values():
                nxt = branch.get("next_prompts", [])
                if old_prompt in nxt:
                    nxt[:] = [new_prompt if p == old_prompt else p for p in nxt]
        graph[new_prompt] = node
    else:
        for other in graph.values():
            for branch in other.get("branches", {}).values():
                nxt = branch.get("next_prompts", [])
                if old_prompt in nxt:
                    nxt[:] = [p for p in nxt if p != old_prompt]
    data["graph"] = graph
    extra = {k: v for k, v in data.items() if k not in ["target", "saved_at", "created_at", "session_count", "graph"]}
    save_map(target, graph, extra=extra, is_update_only=True)
    return True


def set_node_notes(target: str, prompt: str, notes: str) -> bool:
    data = load_map(target)
    if not data:
        return False
    graph = data.get("graph", {})
    if prompt not in graph:
        return False
    if notes.strip():
        graph[prompt]["notes"] = notes.strip()
    else:
        graph[prompt].pop("notes", None)
    data["graph"] = graph
    extra = {k: v for k, v in data.items() if k not in ["target", "saved_at", "created_at", "session_count", "graph"]}
    save_map(target, graph, extra=extra, is_update_only=True)
    return True


def export_mermaid(graph: dict[str, Any], target: str = "") -> str:
    """Render the graph as a Mermaid flowchart."""
    lines = ["flowchart TD"]
    if target:
        lines.append(f'    %% IVR map for {target}')
    # Assign short IDs to each prompt so Mermaid output stays readable
    ids: dict[str, str] = {}
    for i, prompt in enumerate(sorted(graph.keys())):
        ids[prompt] = f"N{i}"
    for prompt, node in sorted(graph.items()):
        nid = ids[prompt]
        label = prompt.replace("\"", "'").replace("\n", " ")
        if len(label) > 80:
            label = label[:77] + "..."
        lines.append(f'    {nid}["{label}"]')
    for prompt, node in sorted(graph.items()):
        for digit, branch in (node.get("branches") or {}).items():
            for child in branch.get("next_prompts", []):
                if child in ids:
                    lines.append(f'    {ids[prompt]} -->|{digit}| {ids[child]}')
    return "\n".join(lines)


def export_markdown(graph: dict[str, Any], target: str = "") -> str:
    """Render the graph as a Markdown document with tables and a Mermaid embed."""
    lines = [f"# IVR Map: {target or 'untitled'}", ""]
    lines.append(f"**Nodes:** {len(graph)}  ")
    branch_count = sum(len(n.get("branches", {})) for n in graph.values())
    lines.append(f"**Branches:** {branch_count}")
    lines.append("")
    lines.append("## Flow Diagram")
    lines.append("")
    lines.append("```mermaid")
    lines.append(export_mermaid(graph, target))
    lines.append("```")
    lines.append("")
    lines.append("## Nodes")
    lines.append("")
    for prompt, node in sorted(graph.items()):
        lines.append(f"### {prompt}")
        lines.append("")
        lines.append(f"- Observations: {node.get('observations', 0)}")
        lines.append(f"- Confidence: {round((node.get('confidence') or 0) * 100)}%")
        if node.get("notes"):
            lines.append(f"- Notes: {node['notes']}")
        branches = node.get("branches") or {}
        if branches:
            lines.append("")
            lines.append("| Digit | Count | Goes to |")
            lines.append("| --- | --- | --- |")
            for digit, b in sorted(branches.items()):
                nxt = ", ".join(b.get("next_prompts", [])) or "—"
                lines.append(f"| {digit} | {b.get('count', 0)} | {nxt} |")
        lines.append("")
    return "\n".join(lines)