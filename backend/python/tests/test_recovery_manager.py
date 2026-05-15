from ivr_assessor.runtime.runtime_supervisor import RuntimeSupervisor, RuntimeState
from ivr_assessor.runtime.recovery_manager import RecoveryManager

def test_recovery_attempts_bounded():
    supervisor = RuntimeSupervisor()
    recovery = RecoveryManager(max_attempts=2)
    
    # Injecting local supervisor into recovery for testing if it was a singleton, 
    # but since it's a class we can just use the global one or mock it.
    # Actually, the singleton 'supervisor' is imported in recovery_manager.
    # To test properly we should probably use a mock or ensure we reset the singleton.
    
    from ivr_assessor.runtime import runtime_supervisor
    original_supervisor = runtime_supervisor.supervisor
    runtime_supervisor.supervisor = supervisor # Monkeypatch for test
    
    try:
        session_id = "test_session"
        supervisor.register_session(session_id)
        supervisor.update_activity(session_id, websocket_connected=False)
        
        assert recovery.attempt_recovery(session_id) is True
        assert supervisor.get_session_info(session_id).recovery_attempts == 1
        
        assert recovery.attempt_recovery(session_id) is True
        assert supervisor.get_session_info(session_id).recovery_attempts == 2
        
        assert recovery.attempt_recovery(session_id) is False
        assert supervisor.get_session_info(session_id).runtime_state == RuntimeState.FAILED
    finally:
        runtime_supervisor.supervisor = original_supervisor

def test_mark_recovered():
    supervisor = RuntimeSupervisor()
    recovery = RecoveryManager()
    
    from ivr_assessor.runtime import runtime_supervisor
    original_supervisor = runtime_supervisor.supervisor
    runtime_supervisor.supervisor = supervisor
    
    try:
        session_id = "test_session"
        supervisor.register_session(session_id)
        supervisor.update_activity(session_id, websocket_connected=False)
        supervisor.update_activity(session_id, websocket_connected=True) # transitions to RECOVERING
        
        assert supervisor.get_session_info(session_id).runtime_state == RuntimeState.RECOVERING
        recovery.mark_recovered(session_id)
        # mark_recovered just emits an event, the actual transition to ACTIVE happens on next activity
    finally:
        runtime_supervisor.supervisor = original_supervisor
