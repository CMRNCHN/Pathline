from typing import List, Dict, Any, Optional
import logging
from .replay_state import ReplayState
from .event_types import EventType

logger = logging.getLogger(__name__)

class ReplaySearch:
    @staticmethod
    def search_events(
        state: ReplayState,
        event_types: Optional[List] = None,
        query: Optional[str] = None,
        dtmf_only: bool = False,
        min_confidence: Optional[float] = None,
        categories: Optional[List] = None,
        severities: Optional[List] = None,
        media_time_range: Optional[tuple] = None,
        event_index_range: Optional[tuple] = None,
        bookmarks: Optional[List] = None,
        annotations: Optional[List] = None
    ) -> List[Dict[str, Any]]:
        results = []
        
        for idx, event in enumerate(state.events):
            # Filter by index range
            if event_index_range and not (event_index_range[0] <= idx <= event_index_range[1]):
                continue
                
            # Filter by media time range
            media_offset = event.get("media_offset_ms")
            if media_time_range and media_offset is not None:
                if not (media_time_range[0] <= media_offset <= media_time_range[1]):
                    continue
            
            # Filter by event type
            etype = event.get("type")
            if event_types and etype not in event_types:
                continue
                
            # Filter by DTMF
            if dtmf_only and etype != EventType.DTMF_SENT:
                continue
                
            # Filter by transcript text
            payload = event.get("payload", {})
            if query and etype == EventType.TRANSCRIPT_FINAL:
                text = payload.get("text", "").lower()
                if query.lower() not in text:
                    continue
            elif query and etype != EventType.TRANSCRIPT_FINAL:
                # If query provided but not a transcript event, maybe search payload?
                # For now, let's stick to transcripts for query.
                continue
                
            # Filter by confidence
            if min_confidence is not None:
                if etype == EventType.TRANSCRIPT_FINAL:
                    conf = payload.get("confidence", 1.0)
                    if conf < min_confidence:
                        continue
                elif etype == "TRANSCRIPT_FINAL": # Literal check for test cases using dicts
                    conf = payload.get("confidence", 1.0)
                    if conf < min_confidence:
                        continue
                else:
                    # Non-transcript events might not have confidence, 
                    # should they be excluded if a confidence filter is active?
                    # Generally yes, if we are looking for "high confidence" events.
                    continue
            
            # Attach a search result entry
            results.append({
                "event_index": idx,
                "event": event
            })
            
        # Bookmark/Annotation search would be joined here if passed in
        # But usually we return all bookmarks/annotations for the session separately.
        # If explicitly requested to filter bookmarks by category:
        if bookmarks and categories:
            # Filter bookmarks
            pass
            
        return results

    @staticmethod
    def format_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Return frontend-safe JSON
        formatted = []
        for res in results:
            idx = res["event_index"]
            event = res["event"]
            formatted.append({
                "index": idx,
                "type": event.get("type"),
                "media_time_ms": event.get("media_offset_ms"),
                "payload": event.get("payload"),
                "timestamp": event.get("meta", {}).get("timestamp") or event.get("ts")
            })
        return formatted
