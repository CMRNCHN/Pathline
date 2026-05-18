import time
import pytest
from runtime.supervision.runtime_supervisor import RuntimeSupervisor, RuntimeState, WebSocketState

def test_supervisor_registration():
    supervisor = RuntimeSupervisor()
    session_id = "test_session"
    supervisor.register_session(session_id)
    
    info = supervisor.get_session_info(session_id)
    assert info is not None
    assert info.session_id == session_id
    assert info.runtime_state == RuntimeState.ACTIVE
    assert info.websocket_state == WebSocketState.CONNECTED

def test_supervisor_activity_updates():
    supervisor = RuntimeSupervisor()
    session_id = "test_session"
    supervisor.register_session(session_id)
    
    initial_activity = supervisor.get_session_info(session_id).last_activity_at
    time.sleep(0.01)
    supervisor.update_activity(session_id)
    
    updated_info = supervisor.get_session_info(session_id)
    assert updated_info.last_activity_at > initial_activity

def test_supervisor_websocket_transitions():
    supervisor = RuntimeSupervisor()
    session_id = "test_session"
    supervisor.register_session(session_id)
    
    # Disconnect
    supervisor.update_activity(session_id, websocket_connected=False)
    info = supervisor.get_session_info(session_id)
    assert info.websocket_state == WebSocketState.DISCONNECTED
    assert info.runtime_state == RuntimeState.DISCONNECTED
    
    # Reconnect
    supervisor.update_activity(session_id, websocket_connected=True)
    info = supervisor.get_session_info(session_id)
    assert info.websocket_state == WebSocketState.CONNECTED
    assert info.runtime_state == RuntimeState.RECOVERING

def test_supervisor_stall_detection():
    supervisor = RuntimeSupervisor()
    supervisor.RUNTIME_STALL_TIMEOUT_SECONDS = 0.1 # Short timeout for test
    
    session_id = "test_session"
    supervisor.register_session(session_id)
    
    time.sleep(0.2)
    supervisor._check_sessions()
    
    info = supervisor.get_session_info(session_id)
    assert info.runtime_state == RuntimeState.STALLING

def test_supervisor_health_snapshot():
    supervisor = RuntimeSupervisor()
    supervisor.register_session("s1")
    supervisor.register_session("s2")
    supervisor.update_activity("s2", websocket_connected=False)
    
    snapshot = supervisor.get_health_snapshot()
    assert snapshot["active_session_count"] == 1
    assert snapshot["websocket_disconnect_count"] == 1
    assert snapshot["runtime_state_counts"][RuntimeState.ACTIVE] == 1
    assert snapshot["runtime_state_counts"][RuntimeState.DISCONNECTED] == 1

def test_supervised_session_success():
    from runtime.supervision.runtime_supervisor import supervisor
    session_id = "test_supervised"
    
    def mock_task():
        return "success"
        
    result = supervisor.supervised_session(session_id, mock_task)
    assert result == "success"
    # Should be removed from registry after completion
    assert supervisor.get_session_info(session_id) is None

def test_supervised_session_failure():
    from runtime.supervision.runtime_supervisor import supervisor
    session_id = "test_supervised_fail"
    
    def mock_task():
        raise ValueError("simulated failure")
        
    with pytest.raises(ValueError, match="simulated failure"):
        supervisor.supervised_session(session_id, mock_task)
    
    # After failure, it is cleaned up and removed from registry
    assert supervisor.get_session_info(session_id) is None

def test_heartbeat_recording():
    supervisor = RuntimeSupervisor()
    supervisor.start() # Start to subscribe to events
    session_id = "test_heartbeat"
    supervisor.register_session(session_id)
    
    info = supervisor.get_session_info(session_id)
    initial_heartbeat = info.last_heartbeat_at
    
    time.sleep(0.01)
    supervisor.record_heartbeat(session_id)
    
    # Need to wait a bit for the bus to deliver the event if it's async
    # But EventBus is currently sync (direct call to handlers)
    assert info.last_heartbeat_at > initial_heartbeat