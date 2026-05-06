# cspell:ignore deepgram autouse caplog endpointing

import asyncio
import logging
from typing import Any

import pytest

from ivr_assessor import transcription as tx
from ivr_assessor.transcription import DeepgramTranscriber


class _FakeResults:
    """Duck-typed stand-in for any Deepgram streaming result shape."""

    def __init__(self, transcript: str, is_final: bool = False, speech_final: bool = False):
        alt = type("A", (), {"transcript": transcript})()
        self.channel = type("C", (), {"alternatives": [alt]})()
        self.is_final = is_final
        self.speech_final = speech_final


class _FakeSocket:
    def __init__(self, scripted_messages: list[Any]):
        self._messages = list(scripted_messages)
        self.sent: list[bytes] = []
        self.closed = False

    def __aiter__(self):
        async def gen():
            for msg in self._messages:
                await asyncio.sleep(0)
                yield msg
        return gen()

    async def send_media(self, data: bytes) -> None:
        self.sent.append(data)

    async def send_close_stream(self) -> None:
        self.closed = True


class _FakeConnectCM:
    def __init__(self, socket: _FakeSocket, accept_when):
        self._socket = socket
        self._accept_when = accept_when
        self._kwargs: dict[str, Any] = {}

    def __call__(self, **kwargs):
        self._kwargs = kwargs
        return self

    async def __aenter__(self):
        if not self._accept_when(self._kwargs):
            raise ValueError(f"rejected kwargs: {self._kwargs}")
        return self._socket

    async def __aexit__(self, *args):
        return None


class _FakeListenV1:
    def __init__(self, cm: _FakeConnectCM):
        self.connect = cm


class _FakeListen:
    def __init__(self, cm: _FakeConnectCM):
        self.v1 = _FakeListenV1(cm)


class _FakeClient:
    def __init__(self, cm: _FakeConnectCM):
        self.listen = _FakeListen(cm)


def _install_fake(monkeypatch: pytest.MonkeyPatch, accept_when, messages: list[Any]) -> _FakeSocket:
    socket = _FakeSocket(messages)
    cm = _FakeConnectCM(socket, accept_when)
    client = _FakeClient(cm)

    def make_transcriber(**kwargs):
        t = DeepgramTranscriber(**kwargs)
        t._client = client
        return t

    DeepgramTranscriber._learned_connect_params = None
    DeepgramTranscriber._learned_model = None
    monkeypatch.setattr(tx, "_make_test_transcriber", make_transcriber, raising=False)
    return socket


@pytest.fixture(autouse=True)
def _reset_class_state():
    DeepgramTranscriber._learned_connect_params = None
    DeepgramTranscriber._learned_model = None
    yield
    DeepgramTranscriber._learned_connect_params = None
    DeepgramTranscriber._learned_model = None


@pytest.fixture(autouse=True)
def _enable_debug_logs(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.DEBUG, logger="ivr_assessor.transcription")


def _build_transcriber(client, messages_results: list[Any] | None = None) -> DeepgramTranscriber:
    t = DeepgramTranscriber()
    t._client = client
    return t


def test_connect_succeeds_on_first_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    socket = _FakeSocket([_FakeResults("hello world", is_final=True, speech_final=True)])
    cm = _FakeConnectCM(socket, accept_when=lambda kw: True)
    client = _FakeClient(cm)
    transcripts: list[tuple[str, bool, bool]] = []
    t = DeepgramTranscriber(on_transcript=lambda s, f, sf: transcripts.append((s, f, sf)))
    t._client = client

    async def go():
        assert await t.connect() is True
        await asyncio.sleep(0.05)
        assert t._connect_attempts == 1
        await t.close()

    asyncio.run(go())
    assert transcripts == [("hello world", True, True)]
    assert DeepgramTranscriber._learned_model == "nova-3"


