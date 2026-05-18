# cspell:ignore dtmf ngrok uvicorn typer

from __future__ import annotations

import json
import queue
import time
from pathlib import Path

import typer

from . import __version__
from runtime.media.ai_voice import VoiceGenerationSpec, generate_voice_file
from runtime.state.batch_template import batch_entries_from_payload, run_batch_template
from runtime.state.call_template import (
    InjectionMode,
    TemplateStyle,
    build_call_template_plan,
    parse_mode_overrides,
)
from runtime.discovery_loop import (
    SessionOutcome,
    run_discovery_loop,
)
from runtime.kernel.execution_controller import ExecutionController
from replay.inspection import (
    format_replay_inspection_text,
    format_runtime_diagnostics_text,
    inspect_replay_artifact,
    load_runtime_payload,
    build_runtime_diagnostics,
)
from runtime.ivr_mapper import IvrMapper
from runtime.state.live_map import (
    InteractivePromptSource,
    LiveMappingSession,
    RecordingTelephonyClient,
    ScriptedPromptSource,
    build_default_response_library,
)
from runtime.multi_session import MultiSessionOrchestrator
from runtime.state.models import CallEvent
from replay.replay_mode import replay_trace
from runtime.state.response_library import ResponseClip, ResponseLibrary
from runtime.kernel.startup_runtime import bootstrap_runtime
from runtime.telephony import TelephonyClient


app = typer.Typer(help="IVR assessor CLI")


@app.callback()
def _bootstrap_runtime() -> None:
    bootstrap_runtime()


class StreamQueuePromptSource:
    def __init__(self, q: queue.Queue, timeout: float):
        self.q = q
        self.timeout = timeout
        self._t_start = time.time()

    def next_event(self, session_id: str) -> CallEvent | None:
        try:
            text = self.q.get(timeout=self.timeout)
        except queue.Empty:
            return None
        if text is None:
            return None
        t_ms = int((time.time() - self._t_start) * 1000)
        return CallEvent(kind="prompt", text=text, t_ms=t_ms)

    def elapsed_ms(self) -> int:
        return int((time.time() - self._t_start) * 1000)


@app.command()
def version() -> None:
    """Print the IVR assessor CLI version."""
    typer.echo(f"ivr-assessor {__version__}")


@app.command()
def dry_run(
    target_number: str = typer.Option(..., "--target-number"),
) -> None:
    controller = ExecutionController(allowlist=[target_number])
    if not controller.can_dial(target_number):
        raise typer.Exit(code=2)

    typer.echo(f"Dry run for {target_number}")


@app.command()
def replay(
    trace_path: Path = typer.Option(..., "--trace-path"),
) -> None:
    result = replay_trace(trace_path)
    typer.echo(f"Replayed {result.summary['event_count']} events")
    typer.echo(f"Mapped {result.summary['node_count']} IVR nodes")
    typer.echo(result.report.text)


@app.command("inspect-replay")
def inspect_replay(
    trace_path: Path = typer.Option(..., "--trace-path"),
    output_format: str = typer.Option("text", "--format"),
) -> None:
    if not trace_path.exists():
        typer.echo(f"Trace file not found: {trace_path}")
        raise typer.Exit(code=2)

    payload = inspect_replay_artifact(trace_path)
    if output_format == "json":
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return
    if output_format != "text":
        typer.echo(f"Unsupported format: {output_format}")
        raise typer.Exit(code=2)
    typer.echo(format_replay_inspection_text(payload))


