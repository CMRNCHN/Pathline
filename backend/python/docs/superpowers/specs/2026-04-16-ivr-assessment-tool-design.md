# IVR Assessment Tool Design

## Goal
Build a local, authorized IVR assessment tool for business-owned phone numbers that can:

- place outbound test calls
- capture IVR prompts and call timing
- inject DTMF sequences with configurable timing
- play prebuilt spoken response clips during the call
- adapt to observed IVR behavior in real time within operator-approved bounds
- map observed menu paths into a navigable IVR tree
- generate a concise findings report for security review

The tool is for permissioned testing only. It must not support impersonation, stealth, credential guessing, unrestricted targeting, or any other abuse-oriented behavior.

## Non-Goals

- no live voice synthesis
- no “sound like a real person” voice masking
- no brute-force PIN, account, or password guessing
- no automated bypass logic for undocumented security controls
- no multi-tenant SaaS platform in the first version
- no unrestricted target discovery

## User Workflow

1. The tester defines an allowlisted target number and a call plan.
2. The tester selects a response script with blank-style variables such as `{account_type}` or `{zip_code}`.
3. The tester chooses one or more prebuilt audio clips for each response slot.
4. The tool places the call and begins listening for prompts.
5. When the IVR asks for input, the tool either sends DTMF or plays the selected audio clip.
6. The tool records prompt text, timestamps, branch changes, and call outcomes.
7. After the call, the tool exports a menu map and report.

## Proposed Architecture

### 1. Execution Controller
Responsible for coordinating the call session, adaptive branching, and operator-defined execution scope.

Inputs:

- target number
- call budget
- timeout limits
- test plan
- operator-approved bounds

Outputs:

- call state events
- call end reason
- session identifier
- execution metrics

### 2. Adaptive Scenario Runner
Responsible for driving the call using a baseline plan plus live decisioning.

Responsibilities:

- choose the next action from current IVR state
- react to observed prompt changes
- retry or branch within configured bounds
- preserve the action history for replay

Supported actions:

- `send_dtmf`
- `play_clip`
- `wait`
- `end_call`

### 3. Event Ledger
Responsible for capturing every observable and chosen interaction during a call.

Responsibilities:

- store prompts, actions, branches, retries, and timing
- store prompt audio snippets
- timestamp prompt boundaries
- retain transcript text when available
- mark uncertain prompts for later review
- preserve replayable session history

### 4. DTMF Injector
Responsible for sending touch-tone sequences with explicit pacing.

Capabilities:

- configurable per-digit delay
- configurable post-prompt wait time
- bounded retry count
- no hidden or adaptive guessing behavior

### 5. Response Library
Responsible for storing and retrieving prebuilt spoken responses.

Library model:

- clip files: WAV or MP3
- labels: `billing`, `support`, `account_type`, `zip_code`
- style tags: `calm`, `professional`, `friendly`, `concise`
- optional variable bindings: `{account_type}`, `{state}`, `{zip_code}`

The tool should support fill-in-the-blank script entries such as:

- `If the IVR asks for account type, play clip "account_type_regular_customer.wav".`
- `If the IVR asks for ZIP code confirmation, play clip "zip_code_10001.wav".`

### 6. Prompt Intelligence Layer
Responsible for classifying prompts and interpreting them in context.

Responsibilities:

- classify prompt type
- detect likely intent from prompt text, audio features, and prior state
- score confidence for candidate actions
- expose the decision context to the scenario runner

### 7. Exploration Engine
Responsible for exploring unknown IVR paths in a controlled way.

Responsibilities:

- propose alternative branches based on prior observations
- choose among candidate actions using confidence and operator settings
- expand coverage across sessions
- respect depth, time, and retry bounds

### 8. IVR Mapper
Responsible for building the menu tree from observed call behavior.

It should track:

- prompt text or nearest transcript approximation
- selected input
- resulting branch
- transfer events
- timeout behavior
- invalid-input behavior
- branch confidence
- session provenance

### 9. Reporter
Responsible for producing a test summary.

Required outputs:

- chronological call timeline
- IVR tree or adjacency list
- clip playback log
- DTMF event log
- notable findings
- anomalies
- discovered paths
- system behaviors
- unanswered prompts
- suggested follow-up tests

## Data Model

### CallPlan

- `target_number`
- `max_depth`
- `max_attempts`
- `dtmf_timeout_ms`
- `response_mode` with values `dtmf`, `clip`, or `mixed`
- `allowed_branches`
- `exploration_budget`
- `confidence_threshold`

### ResponseClip

- `id`
- `label`
- `file_path`
- `style`
- `duration_ms`
- `tags`

### ScriptStep

- `trigger`
- `action`
- `payload`
- `confidence_threshold`

Example actions:

- `send_dtmf`
- `play_clip`
- `wait`
- `end_call`

### IVRNode

- `prompt_signature`
- `observed_text`
- `input_used`
- `children`
- `terminal_state`

## Control Flow

1. Load a call plan and response library.
2. Dial an allowlisted number.
3. Capture the first prompt.
4. Classify the prompt and score candidate next actions.
5. Select the next action using the adaptive scenario runner.
6. Execute DTMF or playback.
7. Observe the next prompt or branch result.
8. Update the IVR graph and exploration history.
9. Repeat until the plan ends, the maximum depth is reached, or the call ends.
10. Persist artifacts and generate the final report.

## Error Handling

The tool should fail safely and visibly.

- If a prompt cannot be recognized, log it as uncertain and pause for operator review.
- If a clip is missing or corrupted, stop playback and record a media error.
- If the call times out, preserve the last known state and close the session cleanly.
- If the target is not on the allowlist, refuse to dial.
- If the script requests too many retries, stop the call instead of continuing.
- If exploration confidence is too low, pause for operator review.

## Security and Safety Guardrails

- allowlist enforcement for every target number
- explicit operator confirmation before dialing
- fixed retry ceilings
- no credential harvesting logic
- no identity spoofing or voice impersonation
- no stealth or evasion features
- audit log for every action taken during a call
- operator-configurable exploration bounds

## Testing Plan

### Unit Tests

- response-variable substitution
- clip selection rules
- DTMF timing generation
- IVR tree updates
- allowlist enforcement
- prompt classification scoring
- exploration budget enforcement

### Integration Tests

- replay a known IVR trace and verify the same branch path is reconstructed
- validate clip playback events are logged in the right order
- confirm timeout and invalid-input handling
- verify adaptive branching chooses alternate paths when prompts change

### Manual Verification

- dry-run mode that prints the full call plan without dialing
- operator review of the generated IVR map after a test call

## Implementation Phases

### Phase 1

- build the CLI
- implement allowlist checks
- add call planning and dry-run mode
- add DTMF injection
- add execution controller and event ledger

### Phase 2

- add prompt capture and transcript storage
- add the response library
- add clip playback during calls
- add prompt intelligence layer

### Phase 3

- add IVR tree mapping
- add exploration engine
- add reporting
- add replay-based tests

## Open Questions

- Assumption: local-first storage for call artifacts, with JSON or CSV export for reports.
- Which call transport will we use first?
- Which telephony provider should the tool integrate with?
- Should the first version store clips by filesystem path, or also support tagging and search?
- What operator-configurable exploration limits should be exposed in v1?
