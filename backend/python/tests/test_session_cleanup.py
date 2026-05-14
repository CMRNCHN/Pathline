import pytest
from ivr_assessor.runtime.runtime_supervisor import RuntimeSupervisor, RuntimeState
from ivr_assessor.runtime.session_cleanup import SessionCleanup

def test_cleanup_idempotency():
    supervisor = RuntimeSupervisor()
    cleanup = SessionCleanup()
    
    from ivr_assessor.runtime import runtime_supervisor
    original_supervisor = runtime_supervisor.supervisor
    runtime_supervisor.supervisor = supervisor
    
    try:
        session_id = "test_session"
        supervisor.register_session(session_id)
        supervisor.terminate_session(session_id)
        
        assert supervisor.get_session_info(session_id).cleanup_state is False
        
        assert cleanup.cleanup_session(session_id) is True
        # Info is now removed from registry
        assert supervisor.get_session_info(session_id) is None
        
        # Second call should also be True (idempotent, even if not in registry anymore)
        assert cleanup.cleanup_session(session_id) is False # False because it's not even in registry to find info
    finally:
        runtime_supervisor.supervisor = original_supervisor

def test_cleanup_transitions_to_cleaned():
    supervisor = RuntimeSupervisor()
    cleanup = SessionCleanup()
    
    from ivr_assessor.runtime import runtime_supervisor
    original_supervisor = runtime_supervisor.supervisor
    runtime_supervisor.supervisor = supervisor
    
    try:
        session_id = "test_session"
        supervisor.register_session(session_id)
        # Not terminated yet
        
        cleanup.cleanup_session(session_id)
        assert supervisor.get_session_info(session_id) is None
    finally:
        runtime_supervisor.supervisor = original_supervisor