@app.command("inspect-runtime")
def inspect_runtime(
    metrics_path: Path | None = typer.Option(None, "--metrics-path"),
    runtime_url: str | None = typer.Option(None, "--runtime-url"),
    output_format: str = typer.Option("text", "--format"),
) -> None:
    if metrics_path is not None and runtime_url is not None:
        typer.echo("Choose either --metrics-path or --runtime-url, not both.")
        raise typer.Exit(code=2)
    if metrics_path is None and runtime_url is None:
        runtime_url = "http://127.0.0.1:8080/api/runtime-diagnostics"
    if metrics_path is not None and not metrics_path.exists():
        typer.echo(f"Metrics file not found: {metrics_path}")
        raise typer.Exit(code=2)

    try:
        payload = load_runtime_payload(metrics_path=metrics_path, runtime_url=runtime_url)
    except Exception as exc:
        typer.echo(f"Unable to load runtime payload: {exc}")
        raise typer.Exit(code=1)

    diagnostics = payload
    if "summary" not in payload or "timeline" not in payload:
        diagnostics = build_runtime_diagnostics(payload)

    if output_format == "json":
        typer.echo(json.dumps(diagnostics, indent=2, sort_keys=True))
        return
    if output_format != "text":
        typer.echo(f"Unsupported format: {output_format}")
        raise typer.Exit(code=2)
    typer.echo(format_runtime_diagnostics_text(diagnostics))


@app.command()
def map(
    target_number: list[str] = typer.Option(..., "--target-number"),
    response_mode: str = typer.Option("dtmf", "--response-mode"),
    session_mode: str = typer.Option(
        "single-session",
        "--session-mode",
        case_sensitive=False,
        help="Choose single-session or multi-session.",
    ),
    prompt: list[str] = typer.Option([], "--prompt", help="Scripted prompt text."),
    response_label: str = typer.Option("general", "--response-label"),
    response_style: str | None = typer.Option(None, "--response-style"),
    response_clip: list[str] = typer.Option(
        [],
        "--response-clip",
        help="A specific audio response clip in the format label=filepath. "
        "Repeat for multiple clips.",
    ),
    mode: str = typer.Option(
        "scripted",
        "--mode",
        help="Use 'scripted' for simulated runs or 'interactive' for real-time manual runs.",
    ),
    twilio_account_sid: str | None = typer.Option(
        None, "--twilio-account-sid", envvar="TWILIO_ACCOUNT_SID"
    ),
    twilio_auth_token: str | None = typer.Option(
        None, "--twilio-auth-token", envvar="TWILIO_AUTH_TOKEN"
    ),
    twilio_phone_number: str | None = typer.Option(
        None, "--twilio-phone-number", envvar="TWILIO_PHONE_NUMBER"
    ),
    user_phone_number: str | None = typer.Option(
        None, "--user-phone-number", envvar="USER_PHONE_NUMBER", help="Your phone number to join the call simultaneously."
    ),
) -> None:
    if not target_number:
        raise typer.Exit(code=2)

    if session_mode == "single-session":
        if len(target_number) != 1:
            typer.echo("single-session mapping expects exactly one target number")
            raise typer.Exit(code=2)

        summary = _run_single_session(
            target_number=target_number[0],
            response_mode=response_mode,
            prompt=prompt,
            response_label=response_label,
            response_style=response_style,
            response_clip=response_clip,
            mode=mode,
            twilio_account_sid=twilio_account_sid,
            twilio_auth_token=twilio_auth_token,
            twilio_phone_number=twilio_phone_number,
            user_phone_number=user_phone_number,
        )
        typer.echo(json.dumps(summary.as_dict(), indent=2, sort_keys=True))
        return

    if session_mode == "multi-session":
        payload = _run_multi_session(
            target_numbers=target_number,
            response_mode=response_mode,
            prompt=prompt,
            response_label=response_label,
            response_style=response_style,
            response_clip=response_clip,
        )
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    typer.echo(f"Unsupported session mode: {session_mode}")
    raise typer.Exit(code=2)


