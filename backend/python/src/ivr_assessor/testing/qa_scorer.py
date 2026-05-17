from typing import Dict, Any, List, Optional

class QAScorer:
    def __init__(self):
        pass

    def score_session(self, 
                      events: List[Dict[str, Any]], 
                      telecom_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        
        factors = {}
        
        # 1. Stability Score (no runtime failures, no stalls)
        runtime_failures = [e for e in events if e.get("kind") == "runtime_failure"]
        stalls = [e for e in events if e.get("kind") == "runtime_stall"]
        stability_score = max(0, 100 - (len(runtime_failures) * 20) - (len(stalls) * 10))
        factors["stability"] = {
            "score": stability_score,
            "count_failures": len(runtime_failures),
            "count_stalls": len(stalls)
        }

        # 2. Routing Score (completion, no loops)
        loops = [e for e in events if e.get("kind") == "loop_detected"]
        routing_score = 100
        if loops:
            routing_score -= min(50, len(loops) * 15)
        
        outcome = telecom_result.get("outcome") if telecom_result else None
        if outcome == "failure":
            routing_score -= 30
        
        factors["routing"] = {
            "score": max(0, routing_score),
            "loops_detected": len(loops),
            "outcome": outcome
        }

        # 3. Transcript Quality Score (confidence events)
        confidence_events = [e for e in events if "confidence" in e.get("payload", {})]
        if confidence_events:
            avg_conf = sum(e["payload"]["confidence"] for e in confidence_events) / len(confidence_events)
            transcript_score = int(avg_conf * 100)
        else:
            transcript_score = 0
            
        factors["transcript_quality"] = {
            "score": transcript_score,
            "avg_confidence": sum(e["payload"]["confidence"] for e in confidence_events) / len(confidence_events) if confidence_events else 0
        }

        # 4. Latency Score
        # Look for response_latency_ms in events
        latency_events = [e["payload"].get("latency_ms") for e in events if "latency_ms" in e.get("payload", {})]
        if latency_events:
            avg_latency = sum(latency_events) / len(latency_events)
            # 0-500ms = 100, 500-2000ms = 100-0
            latency_score = max(0, min(100, int(100 - (avg_latency - 500) / 15))) if avg_latency > 500 else 100
        else:
            latency_score = 100
            avg_latency = 0
            
        factors["latency"] = {
            "score": latency_score,
            "avg_latency_ms": avg_latency
        }

        # 5. Evidence Completeness
        # Check for recording, transcript, events
        has_recording = any(e.get("kind") == "recording_started" for e in events)
        has_transcript = len(confidence_events) > 0
        completeness_score = (50 if has_recording else 0) + (50 if has_transcript else 0)
        factors["evidence_completeness"] = {
            "score": completeness_score,
            "has_recording": has_recording,
            "has_transcript": has_transcript
        }

        # Calculate final session score
        session_score = int(
            (stability_score * 0.3) + 
            (routing_score * 0.3) + 
            (transcript_score * 0.2) + 
            (latency_score * 0.1) + 
            (completeness_score * 0.1)
        )

        return {
            "session_score": session_score,
            "factors": factors,
            "explanation": "Deterministic score based on stability, routing, transcript quality, latency, and evidence completeness."
        }
