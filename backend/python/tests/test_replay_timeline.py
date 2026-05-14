import pytest
from ivr_assessor.events.replay_timeline import ReplayTimeline

def test_timeline_navigation():
    events = [{"ts": 1}, {"ts": 2}, {"ts": 3}]
    timeline = ReplayTimeline("session_1", events)
    
    assert timeline.cursor_position == 0
    assert timeline.total_events == 3
    
    timeline.step_forward()
    assert timeline.cursor_position == 1
    assert timeline.current_event() == events[0]
    
    timeline.step_forward()
    timeline.step_forward()
    assert timeline.cursor_position == 3
    
    # Boundary
    timeline.step_forward()
    assert timeline.cursor_position == 3
    
    timeline.step_backward()
    assert timeline.cursor_position == 2
    assert timeline.current_event() == events[1]
    
    timeline.seek(0)
    assert timeline.cursor_position == 0
    assert timeline.current_event() is None

def test_timeline_seek():
    events = [{"ts": 1}, {"ts": 2}, {"ts": 3}]
    timeline = ReplayTimeline("session_1", events)
    
    timeline.seek(2)
    assert timeline.cursor_position == 2
    
    timeline.seek(5) # OOB
    assert timeline.cursor_position == 3
    
    timeline.seek(-1) # OOB
    assert timeline.cursor_position == 0