@app.command("iterate-map")
def iterate_map(
    target_number: str = typer.Option(..., "--target-number"),
    prompt: list[str] = typer.Option(
        [],
        "--prompt",
        help="Scripted prompt text. Repeat for multiple prompts. Each call replays "
        "this list (use scripted mode to dry-run the loop without real telephony).",
    ),
    max_calls: int = typer.Option(12, "--max-calls", help="Hard cap on number of calls."),
    wall_clock_cap_s: float = typer.Option(
        30.0,
        "--wall-clock-cap-s",
        help="Soft cap per call. After this many seconds we stop pulling new prompts "
        "but still finish processing the current one.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Optional path to write the JSON report. Always echoed to stdout.",
    ),
    mode: str = typer.Option(
        "scripted",
        "--mode",
        help="Use 'scripted' for simulated runs or 'interactive' for real Twilio calls.",
    ),
    stream_url: str | None = typer.Option(
        None,
        "--stream-url",
        envvar="IVR_STREAM_URL",
        help="ngrok wss:// URL for Twilio to stream audio to.",
    ),
    twilio_account_sid: str | None = typer.Option(
        None, "--twilio-account-sid", envvar="TWILIO_ACCOUNT_SID"
    ),
    twilio_auth_token: str | None = typer.Option(
        None, "--twilio-auth-token", envvar="TWILIO_AUTH_TOKEN"
    ),
    twilio_phone_number: str | None = typer.Option(
        None, "--twilio-phone-number", envvar="TWILIO_PHONE_NUMBER"
    ),
) -> None:
    """Run the iterative discovery loop until the IVR tree saturates.

    Each call lasts at most --wall-clock-cap-s seconds (soft cap). Between
    calls, the accumulated graph is replanned DFS-deepest into the next
    unexplored option. The loop stops when two consecutive calls add no
    new nodes, when every announced option has been walked, or when
    --max-calls is reached — whichever comes first.
    """
    prompt_queue = None
    if mode == "interactive":
        from .streaming_server import (
            start_server_in_background,
            register_transcript_callback,
            default_stream_auth_token,
            append_stream_auth_token,
        )

        if not stream_url:
            typer.echo("Error: --stream-url is required for interactive mode.", err=True)
            raise typer.Exit(code=1)

        prompt_queue = queue.Queue()

        wss = stream_url.strip().replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        if not wss.rstrip("/").endswith("/stream"):
            wss = f"{wss.rstrip('/')}/stream"
        stream_url = append_stream_auth_token(wss, default_stream_auth_token())

        start_server_in_background(port=8081)

        _utterance: dict[str, list[str]] = {"chunks": []}

        def _flush_utterance() -> None:
            joined = " ".join(_utterance["chunks"]).strip()
            _utterance["chunks"] = []
            if joined:
                prompt_queue.put(joined)

        def _on_transcript(text: str, is_final: bool, speech_final: bool) -> None:
            t = text.strip()
            if not t:
                if speech_final:
                    _flush_utterance()
                return
            if is_final:
                _utterance["chunks"].append(t)
                if speech_final:
                    _flush_utterance()

        register_transcript_callback(_on_transcript)

        from .events.event_sink import sink as EventSink
        from runtime.supervision.runtime_supervisor import supervisor
        EventSink.start()
        supervisor.start()

    def _runner(
        target: str,
        planned_path: list[str],
        mapper: IvrMapper,
    ) -> SessionOutcome:
        before_nodes = len(mapper.graph())
        before_branches = sum(
            1
            for node in mapper.graph().values()
            for b in (node.get("branches") or {}).values()
            if int((b or {}).get("count", 0) or 0) > 0
        )
        
        if mode == "interactive":
            from .twilio_client import TwilioTelephonyClient
            telephony = TwilioTelephonyClient(
                account_sid=twilio_account_sid,
                auth_token=twilio_auth_token,
                twilio_number=twilio_phone_number,
                stream_url=stream_url,
            )
            psource = StreamQueuePromptSource(prompt_queue, timeout=10.0)
        else:
            telephony = RecordingTelephonyClient()
            psource = ScriptedPromptSource(
                [
                    CallEvent(kind="prompt", text=text, t_ms=index * 250)
                    for index, text in enumerate(prompt)
                ]
            )

        session = LiveMappingSession(
            target_number=target,
            response_mode="dtmf",
            prompt_source=psource,
            telephony=telephony,
            response_library=build_default_response_library("general"),
            mapper=mapper,
            wall_clock_cap_s=wall_clock_cap_s,
            forced_branches=list(planned_path),
        )
        try:
            from runtime.supervision.runtime_supervisor import supervisor
            # Use call_sid if available from telephony.dial, but session.run does it
            # To be safe, generate a temporary one or dial early.
            # In interactive mode, we want supervised registration BEFORE dial might fail?
            # Actually, supervised_session will call register_session.
            
            # If session_id is None, supervised_session might have issues.
            # Let's ensure it has one.
            if mode == "interactive" and not session.session_id:
                # We can dial now to get the ID
                session.session_id = telephony.dial(target)
            
            call_sid = session.session_id or f"cli-{int(time.time())}"
            summary = supervisor.supervised_session(call_sid, session.run, call_sid=call_sid)
        except Exception as exc:  # pragma: no cover — surfaced to user
            return SessionOutcome(
                nodes_added=0,
                branches_walked=0,
                events=0,
                aborted=True,
                error=str(exc),
            )
        finally:
            if mode == "interactive" and session.session_id:
                try:
                    telephony.hangup(session.session_id)
                except Exception:
                    pass
            if prompt_queue:
                while True:
                    try:
                        prompt_queue.get_nowait()
                    except queue.Empty:
                        break

        after_nodes = len(mapper.graph())
        after_branches = sum(
            1
            for node in mapper.graph().values()
            for b in (node.get("branches") or {}).values()
            if int((b or {}).get("count", 0) or 0) > 0
        )
        return SessionOutcome(
            nodes_added=max(0, after_nodes - before_nodes),
            branches_walked=max(0, after_branches - before_branches),
            events=len(summary.events),
        )

    mapper, report = run_discovery_loop(
        target_number=target_number,
        runner=_runner,
        max_calls=max_calls,
    )

    payload = {
        "report": report.as_dict(),
        "graph": mapper.graph(),
    }
    blob = json.dumps(payload, indent=2, sort_keys=True, default=_json_default)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(blob, encoding="utf-8")
    typer.echo(blob)


