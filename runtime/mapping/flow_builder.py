from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class _Node:
    id: str
    label: str
    prompt: str
    visits: int = 0


@dataclass
class _Edge:
    id: str
    source: str
    target: str
    label: str


class FlowMapBuilder:
    """Builds an IVR flow map incrementally from transcription events."""

    def __init__(self) -> None:
        self._nodes: dict[str, _Node] = {}
        self._edges: dict[str, _Edge] = {}
        self._current_node_id: str | None = None

    # ------------------------------------------------------------------
    # Public mutation API
    # ------------------------------------------------------------------

    def add_node(
        self,
        label: str,
        prompt: str = "",
        transcript: str = "",
        confidence: float = 1.0,
    ) -> str:
        node_id = self._node_id(label)
        if node_id in self._nodes:
            self._nodes[node_id].visits += 1
        else:
            self._nodes[node_id] = _Node(id=node_id, label=label, prompt=prompt)

        if self._current_node_id and self._current_node_id != node_id:
            edge_id = f"{self._current_node_id}->{node_id}"
            if edge_id not in self._edges:
                self._edges[edge_id] = _Edge(
                    id=edge_id,
                    source=self._current_node_id,
                    target=node_id,
                    label="",
                )

        self._current_node_id = node_id
        return node_id

    def add_dtmf_option(self, digit: str, target_label: str) -> None:
        if self._current_node_id is None:
            return
        target_id = self._node_id(target_label)
        if target_id not in self._nodes:
            self._nodes[target_id] = _Node(id=target_id, label=target_label, prompt="")
        edge_id = f"{self._current_node_id}-dtmf{digit}->{target_id}"
        if edge_id not in self._edges:
            self._edges[edge_id] = _Edge(
                id=edge_id,
                source=self._current_node_id,
                target=target_id,
                label=f"DTMF {digit}",
            )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def to_cytoscape(self) -> dict:
        elements = []
        for node in self._nodes.values():
            elements.append({"data": {"id": node.id, "label": node.label}})
        for edge in self._edges.values():
            elements.append(
                {
                    "data": {
                        "id": edge.id,
                        "source": edge.source,
                        "target": edge.target,
                        "label": edge.label,
                    }
                }
            )
        return {"elements": elements}

    def to_dict(self) -> dict:
        return {
            "nodes": [
                {"id": n.id, "label": n.label, "prompt": n.prompt, "visits": n.visits}
                for n in self._nodes.values()
            ],
            "edges": [
                {"id": e.id, "source": e.source, "target": e.target, "label": e.label}
                for e in self._edges.values()
            ],
        }

    def to_mermaid(self) -> str:
        lines = ["graph TD"]
        for node in self._nodes.values():
            safe = node.label.replace('"', "'")
            lines.append(f'    {node.id}["{safe}"]')
        for edge in self._edges.values():
            arrow = f"-- {edge.label} -->" if edge.label else "-->"
            lines.append(f"    {edge.source} {arrow} {edge.target}")
        return "\n".join(lines)

    @property
    def nodes(self) -> dict[str, _Node]:
        return self._nodes

    @property
    def edges(self) -> dict[str, _Edge]:
        return self._edges

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _node_id(label: str) -> str:
        return "n" + hashlib.md5(label.strip().lower().encode()).hexdigest()[:8]
