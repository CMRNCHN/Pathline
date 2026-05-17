from typing import List, Dict, Any, Optional

class FailureClassifier:
    CATEGORIES = {
        "DEAD_END": "Call reached a state where no further progression was possible.",
        "LOOP_DETECTED": "Repeated prompts or states were detected.",
        "NO_INPUT_TIMEOUT": "Call ended due to silence or lack of user input detected.",
        "LOW_CONFIDENCE": "Audio transcription confidence was consistently below threshold.",
        "TRANSFER_STOPPED": "Call transfer failed or was blocked.",
        "ROUTING_DRIFT": "Actual path diverged significantly from expected path.",
        "AUDIO_GAP": "Significant periods of missing audio detected.",
        "WEBSOCKET_FAILURE": "Connection to the streaming server was lost.",
        "RUNTIME_STALLED": "Internal state machine stopped responding.",
        "OPERATOR_ABORT": "User manually terminated the session.",
        "UNKNOWN_FAILURE": "The cause of failure could not be determined.",
        "SUCCESSFUL_COMPLETION": "The session reached a terminal goal successfully."
    }

    def classify(self, events: List[Dict[str, Any]], telecom_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        primary = "UNKNOWN_FAILURE"
        secondary = []
        explanation = "Default classification."
        evidence_event_ids = []

        # Check for success first
        if telecom_result and telecom_result.get("outcome") == "success":
            primary = "SUCCESSFUL_COMPLETION"
            explanation = "Test plan goals were met."
        
        # Rule-based classification
        runtime_failures = [e for e in events if e.get("kind") == "runtime_failure"]
        if runtime_failures:
            primary = "RUNTIME_STALLED"
            explanation = "Internal runtime errors detected."
            evidence_event_ids.extend([e.get("event_id") for e in runtime_failures if e.get("event_id")])

        loops = [e for e in events if e.get("kind") == "loop_detected"]
        if loops:
            if primary == "UNKNOWN_FAILURE":
                primary = "LOOP_DETECTED"
            else:
                secondary.append("LOOP_DETECTED")
            evidence_event_ids.extend([e.get("event_id") for e in loops if e.get("event_id")])

        # Check for VAD / timeout
        timeouts = [e for e in events if "timeout" in e.get("kind", "").lower()]
        if timeouts:
            secondary.append("NO_INPUT_TIMEOUT")

        # Confidence
        confidence_events = [e for e in events if e.get("payload", {}).get("confidence", 1.0) < 0.4]
        if confidence_events:
            secondary.append("LOW_CONFIDENCE")

        # Result based overrides
        if telecom_result:
            stop_reason = telecom_result.get("stop_reason")
            if stop_reason == "max_duration":
                secondary.append("DEAD_END")
                explanation = "Reached maximum allowed duration without completion."
            elif stop_reason == "user_abort":
                primary = "OPERATOR_ABORT"
                explanation = "Session was terminated by the operator."

        return {
            "primary_category": primary,
            "secondary_categories": list(set(secondary)),
            "confidence": 0.9 if primary != "UNKNOWN_FAILURE" else 0.5,
            "evidence_event_ids": evidence_event_ids,
            "explanation": explanation
        }
