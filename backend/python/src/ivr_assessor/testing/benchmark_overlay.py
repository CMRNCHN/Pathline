from typing import List, Dict, Any, Optional

class BenchmarkOverlay:
    def __init__(self):
        pass

    def summarize(self, events: List[Dict[str, Any]], telecom_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        durations = [e.get("t_ms", 0) for e in events]
        total_duration_ms = max(durations) if durations else 0
        
        prompts = [e for e in events if e.get("kind") == "prompt"]
        dtmfs = [e for e in events if e.get("kind") == "dtmf_sent"]
        speech = [e for e in events if e.get("kind") == "speech_detected"]
        retries = [e for e in events if "retry" in str(e).lower()]
        unresolved = [e for e in events if e.get("kind") == "unresolved_state"]
        failures = [e for e in events if e.get("kind") == "runtime_failure"]
        transcripts = [e["payload"].get("confidence") for e in events if "confidence" in e.get("payload", {})]
        transfers = [e for e in events if e.get("kind") == "transfer_initiated"]
        loops = [e for e in events if e.get("kind") == "loop_detected"]

        latency_events = [e["payload"].get("latency_ms") for e in events if "latency_ms" in e.get("payload", {})]
        avg_latency = sum(latency_events) / len(latency_events) if latency_events else 0

        return {
            "total_duration_ms": total_duration_ms,
            "prompt_count": len(prompts),
            "dtmf_count": len(dtmfs),
            "speech_injection_count": len(speech),
            "retry_count": len(retries),
            "unresolved_count": len(unresolved),
            "runtime_failure_count": len(failures),
            "transcript_confidence_avg": sum(transcripts) / len(transcripts) if transcripts else 0,
            "transfer_count": len(transfers),
            "loop_count": len(loops),
            "average_latency_ms": avg_latency
        }
