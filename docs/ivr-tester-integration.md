# ivr-tester Integration

Pathline ports phrase-matching logic from the upstream [ivr-tester](https://github.com/SketchingDev/ivr-tester)
repository while keeping Pathline's client-mediated privacy boundary.

## What was ported

| ivr-tester module | Pathline location | Notes |
|-------------------|-------------------|-------|
| `when/contains`, `similarTo`, `containsSimilarTo` | `client/src/engine/when/` | Composable predicates |
| `when/matches`, `and`, `or`, `hasPart` | `client/src/engine/when/` | Same semantics |
| Pipe-OR detect strings | `evaluateDetect()` | Backward compatible |
| Structured `and`/`or` detect JSON | `evaluateDetect()` / script sync | Nested JSON predicates |
| Fuzzy matching | `~phrase` detect prefix | New opt-in syntax |
| Regex matching | `regex:/pattern/flags` | New opt-in syntax |
| DTMF `w` pauses | `client/src/dtmf/dtmf.ts` + native bridge | `w` waits 500 ms; not sent as a digit |

Pathline's `runEngine.ts` now calls `evaluateDetect()` instead of inline substring logic.

## What stays in ivr-tester only

- Twilio orchestration (server-mediated exception path)
- Cloud transcriber plugins (Google STT, Amazon Transcribe)
- ngrok-based public WebSocket server

These conflict with Pathline v1's client-mediated model and should not become Pathline defaults.

## Hardening applied upstream

The ivr-tester repo now includes Pathline-aligned controls for its server-mediated mode:

- Ephemeral session tokens on media stream URLs
- Scenario ID correlation for parallel runs
- Outbound consent gate
- Redacted telephony debug logs
- Safe recording paths

See ivr-tester `docs/threat-model.md`.

## Detect string syntax (Pathline)

| Form | Meaning |
|------|---------|
| `enter pin` | Case-insensitive substring |
| `pin\|password` | Any alternative matches |
| `{"and":["account",{"or":["balance","status"]}]}` | Nested structured predicates |
| `{"regex":"account \\d+","flags":"i"}` | Structured regular expression |
| `~enter pin` | Fuzzy substring match (default threshold 0.8) |
| `~0.9:enter pin` | Fuzzy match with custom threshold |
| `regex:/pin \\d+/i` | Regular expression |

Special tokens `__next_utterance__` and `__end_now__` are unchanged.
Wait Steps compile to `__wait_N__` and are completed by the run engine after
the prior Step is done. Automated runs also fail closed with a clear timeout
outcome when the next expected Step does not match within its Step timeout (or
the Path setup timeout).

## DTMF pause syntax

Pathline now preserves ivr-tester-style `w` pauses in key sequences:

```text
1234w#
```

The client waits 500 ms for each `w`; the native bridge also honors `w` if a
sequence reaches it directly. Ledgers store a hash and real digit count only,
so pause markers are not counted as keypad digits.

## Future work

- ~~Port `PostSilencePrompt` silence-after-match timing~~ — implemented via `PhraseIngressGate`
- ~~Vault-bound run variables~~ — Account profile resolution at run start
- ~~Encrypted local recordings + auto-purge~~ — `encryptedRecordingStore.ts`
- ~~Compile structured JSON when specs in Path script sync (like ivr-tester CLI)~~ — nested `and`/`or`, contains, fuzzy, and regex are implemented.
- Keep audit ledger free of transcript text (already enforced in STT fixture)
