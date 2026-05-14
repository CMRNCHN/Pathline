from typing import Any, Dict, List, Optional

def diff_states(before: Optional[Any], after: Any) -> Dict[str, Any]:
    """
    Compute operational deltas between two ReplayState objects.
    Returns a frontend-safe JSON-compatible dictionary.
    """
    diff = {
        "added": {},
        "removed": {},
        "changed": {},
        "metrics": {}
    }

    if before is None:
        # Initial state, everything is 'added'
        diff["added"] = {
            "nodes": after.nodes,
            "edges": after.edges,
            "transcripts": after.transcripts,
            "visited_nodes": after.visited_nodes,
            "dtmf_history": after.dtmf_history,
            "active_path": after.active_path
        }
        diff["changed"]["call_status"] = after.call_status
        return diff

    # 1. Nodes
    before_nodes = set(before.nodes.keys())
    after_nodes = set(after.nodes.keys())
    
    added_nodes = after_nodes - before_nodes
    if added_nodes:
        diff["added"]["nodes"] = {nid: after.nodes[nid] for nid in added_nodes}
    
    # Check for changed nodes (e.g. metadata updates)
    changed_nodes = {}
    for nid in before_nodes & after_nodes:
        if before.nodes[nid] != after.nodes[nid]:
            changed_nodes[nid] = after.nodes[nid]
    if changed_nodes:
        diff["changed"]["nodes"] = changed_nodes

    # 2. Edges (list of dicts, order matters for reconstruction but we look for new ones)
    before_edges = [json_stable_hash(e) for e in before.edges]
    added_edges = []
    for edge in after.edges:
        if json_stable_hash(edge) not in before_edges:
            added_edges.append(edge)
    if added_edges:
        diff["added"]["edges"] = added_edges

    # 3. Transcripts
    if len(after.transcripts) > len(before.transcripts):
        diff["added"]["transcripts"] = after.transcripts[len(before.transcripts):]

    # 4. DTMF History
    if len(after.dtmf_history) > len(before.dtmf_history):
        diff["added"]["dtmf_history"] = after.dtmf_history[len(before.dtmf_history):]

    # 5. Active Path
    if after.active_path != before.active_path:
        diff["changed"]["active_path"] = after.active_path

    # 6. Call Status
    if after.call_status != before.call_status:
        diff["changed"]["call_status"] = after.call_status

    # 7. Metrics
    diff["metrics"] = after.metrics

    return diff

def json_stable_hash(obj: Any) -> str:
    """Simple stable string representation for comparison of list items."""
    import json
    return json.dumps(obj, sort_keys=True)