def test_autofix_walks_until_a_variant_accepts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject the first three string-bool variants until native bools are tried."""
    socket = _FakeSocket([])

    def accept(kwargs: dict[str, Any]) -> bool:
        return kwargs.get("smart_format") is True and kwargs.get("interim_results") is True

    cm = _FakeConnectCM(socket, accept_when=accept)
    client = _FakeClient(cm)
    t = DeepgramTranscriber()
    t._client = client

    async def go():
        assert await t.connect() is True
        await t.close()

    asyncio.run(go())
    assert t._connect_attempts >= 2
    learned = DeepgramTranscriber._learned_connect_params
    assert learned is not None
    assert learned.get("smart_format") is True
    assert learned.get("interim_results") is True


def test_autofix_falls_back_to_alternate_model(monkeypatch: pytest.MonkeyPatch) -> None:
    socket = _FakeSocket([])
    cm = _FakeConnectCM(socket, accept_when=lambda kw: kw.get("model") == "nova-2")
    client = _FakeClient(cm)
    t = DeepgramTranscriber()
    t._client = client

    async def go():
        assert await t.connect() is True
        await t.close()

    asyncio.run(go())
    assert DeepgramTranscriber._learned_model == "nova-2"


def test_connect_returns_false_when_all_variants_fail() -> None:
    cm = _FakeConnectCM(_FakeSocket([]), accept_when=lambda kw: False)
    client = _FakeClient(cm)
    statuses: list[str] = []
    t = DeepgramTranscriber(on_status=statuses.append)
    t._client = client

    async def go():
        assert await t.connect() is False

    asyncio.run(go())
    assert t._connect_attempts > 4
    assert any("all connect variants failed" in s for s in statuses)


def test_learned_params_skip_probe_on_second_connect() -> None:
    socket = _FakeSocket([])
    cm = _FakeConnectCM(socket, accept_when=lambda kw: kw.get("smart_format") is True)
    client = _FakeClient(cm)

    async def go():
        first = DeepgramTranscriber()
        first._client = client
        assert await first.connect() is True
        await first.close()
        first_attempts = first._connect_attempts

        second = DeepgramTranscriber()
        second._client = client
        assert await second.connect() is True
        await second.close()
        return first_attempts, second._connect_attempts

    first_attempts, second_attempts = asyncio.run(go())
    assert first_attempts > 1
    assert second_attempts == 1


def test_stats_track_frames_and_messages() -> None:
    socket = _FakeSocket(
        [_FakeResults("hi"), _FakeResults("there", is_final=True)]
    )
    cm = _FakeConnectCM(socket, accept_when=lambda kw: True)
    client = _FakeClient(cm)
    t = DeepgramTranscriber()
    t._client = client

    async def go():
        await t.connect()
        await t.process_audio(b"\x00" * 160)
        await t.process_audio(b"\x00" * 160)
        await asyncio.sleep(0.05)
        await t.close()

    asyncio.run(go())
    s = t.stats()
    assert s["frames_sent"] == 2
    assert s["bytes_sent"] == 320
    assert s["messages_received"] == 2
    assert s["transcripts_emitted"] == 2
    assert s["connected"] is False


def test_debug_logging_emits_lifecycle_events(caplog: pytest.LogCaptureFixture) -> None:
    socket = _FakeSocket([_FakeResults("logged", is_final=False)])
    cm = _FakeConnectCM(socket, accept_when=lambda kw: True)
    client = _FakeClient(cm)
    t = DeepgramTranscriber()
    t._client = client

    async def go():
        await t.connect()
        await t.process_audio(b"\x01" * 160)
        await asyncio.sleep(0.05)
        await t.close()

    asyncio.run(go())
    log_text = "\n".join(record.message for record in caplog.records)
    assert "connect attempt 1" in log_text
    assert "send #1" in log_text
    assert "transcript #1" in log_text
    assert "close: frames_sent=1" in log_text


def test_is_final_and_speech_final_emitted_separately() -> None:
    """is_final and speech_final must reach the callback as distinct flags so
    the GUI can buffer chunks until endpointing fires."""
    socket = _FakeSocket(
        [
            _FakeResults("thank you for calling", is_final=True, speech_final=False),
            _FakeResults("acme corp press 1 for sales", is_final=True, speech_final=True),
        ]
    )
    cm = _FakeConnectCM(socket, accept_when=lambda kw: True)
    client = _FakeClient(cm)
    received: list[tuple[str, bool, bool]] = []
    t = DeepgramTranscriber(on_transcript=lambda s, f, sf: received.append((s, f, sf)))
    t._client = client

    async def go():
        await t.connect()
        await asyncio.sleep(0.05)
        await t.close()

    asyncio.run(go())
    assert received == [
        ("thank you for calling", True, False),
        ("acme corp press 1 for sales", True, True),
    ]


def test_endpointing_param_is_passed_to_connect() -> None:
    socket = _FakeSocket([])
    captured: dict[str, Any] = {}

    def accept(kwargs: dict[str, Any]) -> bool:
        captured.update(kwargs)
        return True

    cm = _FakeConnectCM(socket, accept_when=accept)
    client = _FakeClient(cm)
    t = DeepgramTranscriber()
    t._client = client

    async def go():
        await t.connect()
        await t.close()

    asyncio.run(go())
    assert captured.get("endpointing") == 500


def test_duck_types_dict_shaped_messages() -> None:
    """If a future SDK returns dicts instead of typed objects, transcripts
    should still flow."""
    raw_dict_message = {
        "channel": {"alternatives": [{"transcript": "from a dict"}]},
        "is_final": True,
        "speech_final": True,
    }
    socket = _FakeSocket([raw_dict_message])
    cm = _FakeConnectCM(socket, accept_when=lambda kw: True)
    client = _FakeClient(cm)
    received: list[tuple[str, bool, bool]] = []
    t = DeepgramTranscriber(on_transcript=lambda s, f, sf: received.append((s, f, sf)))
    t._client = client

    async def go():
        await t.connect()
        await asyncio.sleep(0.05)
        await t.close()

    asyncio.run(go())
    assert received == [("from a dict", True, True)]


def test_process_audio_without_connect_is_safe(caplog: pytest.LogCaptureFixture) -> None:
    t = DeepgramTranscriber()

    async def go():
        await t.process_audio(b"\x00" * 160)

    asyncio.run(go())
    assert t.stats()["frames_sent"] == 0
    assert any("no socket" in r.message for r in caplog.records)
