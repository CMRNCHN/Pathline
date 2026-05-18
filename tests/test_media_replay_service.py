from replay.media_sync.media_replay_service import MediaReplayService

def test_resolve_recording_path(tmp_path, monkeypatch):
    # Setup mock recordings dir
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir()
    date_dir = rec_dir / "2024-01-01"
    date_dir.mkdir()
    rec_file = date_dir / "session_test123.wav"
    rec_file.write_text("dummy audio")
    
    monkeypatch.setattr("replay.media_sync.media_replay_service.RECORDINGS_DIR", rec_dir)
    
    service = MediaReplayService()
    resolved = service.resolve_recording_path("test123")
    assert resolved == rec_file
    
    unresolved = service.resolve_recording_path("nonexistent")
    assert unresolved is None

def test_get_media_metadata(tmp_path, monkeypatch):
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir()
    date_dir = rec_dir / "2024-01-01"
    date_dir.mkdir()
    rec_file = date_dir / "session_test123.wav"
    rec_file.write_text("dummy audio")
    
    monkeypatch.setattr("replay.media_sync.media_replay_service.RECORDINGS_DIR", rec_dir)
    
    service = MediaReplayService()
    metadata = service.get_media_metadata("test123")
    
    assert metadata["session_id"] == "test123"
    assert metadata["recording_exists"] is True
    assert "session_test123.wav" in metadata["recording_path"]
    assert metadata["media_url"] == "/api/replays/test123/media/stream"