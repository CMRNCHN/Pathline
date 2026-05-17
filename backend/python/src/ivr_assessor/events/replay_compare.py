from typing import Dict, Any, Optional
import logging
from .replay_state import ReplayState
from .replay_diff import diff_states

logger = logging.getLogger(__name__)

class ReplayCompare:
    @staticmethod
    def compare_sessions(left: ReplayState, right: ReplayState) -> Dict[str, Any]:
        """
        Compare two replay sessions and return a summary of differences.
        """
        # Event count and duration
        left_duration = 0
        if left.events:
             left_duration = left.events[-1].get("media_offset_ms", 0)
        
        right_duration = 0
        if right.events:
             right_duration = right.events[-1].get("media_offset_ms", 0)

        # Basic diff using existing logic
        delta = diff_states(left, right)
        
        # Path divergence: first index where active_path differs
        path_divergence_index = -1
        min_path_len = min(len(left.active_path), len(right.active_path))
        for i in range(min_path_len):
            if left.active_path[i] != right.active_path[i]:
                path_divergence_index = i
                break
        
        if path_divergence_index == -1 and len(left.active_path) != len(right.active_path):
             path_divergence_index = min_path_len

        # Confidence summary
        def get_avg_confidence(state: ReplayState) -> float:
            confidences = [e.get("payload", {}).get("confidence", 1.0) 
                           for e in state.events if e.get("type") == "TRANSCRIPT_FINAL"]
            return sum(confidences) / len(confidences) if confidences else 1.0

        summary = {
            "left_session_id": left.session_id,
            "right_session_id": right.session_id,
            "event_count_delta": len(right.events) - len(left.events),
            "duration_delta_ms": right_duration - left_duration,
            "path_divergence_index": path_divergence_index,
            "node_delta_summary": {
                "added": len(delta.get("added", {}).get("nodes", {})),
                "changed": len(delta.get("changed", {}).get("nodes", {}))
            },
            "edge_delta_summary": {
                "added": len(delta.get("added", {}).get("edges", []))
            },
            "transcript_delta_summary": {
                "added": len(delta.get("added", {}).get("transcripts", []))
            },
            "confidence_delta_summary": {
                "left_avg": get_avg_confidence(left),
                "right_avg": get_avg_confidence(right)
            },
            "failure_event_delta": len([e for e in right.events if e.get("type") == "ERROR_RAISED"]) - \
                                   len([e for e in left.events if e.get("type") == "ERROR_RAISED"])
        }
        
        return summary
