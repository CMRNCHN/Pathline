"""runtime/node_view.py — Adapter bridging storage.IVRNode to the interface
expected by DiscoveryEngine.

The discovery engine was designed around a PromptNode with a .branches dict
(option → BranchObservation) and .announced_options list. StorageBackend stores
these as separate tables (ivr_edges, announced_options). This module assembles
them into a NodeView that satisfies the discovery engine's interface without
changing the storage schema or the discovery engine internals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.storage import StorageBackend, IVRNode


@dataclass
class BranchView:
    """Mimics the BranchObservation.count interface the discovery engine reads."""
    dtmf_option: str
    to_node_id: str | None
    count: int          # = edge.observation_count
    confidence: float   # = edge.confidence


@dataclass
class NodeView:
    """Combines IVRNode + its edges + announced_options into one object.

    Attributes mirror those accessed by DiscoveryEngine:
      .node_id, .canonical_key, .epistemic_state, .confidence,
      .announced_options (list of AnnouncedOption),
      .branches (dict[str, BranchView])
    """
    node_id: str
    system_id: str
    canonical_key: str
    display_prompt: str
    epistemic_state: str        # EpistemicState value
    confidence: float
    observation_count: int
    announced_options: list      # list[AnnouncedOption]
    branches: dict[str, BranchView] = field(default_factory=dict)

    @property
    def prompt(self) -> str:
        """Alias for display_prompt — satisfies DiscoveryEngine helper functions."""
        return self.display_prompt

    # Convenience — used by _is_menu_node, _is_auth_gate helpers
    @property
    def node_type(self) -> str:
        """Inferred from epistemic state and structure; not stored separately."""
        if not self.branches:
            return "LEAF"
        return "MENU"


def build_node_view(node: IVRNode, storage: StorageBackend) -> NodeView:
    """Load edges and announced options for *node* and return a NodeView."""
    edges = storage.get_edges_from_node(node.node_id)
    announced = storage.get_announced_options(node.node_id)

    branches: dict[str, BranchView] = {
        edge.dtmf_option: BranchView(
            dtmf_option=edge.dtmf_option,
            to_node_id=edge.to_node_id,
            count=edge.observation_count,
            confidence=edge.confidence,
        )
        for edge in edges
    }

    return NodeView(
        node_id=node.node_id,
        system_id=node.system_id,
        canonical_key=node.canonical_key,
        display_prompt=node.display_prompt,
        epistemic_state=node.epistemic_state,
        confidence=node.confidence,
        observation_count=node.observation_count,
        announced_options=announced,
        branches=branches,
    )


def build_node_views(system_id: str, storage: StorageBackend) -> dict[str, NodeView]:
    """Return all NodeViews for *system_id*, keyed by node_id."""
    nodes = storage.get_nodes_by_system(system_id)
    return {n.node_id: build_node_view(n, storage) for n in nodes}
