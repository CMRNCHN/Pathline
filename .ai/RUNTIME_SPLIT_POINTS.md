# Runtime Split Points

Documents the coordination gravity that would need to be resolved before the GUI server
and stream server can run as separate OS processes (e.g., separate Docker containers,
separate systemd units, or separate workers).

Current topology: single Python process, two ports.
- `8080` — `ThreadingHTTPServer` (live_map_gui.py `launch()`)
- `8081` — `StreamingServer` FastAPI/uvicorn (streaming_server.py), started as a background
            thread inside the GUI process

---

## Shared in-process state (the coupling)

### 1. `AppState` singleton (`backend/ui/ui_state.py` → `STATE`)
All of the following are written from both the HTTP handler thread and the session thread,
and read from the HTTP polling endpoint (`/status`):
- `STATE.logs` — append-only list; HTTP handler drains it in `build_status_payload()`
- `STATE.live_caption` — written by the transcript callback in `_run_session_thread`
- `STATE.graph` — written by the session thread after each DFS cycle
- `STATE.is_running`, `STATE.session`, `STATE.source`, `STATE.streaming_server`

**Split cost:** Replace with a small IPC layer (e.g., a Redis list for logs, a shared Redis
key for live_caption/graph/is_running). The session thread would need to run in the same
process as the stream server (it already owns transcript callbacks), and expose a minimal
HTTP API that the GUI server polls instead of reading `STATE` directly.

### 2. `RunSuiteState` singleton (`backend/ui/ui_state.py` → `RS_STATE`)
- `RS_STATE.set_runner()` / `RS_STATE.get_runner()` / `RS_STATE.poll()` / `RS_STATE.abort()`
- The runner is wired to the stream server via `persistent_stream.register_transcript_callback`
  inside `start_run_suite()` in `run_suite_routes.py`.

**Split cost:** Same as AppState. The SuiteRunner would need to live in the same process
as the stream server; expose a `/run-suite/poll` endpoint that the GUI proxies.

### 3. `_persistent_stream` module-level singleton (`live_map_gui.py`)
- Created lazily by `_get_or_start_stream_server()`.
- Passed into `_run_session_thread` so it can register transcript callbacks.
- Its `.stream_auth_token` is read when building stream URLs for Twilio.

**Split cost:** Move stream server startup to its own entrypoint. Expose `stream_auth_token`
via an internal `/internal/stream-token` endpoint (127.0.0.1 only). GUI fetches it at
call-start time instead of reading the object directly.

### 4. `_run_session_thread` (live_map_gui.py)
The session thread is spawned from the HTTP handler (`/start` route via `mapper_routes.handle_start`).
It references `_persistent_stream` by closure (through `_get_or_start_stream_server()`),
mutates `STATE`, and calls `session.run()` which drives the DFS loop.

**Split cost:** Highest. The session thread is the hot path; it must stay co-located with
the stream server for zero-copy transcript delivery. The GUI would become a thin frontend
that starts the session via an internal API call.

---

## Split readiness checklist

| Area                        | Ready to split? | Blocker                                     |
|-----------------------------|-----------------|---------------------------------------------|
| Static file serving         | ✅ Yes           | No shared state                             |
| Config API (`/config`)      | ✅ Yes           | Reads env only                              |
| Test suite editor CRUD      | ✅ Yes           | File I/O on `SUITES_DIR` only               |
| Run suite CRUD (list/delete)| ✅ Yes           | File I/O on `RUN_SUITES_DIR` only           |
| `/status` polling           | ❌ No            | Reads `STATE` directly                      |
| `/start` call initiation    | ❌ No            | Spawns session thread; touches stream server|
| `/inject-dtmf`, `/inject`   | ❌ No            | Calls `STATE.source.prompt_queue.put()`     |
| Run suite start/poll/abort  | ❌ No            | `RS_STATE` couples runner to stream server  |
| IVR graph reads             | ⚠️ Partial       | `STATE.graph` written in-process; could be  |
|                             |                 | persisted to disk and read by GUI           |

---

## Recommended split path (if ever needed)

1. Move `_run_session_thread` + `SuiteRunner` into the stream server process.
2. Expose internal HTTP endpoints (127.0.0.1 only):
   - `POST /internal/start` — starts session, returns session_id
   - `GET  /internal/status` — returns logs, graph, live_caption, is_running
   - `POST /internal/inject` — puts to prompt queue
   - `GET  /internal/stream-token` — returns stream_auth_token
   - `GET  /internal/run-suite/poll` — returns RS_STATE events
3. GUI server becomes a pure proxy + static asset server; no shared Python objects.
4. `AppState` and `RunSuiteState` can be deleted or reduced to thin stubs.

No changes to the hot path (audio_pipeline → stt → transcript_filter → DFS → tts) are needed.
