from dataclasses import dataclass, field
from typing import Dict, List, Any
from replay.verification.replay_diff import diff_states

@dataclass
class MockState:
    nodes: Dict[str, Any] = field(default_factory=dict)
    edges: List[Any] = field(default_factory=list)
    transcripts: List[Dict[str, Any]] = field(default_factory=list)
    dtmf_history: List[str] = field(default_factory=list)
    active_path: List[str] = field(default_factory=list)
    call_status: str = "unknown"
    visited_nodes: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

def test_diff_initial():
    after = MockState(
        nodes={"n1": {"id": "n1"}},
        call_status="started"
    )
    diff = diff_states(None, after)
    assert "n1" in diff["added"]["nodes"]
    assert diff["changed"]["call_status"] == "started"

def test_diff_node_added():
    before = MockState(nodes={"n1": {"id": "n1"}})
    after = MockState(nodes={"n1": {"id": "n1"}, "n2": {"id": "n2"}})
    diff = diff_states(before, after)
    assert "n2" in diff["added"]["nodes"]
    assert "n1" not in diff["added"]["nodes"]

def test_diff_transcript_added():
    before = MockState(transcripts=[{"text": "hello"}])
    after = MockState(transcripts=[{"text": "hello"}, {"text": "world"}])
    diff = diff_states(before, after)
    assert len(diff["added"]["transcripts"]) == 1
    assert diff["added"]["transcripts"][0]["text"] == "world"

def test_diff_edge_added():
    before = MockState(edges=[{"from": "a", "to": "b"}])
    after = MockState(edges=[{"from": "a", "to": "b"}, {"from": "b", "to": "c"}])
    diff = diff_states(before, after)
    assert len(diff["added"]["edges"]) == 1
    assert diff["added"]["edges"][0]["to"] == "c"