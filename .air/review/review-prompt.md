Please perform a strict engineering review of the current IVRSuite changeset.

Focus on:

1. Code Quality

* assess maintainability
* assess readability
* identify coupling risks
* identify growing god-objects
* identify architectural drift
* identify hidden complexity
* identify ownership ambiguity

2. Correctness

* verify runtime behavior assumptions
* verify async coordination correctness
* verify websocket behavior correctness
* verify replay assumptions
* verify VAD/STT/TTS pipeline correctness
* verify queue/backpressure handling
* verify tunnel lifecycle handling
* verify startup orchestration correctness

3. Bugs / Runtime Risks

* race conditions
* deadlocks
* dropped frames
* websocket desync
* replay fidelity gaps
* transcript duplication
* stale state issues
* resource leaks
* subprocess cleanup issues
* tunnel restart edge cases
* invalid async usage
* ordering assumptions

4. Security

* exposed secrets risk
* unsafe logging
* PAN leakage risk
* insecure temp files
* unsafe subprocess handling
* replay artifact leakage
* webhook validation issues
* tunnel exposure risks
* filesystem traversal risks
* unsafe environment handling

5. Best Practices

* Python async correctness
* websocket ownership clarity
* explicit state ownership
* deterministic runtime behavior
* replayability preservation
* bounded queues
* explicit cleanup
* test isolation
* modular boundaries
* logging consistency
* operational observability

6. Tests
    Identify:

* missing edge-case tests
* missing async tests
* websocket lifecycle tests
* reconnect tests
* replay integrity tests
* queue pressure tests
* interruption/barging tests
* startup race-condition tests
* tunnel restart tests
* storage persistence tests

7. Documentation
    Review:

* HANDOFF.md
* PROJECT_STATE.md
* AIR_RULES.md
* NEXT_SESSION.md
* README.md

Identify:

* outdated assumptions
* missing operational docs
* missing startup docs
* missing smoke-test docs
* missing replay docs
* missing troubleshooting guidance
* missing architecture ownership documentation

Important constraints:

* preserve deterministic runtime behavior
* preserve replay semantics
* preserve websocket semantics
* avoid speculative redesign
* avoid unnecessary abstractions
* do not recommend frameworks
* do not recommend orchestration platforms
* do not recommend generalized event systems yet

This review should prioritize:
runtime correctness,
operational reliability,
replay fidelity,
observability,
and maintainability under long-term AI-assisted development.

At the end provide:

* Critical Issues
* High Priority Improvements
* Medium Priority Improvements
* Low Priority Improvements
* Recommended Next Engineering Priority
* Architectural Risk Summary