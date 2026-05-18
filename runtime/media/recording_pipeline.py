from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

def download_recording(url: str, dest_path: Path) -> None:
    if not url.endswith(".wav"):
        url += ".wav"
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

def transcribe_audio(audio_path: Path) -> list[dict[str, Any]]:
    api_key = os.environ.get("DEEPGRAM_API_KEY")
    if not api_key:
        logger.warning("DEEPGRAM_API_KEY missing, skipping transcription")
        return []
    
    url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&utterances=true"
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "audio/wav"
    }
    
    with open(audio_path, "rb") as f:
        response = requests.post(url, headers=headers, data=f)
    
    if not response.ok:
        logger.error("Deepgram API error: %s", response.text)
        response.raise_for_status()
        
    data = response.json()
    utterances = data.get("results", {}).get("utterances", [])
    
    transcript: list[dict[str, Any]] = []
    for u in utterances:
        transcript.append({
            "start": float(u.get("start", 0.0)),
            "end": float(u.get("end", 0.0)),
            "text": str(u.get("transcript", ""))
        })
    return transcript

def classify_segment(text: str) -> str:
    keywords = {"press", "enter", "say", "account", "invalid", "hold", "for"}
    text_lower = text.lower()
    
    if any(kw in text_lower for kw in keywords):
        return "ivr_prompt"
    
    words = text_lower.split()
    if len(words) < 15 and text_lower.endswith(('.', ':', '?')):
        if words and words[0] in ("please", "enter", "press", "say", "speak"):
            return "ivr_prompt"
            
    return "system_message"

def detect_triggers(transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
    triggers: list[dict[str, Any]] = []
    
    for segment in transcript:
        text = str(segment.get("text", ""))
        segment_type = classify_segment(text)
        
        if segment_type == "ivr_prompt":
            triggers.append({
                "start": float(segment.get("start", 0.0)),
                "end": float(segment.get("end", 0.0)),
                "text": text,
                "type": segment_type
            })
            
    return triggers

def slice_audio(full_audio_path: Path, clips_dir: Path, triggers: list[dict[str, Any]]) -> None:
    clips_dir.mkdir(parents=True, exist_ok=True)
    
    for idx, trigger in enumerate(triggers):
        clip_path = clips_dir / f"clip_{idx}.wav"
        cmd = [
            "ffmpeg", "-y", "-i", str(full_audio_path),
            "-ss", str(trigger["start"]),
            "-to", str(trigger["end"]),
            "-c", "copy", str(clip_path)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except subprocess.CalledProcessError as e:
            logger.error("Failed to extract clip %d: %s", idx, e)

def process_recording(recording_url: str, call_sid: str, recording_sid: str = "") -> None:
    logger.info("Starting post-call processing for %s", call_sid)
    
    try:
        base_dir = Path("data") / "recordings" / call_sid
        base_dir.mkdir(parents=True, exist_ok=True)
        
        full_audio_path = base_dir / "full.wav"
        transcript_path = base_dir / "transcript.json"
        triggers_path = base_dir / "triggers.json"
        clips_dir = base_dir / "clips"
        metadata_path = base_dir / "metadata.json"
        
        logger.info("Downloading recording from %s", recording_url)
        download_recording(recording_url, full_audio_path)
        
        logger.info("Transcribing audio...")
        transcript = transcribe_audio(full_audio_path)
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(transcript, f, indent=2)
            
        logger.info("Detecting triggers...")
        triggers = detect_triggers(transcript)
        with open(triggers_path, "w", encoding="utf-8") as f:
            json.dump(triggers, f, indent=2)
            
        logger.info("Slicing audio...")
        slice_audio(full_audio_path, clips_dir, triggers)
        
        logger.info("Saving metadata...")
        duration = transcript[-1]["end"] if transcript else 0.0
        metadata = {
            "call_sid": call_sid,
            "recording_sid": recording_sid,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "clip_count": len(triggers),
            "duration": duration
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
            
        logger.info("Pipeline completed successfully for %s", call_sid)
        
    except Exception as e:
        logger.error("Pipeline failed for %s: %s", call_sid, e, exc_info=True)