def _json_default(value: object) -> object:
    if isinstance(value, set):
        return sorted(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON-serializable")


@app.command("live-map-gui")
def live_map_gui(
    stream_url: str | None = typer.Option(
        None,
        "--stream-url",
        envvar="IVR_STREAM_URL",
        help="WebSocket URL for Twilio media streaming (e.g. wss://xxxx.ngrok-free.app/stream).",
    ),
) -> None:
    """Launch the live map GUI."""
    try:
        from .live_map_gui import launch as launch_live_map
        launch_live_map(default_stream_url=stream_url)
    except Exception as exc:  # pragma: no cover - surfaced to user at runtime
        typer.echo(f"Unable to launch live map GUI: {exc}")
        raise typer.Exit(code=1)

@app.command("tracker-gui")
def tracker_gui() -> None:
    """Launch the local phone tracker GUI."""
    try:
        from .phone_tracker_gui import launch as launch_phone_tracker

        launch_phone_tracker()
    except ModuleNotFoundError as exc:
        if exc.name == "_tkinter":
            typer.echo("Unable to launch tracker GUI: tkinter is not available in this Python build")
            raise typer.Exit(code=1)
        raise
    except Exception as exc:  # pragma: no cover - surfaced to user at runtime
        typer.echo(f"Unable to launch tracker GUI: {exc}")
        raise typer.Exit(code=1)


@app.command("sms-serve")
def sms_serve(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8080, "--port"),
    no_verify_signature: bool = typer.Option(
        False,
        "--no-verify-signature",
        help="Disable Twilio request signature validation (debug only).",
    ),
) -> None:
    """Run the SMS bridge server (Twilio inbound webhook -> mapping job -> SMS reply)."""
    import uvicorn

    from .sms_server import build_state_from_env, create_app

    try:
        state = build_state_from_env()
    except RuntimeError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2)

    if no_verify_signature:
        state.validate_signature = False
        typer.echo("WARNING: Twilio signature validation DISABLED.")

    typer.echo(f"Allowed senders: {sorted(state.allowed)}")
    typer.echo(f"Twilio number:   {state.twilio_number}")
    base = state.public_base_url or f"http://{host}:{port}"
    typer.echo(f"Webhook URL:     {base.rstrip('/')}/sms  (set this in Twilio console)")
    if not state.public_base_url:
        typer.echo("Tip: set SMS_PUBLIC_BASE_URL to your ngrok https URL for signature validation.")

    uvicorn.run(create_app(state), host=host, port=port)


