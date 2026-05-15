from ivr_assessor.backend.routes.mapper_routes import build_status_payload
from ivr_assessor.runtime.runtime_supervisor import supervisor

def test_status_payload_includes_health():
    supervisor.register_session("test_session")
    payload = build_status_payload()
    
    assert "runtime_health" in payload
    assert payload["runtime_health"]["active_sessions"] >= 1
    assert "runtime_state_counts" in payload["runtime_health"]
    assert payload["runtime_health"]["runtime_state_counts"]["ACTIVE"] >= 1