@app.command("call-template")
def call_template(
    target_number: str = typer.Option(..., "--target-number"),
    default_mode: InjectionMode = typer.Option(InjectionMode.DTMF, "--default-mode"),
    style: TemplateStyle = typer.Option(TemplateStyle.PRO_AUDIO_WORKSTATION, "--style"),
    field: list[str] = typer.Option(
        [],
        "--field",
        help="Placeholder field in the form key=value. Repeat for multiple fields.",
    ),
    field_mode: list[str] = typer.Option(
        [],
        "--field-mode",
        help="Per-field mode override in the form key=dtmf|mixed. Repeat for multiple fields.",
    ),
    export: Path | None = typer.Option(
        None,
        "--export",
        help="Write the template plan to a text file.",
    ),
    render_wav: Path | None = typer.Option(
        None,
        "--render-wav",
        help="Render a placeholder beep WAV for the template plan.",
    ),
) -> None:
    parsed_fields: dict[str, str] = {}
    for item in field:
        if "=" not in item:
            typer.echo(f"Invalid field entry: {item!r}. Expected key=value.")
            raise typer.Exit(code=2)
        key, value = item.split("=", 1)
        key = key.strip()
        if not key or not value:
            typer.echo(f"Invalid field entry: {item!r}. Expected key=value.")
            raise typer.Exit(code=2)
        parsed_fields[key] = value

    try:
        parsed_modes = parse_mode_overrides(field_mode)
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2)

    plan = build_call_template_plan(
        target_number=target_number,
        fields=parsed_fields,
        default_mode=default_mode,
        style=style,
        mode_overrides=parsed_modes,
    )

    if export is not None:
        export.parent.mkdir(parents=True, exist_ok=True)
        export.write_text(plan.to_text(), encoding="utf-8")

    if render_wav is not None:
        plan.render_beep_wav(render_wav)

    typer.echo(json.dumps(plan.as_dict(), indent=2, sort_keys=True))


@app.command("batch-template")
def batch_template(
    config: Path = typer.Option(
        ...,
        "--config",
        help="Path to a JSON config with base_fields and entries.",
    ),
    default_mode: InjectionMode = typer.Option(InjectionMode.DTMF, "--default-mode"),
    style: TemplateStyle = typer.Option(TemplateStyle.PRO_AUDIO_WORKSTATION, "--style"),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Optional path to write the JSON result. Always echoed to stdout.",
    ),
) -> None:
    """Run a template against multiple entries sequentially and emit JSON transcripts."""
    if not config.exists():
        typer.echo(f"Config file not found: {config}")
        raise typer.Exit(code=2)

    try:
        payload = json.loads(config.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        typer.echo(f"Invalid JSON in {config}: {exc}")
        raise typer.Exit(code=2)

    base_fields_raw = payload.get("base_fields") or {}
    if not isinstance(base_fields_raw, dict):
        typer.echo("base_fields must be a JSON object")
        raise typer.Exit(code=2)
    base_fields = {str(key): str(value) for key, value in base_fields_raw.items()}

    entries_raw = payload.get("entries") or []
    if not isinstance(entries_raw, list):
        typer.echo("entries must be a JSON array")
        raise typer.Exit(code=2)

    try:
        entries = batch_entries_from_payload(entries_raw)
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2)

    if not entries:
        typer.echo("No entries provided")
        raise typer.Exit(code=2)

    result = run_batch_template(
        base_fields=base_fields,
        entries=entries,
        default_mode=default_mode,
        style=style,
    )
    blob = json.dumps(result.as_dict(), indent=2, sort_keys=True)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(blob, encoding="utf-8")
    typer.echo(blob)


@app.command("test-suite")
def test_suite_command(
    suite: Path = typer.Option(..., "--suite", help="Path to a JSON test suite file"),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Optional directory to write results. Defaults to ~/.ivr_assessor/reports.",
    ),
) -> None:
    """Run a test suite from a JSON file and generate transcript reports."""
    from .test_suite import run_test_suite_from_file, save_suite_result

    if not suite.exists():
        typer.echo(f"Suite file not found: {suite}")
        raise typer.Exit(code=2)

    try:
        result = run_test_suite_from_file(suite)
    except Exception as exc:
        typer.echo(f"Error running test suite: {exc}")
        raise typer.Exit(code=2)

    json_path, md_path = save_suite_result(result, output_dir=output)
    typer.echo("Results saved:")
    typer.echo(f"  JSON: {json_path}")
    typer.echo(f"  Markdown: {md_path}")
    typer.echo(f"\nSummary: {result.passed_cases}/{result.total_cases} cases passed")


@app.command("test-suite-wizard")
def test_suite_wizard(
    output: Path = typer.Option(..., "--output", help="Path to save the generated JSON suite"),
) -> None:
    """Interactive wizard to build a test suite without writing JSON."""
    typer.echo("🧪 Test Suite Wizard")
    typer.echo("Let's build a fill-in-the-blanks test suite.\n")

    suite_name = typer.prompt("Suite Name", default="My Test Suite")
    suite_target = typer.prompt("Default Target Number", default="+18005550199")

    cases = []
    while True:
        typer.echo(f"\n--- Adding Case #{len(cases) + 1} ---")
        case_name = typer.prompt("Case Name", default=f"Case {len(cases) + 1}")

        target = typer.prompt("Target Number (leave blank to use suite default)", default="")
        if not target.strip():
            target = suite_target

        path_str = typer.prompt("Initial DTMF Path (comma separated digits, or leave blank)", default="")
        initial_path = [p.strip() for p in path_str.split(",") if p.strip()]

        triggers = []
        while True:
            add_trigger = typer.confirm(f"Add a trigger to '{case_name}'?", default=True)
            if not add_trigger:
                break

            phrase = typer.prompt("When the IVR says (phrase)")
            response = typer.prompt("Respond with")
            kind = typer.prompt("Response kind (dtmf or speech)", default="dtmf")

            triggers.append({
                "phrase": phrase,
                "response": response,
                "kind": kind
            })

        cases.append({
            "name": case_name,
            "target_number": target,
            "initial_path": initial_path,
            "triggers": triggers
        })

        add_case = typer.confirm("\nAdd another test case?", default=False)
        if not add_case:
            break

    suite = {"name": suite_name, "target_number": suite_target, "cases": cases}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(suite, indent=2), encoding="utf-8")
    typer.echo(f"\n✅ Saved test suite to {output}")
    typer.echo(f"Run it with: ivr-assessor test-suite --suite {output}")


@app.command("voice-generate")
def voice_generate(
    text: str = typer.Option(..., "--text"),
    out: Path = typer.Option(..., "--out"),
    voice: str = typer.Option("nova", "--voice", help="TTS voice (e.g., alloy, echo, fable, onyx, nova, shimmer)"),
    style: TemplateStyle = typer.Option(TemplateStyle.PRO_AUDIO_WORKSTATION, "--style"),
    model: str = typer.Option("tts-1-hd", "--model", help="Use tts-1-hd for higher quality audio"),
    response_format: str = typer.Option("wav", "--response-format"),
) -> None:
    spec = VoiceGenerationSpec(
        text=text,
        voice=voice,
        style=style,
        model=model,
        response_format=response_format,
    )
    try:
        generate_voice_file(spec, out)
    except Exception as exc:
        typer.echo(f"Unable to generate voice: {exc}")
        raise typer.Exit(code=1)
    typer.echo(str(out))


def _parse_response_clips(entries: list[str]) -> list[ResponseClip]:
    """Parses 'label=filepath' strings into ResponseClip objects."""
    clips = []
    for item in entries:
        if "=" not in item:
            typer.echo(f"Warning: Skipping invalid response clip entry: {item!r}", err=True)
            continue
        label, path_str = item.split("=", 1)
        path = Path(path_str)
        if not path.exists():
            typer.echo(f"Warning: Response clip file not found: {path}", err=True)
            continue

        # Create a simple ID and assume duration.
        clip = ResponseClip(
            id=f"custom-{label}",
            label=label.strip(),
            file_path=path,
            style="custom",
            duration_ms=2000,  # Placeholder
        )
        clips.append(clip)
    return clips


def _build_response_library(
    response_label: str,
    response_style: str | None,
    custom_clips: list[str],
) -> ResponseLibrary:
    """Builds a response library merging default clips for the label with any custom clips."""
    default_clips = build_default_response_library(response_label, response_style=response_style).clips
    parsed_custom = _parse_response_clips(custom_clips)
    return ResponseLibrary(clips=default_clips + parsed_custom)


def _get_clients_for_mode(
    mode: str,
    prompt: list[str],
    twilio_sid: str | None,
    twilio_token: str | None,
    twilio_number: str | None,
    user_phone_number: str | None = None,
) -> tuple[TelephonyClient, object]:
    """Selects the telephony client and prompt source based on the run mode."""
    if mode == "interactive":
        try:
            from .twilio_client import TwilioTelephonyClient

            telephony = TwilioTelephonyClient(
                account_sid=twilio_sid,
                auth_token=twilio_token,
                twilio_number=twilio_number,
                user_phone_number=user_phone_number,
            )
            prompt_source = InteractivePromptSource()
            typer.echo("Using Twilio for live call in interactive mode.", err=True)
            return telephony, prompt_source
        except (ImportError, ValueError) as e:
            typer.echo(f"Error setting up Twilio client: {e}", err=True)
            raise typer.Exit(code=1)

    # Default to scripted mode for simulation
    telephony = RecordingTelephonyClient()
    prompt_source = ScriptedPromptSource(
        [
            CallEvent(kind="prompt", text=text, t_ms=index * 250)
            for index, text in enumerate(prompt)
        ]
    )
    return telephony, prompt_source


def _run_single_session(
    target_number: str,
    response_mode: str,
    prompt: list[str],
    response_label: str,
    response_style: str | None,
    response_clip: list[str],
    mode: str,
    twilio_account_sid: str | None,
    twilio_auth_token: str | None,
    twilio_phone_number: str | None,
    user_phone_number: str | None = None,
) -> object:
    telephony, prompt_source = _get_clients_for_mode(
        mode=mode,
        prompt=prompt,
        twilio_sid=twilio_account_sid,
        twilio_token=twilio_auth_token,
        twilio_number=twilio_phone_number,
        user_phone_number=user_phone_number,
    )
    response_library = _build_response_library(
        response_label=response_label,
        response_style=response_style,
        custom_clips=response_clip,
    )
    session = LiveMappingSession(
        target_number=target_number,
        response_mode=response_mode,
        prompt_source=prompt_source,
        telephony=telephony,
        response_library=response_library,
        response_label=response_label,
        response_style=response_style,
    )
    return session.run()


def _run_multi_session(
    target_numbers: list[str],
    response_mode: str,
    prompt: list[str],
    response_label: str,
    response_style: str | None,
    response_clip: list[str],
) -> dict[str, object]:
    telephony = RecordingTelephonyClient()
    orchestrator = MultiSessionOrchestrator()
    response_library = _build_response_library(
        response_label=response_label,
        response_style=response_style,
        custom_clips=response_clip,
    )

    for index, target in enumerate(target_numbers):
        prompt_source = ScriptedPromptSource(
            [
                CallEvent(kind="prompt", text=text, t_ms=event_index * 250)
                for event_index, text in enumerate(prompt)
            ]
        )
        session = LiveMappingSession(
            target_number=target,
            response_mode=response_mode,
            prompt_source=prompt_source,
            telephony=telephony,
            response_library=response_library,
            response_label=response_label,
            response_style=response_style,
        )
        summary = session.run()
        orchestrator.start_session(summary.session_id or f"session-{index + 1}", target)
        for event in summary.events:
            orchestrator.record_event(
                summary.session_id or f"session-{index + 1}",
                CallEvent(**event),
                branch_confidence=0.8,
            )

    return {
        "session_mode": "multi-session",
        "session_index": orchestrator.session_index(),
        "graph": orchestrator.combined_graph(),
    }


def main() -> None:
    app()


if __name__ == "__main__":
    main()