# Review / Replay / Analysis Backend Semantics Plan

Status: planning only  
Date: 2026-05-13  
Authoritative anchor: `.ai/plans/ivr-phase-operations-anchor.md`

## Purpose

Define safe future backend semantics for Review / Replay / Analysis without changing live runtime behavior. This plan uses the completed replay/review audit as source input and remains subordinate to the phase-oriented operations anchor.

## Non-Authorization

This plan does not authorize implementation. It does not authorize:

- Runtime hot-path changes.
- WebSocket or protocol changes.
- Replay semantic changes.
- Topology changes.
- Storage migration.
- Live traversal steering.
- Autonomous route refinement.
- Hidden orchestration or AI-driven routing.

Replay remains deterministic post-run reconstruction. Route refinement remains operator-reviewed and evidence-based. Frontend refinement cues remain advisory unless backed by explicit backend verdict semantics. Duplicate merging must preserve evidence and lineage. Suite extraction must not mutate live traversal behavior.

## Source Audit Baseline

Supported today:

- `replay_mode.replay_trace` can reconstruct a trace into events, graph, report, and summary.
- `inspection.inspect_replay_artifact` can summarize chronology, DTMF path, first/last prompt, largest gap, and non-monotonic notes.
- Runtime diagnostics expose session chronology, queue visibility, checkpoint chronology, artifact counts, and WebSocket lifecycle diagnostics.
- Frontend review surfaces can consume runtime diagnostics, call-path replay rows, checkpoint visibility, artifact counts, and advisory route-refinement cues.

Partially supported today:

- Prompt/node relabeling and notes exist conceptually in map storage handlers, but relabel safety and merge semantics are not formalized.
- Checkpoint review is visibility-oriented, not verdict-oriented.
- Artifact inspection exposes counts and recording statuses, not durable artifact provenance.
- Failed traversal analysis is heuristic and frontend-advisory.

Missing today:

- Evidence-preserving duplicate prompt merge semantics.
- Formal checkpoint verdict model.
- Artifact/evidence index with provenance.
- Durable failed traversal taxonomy.
- Replay-to-suite extraction readiness boundary.

## Proposed Backend Domain Model

These are logical backend concepts for later implementation, not immediate storage changes.

### ReviewRun

A read-only post-run review envelope derived from one completed runtime session or replay artifact.

Fields:

- `review_id`: stable identifier for the review envelope.
- `source_type`: `runtime_session`, `replay_trace`, `snapshot`, or `report`.
- `source_ref`: path or internal artifact reference, not raw mutable content.
- `target`: IVR target identifier.
- `created_at`: review envelope creation timestamp.
- `runtime_session_id`: optional source session identifier when available.
- `replay_summary`: event count, prompt count, action count, node count, root prompts, DTMF path, duration.
- `graph_ref`: reference to reconstructed graph snapshot.
- `artifact_index_ref`: reference to evidence index.
- `checkpoint_verdicts_ref`: reference to operator or system checkpoint verdicts.
- `route_refinement_set_ref`: reference to proposed/refined route edits.

Rules:

- A `ReviewRun` is post-run only.
- A `ReviewRun` must not enqueue actions, alter live traversal, or change active session state.
- A `ReviewRun` may point to immutable source artifacts and additive review metadata.

### ReviewNode

A review-time representation of an observed IVR prompt/state node.

Fields:

- `node_id`: stable review-local identifier.
- `canonical_label`: operator-reviewed label.
- `observed_texts`: all source prompt strings associated with this node.
- `source_event_refs`: event references that support the node.
- `lineage`: list of prior node identifiers and labels if relabeled or merged.
- `confidence`: reconstruction or prompt-match confidence from source graph, not a review verdict.
- `notes`: operator notes.
- `merge_status`: `none`, `candidate`, `merged`, or `rejected`.

Rules:

- Relabeling changes `canonical_label`, not source evidence.
- Source prompt texts remain preserved.
- Merges add lineage and aliases; they must not discard branches or event references.

### ReviewEdge

A review-time transition between nodes.

Fields:

- `edge_id`: stable review-local identifier.
- `from_node_id`: source node.
- `response_anchor`: DTMF digit or spoken response.
- `to_node_id`: destination node, if observed.
- `source_event_refs`: action and prompt event references supporting the edge.
- `status`: `observed`, `unresolved`, `loop_candidate`, `dead_end_candidate`, or `operator_rejected`.
- `notes`: operator notes.

Rules:

- Edges represent observed review evidence only.
- Edges must not instruct future traversal unless separately converted into a suite or approved route artifact.

### RouteRefinement

An operator-reviewed proposed change to labels, notes, route grouping, checkpoint interpretation, or suite-readiness metadata.

Fields:

- `refinement_id`: stable identifier.
- `review_id`: parent review envelope.
- `kind`: `relabel_node`, `merge_nodes`, `split_node`, `mark_edge`, `add_note`, `checkpoint_verdict`, `suite_candidate`.
- `status`: `draft`, `proposed`, `accepted`, `rejected`, `superseded`.
- `operator`: optional local operator identifier.
- `created_at` and `decided_at`.
- `evidence_refs`: artifact/event/checkpoint references supporting the change.
- `before`: prior review-visible state.
- `after`: proposed review-visible state.

Rules:

- Refinements are append-only decisions or proposals.
- Accepted refinements affect post-run review views only unless a separate implementation explicitly exports them.
- Refinements are never live traversal instructions.

### CheckpointVerdict

A formal review verdict over an expected state, prompt, artifact, or route position.

Fields:

- `checkpoint_id`: stable checkpoint identifier.
- `review_id`: parent review envelope.
- `checkpoint_type`: `prompt_seen`, `state_reached`, `response_sent`, `artifact_exists`, `recording_complete`, `route_complete`, `custom`.
- `expected`: expected prompt/state/artifact condition.
- `observed`: observed condition summary.
- `verdict`: `pass`, `fail`, `inconclusive`, `not_applicable`, or `not_reviewed`.
- `evidence_refs`: supporting event/artifact refs.
- `reviewed_by`: optional operator identifier.
- `reviewed_at`: timestamp.
- `notes`: operator explanation.

Rules:

- Existing queue/runtime checkpoint visibility is not equivalent to a `pass` verdict.
- Frontend cues may display `not_reviewed` until explicit verdicts exist.
- Automated preclassification may suggest a verdict candidate, but operator acceptance is required for durable review verdicts unless a future plan defines deterministic system verdict rules.

### ArtifactIndexEntry

A read-only provenance record for evidence available to review.

Fields:

- `artifact_id`: stable identifier.
- `review_id`: parent review envelope.
- `artifact_type`: `trace`, `snapshot`, `report`, `recording`, `transcript`, `runtime_metrics`, `runtime_diagnostics`, `map_export`, `suite_report`.
- `path_ref`: local path or internal storage reference.
- `created_at`, `updated_at`, `size_bytes`.
- `source`: generating subsystem or command.
- `content_hash`: optional hash for integrity when practical.
- `session_id`: optional runtime session identifier.
- `recording_sid`: optional Twilio recording SID.
- `preview`: bounded text or metadata preview.

Rules:

- Index entries reference artifacts; they do not rewrite artifacts.
- Missing artifacts are represented explicitly with availability status rather than silently ignored.
- Paths must remain local-first and must not leak secrets.

### FailedTraversalFinding

A classified review finding about incomplete, unexpected, or suspicious traversal behavior.

Fields:

- `finding_id`: stable identifier.
- `review_id`: parent review envelope.
- `category`: taxonomy value from the failed traversal taxonomy.
- `severity`: `info`, `warning`, `error`, or `blocked`.
- `status`: `candidate`, `confirmed`, `dismissed`, or `resolved_in_review`.
- `evidence_refs`: event/checkpoint/artifact refs.
- `summary`: short operator-facing explanation.
- `suggested_review_action`: bounded advisory next step.

Rules:

- Findings are review diagnostics, not live corrective actions.
- Findings may inform route refinement proposals, but operator confirmation is required before durable refinement decisions.

### SuiteExtractionCandidate

A post-run candidate for creating a reusable suite from verified evidence.

Fields:

- `candidate_id`: stable identifier.
- `review_id`: parent review envelope.
- `route_path`: ordered node and edge refs.
- `checkpoint_refs`: checkpoint verdicts required for extraction.
- `artifact_refs`: supporting evidence.
- `readiness`: `not_ready`, `needs_review`, `ready`, or `extracted`.
- `blocking_reasons`: list of missing evidence or unresolved findings.
- `export_preview`: bounded JSON-like suite draft preview.

Rules:

- Candidate generation is post-run only.
- Extraction must create or export a separate suite artifact.
- Extraction must not mutate live traversal behavior, DFS routing, replay behavior, or active runtime state.

## Safe Route Refinement Lifecycle

1. `Observed`: replay/review reconstructs events, graph nodes, edges, chronology, checkpoint visibility, and artifact index.
2. `Candidate`: backend derives bounded candidate findings such as repeated prompt, unresolved branch, missing artifact, or pending checkpoint visibility.
3. `Operator Review`: operator inspects evidence and optionally creates relabel, merge, note, checkpoint verdict, or suite candidate proposals.
4. `Proposed`: proposed refinements are stored as additive metadata with evidence refs and before/after state.
5. `Accepted` or `Rejected`: operator decision finalizes review metadata without mutating source evidence.
6. `Export-Ready`: accepted refinements and passing checkpoint verdicts can mark a route as suite-extraction-ready.
7. `Extracted`: a separate suite artifact may be generated in a later scoped implementation without changing live traversal.

Lifecycle guardrails:

- No lifecycle state may enqueue runtime actions.
- No lifecycle state may modify WebSocket behavior or token auth.
- No lifecycle state may alter replay reconstruction semantics.
- No lifecycle state may silently mutate source traces, recordings, reports, or snapshots.
- Any future persistence must be additive and separately approved.

## Prompt / Node Relabeling Safety

Relabeling rules:

- Relabeling changes only the review-visible `canonical_label`.
- Original prompt text remains in `observed_texts` and source event refs.
- Relabel proposals must include `before`, `after`, operator decision state, and evidence refs.
- Relabeling must not rewrite event ledger text, replay artifact text, recording transcript text, or runtime graph source evidence.
- Empty labels, duplicate canonical labels without explicit merge intent, and labels that erase all distinguishers must be rejected.

Preconditions for later implementation:

- Existing map edit behavior should be reviewed before use because the audited `map_store.edit_node` and `set_node_notes` paths call `save_map` with an unsupported update-only keyword. A scoped bugfix may be required before safe relabeling is exposed.
- Relabel APIs should report success/failure explicitly instead of returning success for no-op or failed edits.

## Duplicate Prompt Merge Rules

Merge eligibility:

- Candidate nodes share equivalent prompt meaning, or the operator explicitly identifies them as the same IVR state.
- Supporting evidence is available for all nodes being merged.
- Branch conflicts are either absent or explicitly resolved.

Merge operation semantics:

- Create a new canonical review node or designate one surviving review node.
- Preserve all original node IDs in lineage.
- Preserve all observed prompt texts as aliases/source texts.
- Union source event refs, artifact refs, notes, and confidence metadata.
- Union branches only when response anchors and destinations are compatible.
- Mark conflicting branches as `conflict_pending`, not silently overwritten.
- Preserve per-source branch counts and observations where available.

Merge rejection cases:

- Two nodes have incompatible response anchors leading to different confirmed states without operator conflict resolution.
- Merge would drop event refs, branch observations, notes, or artifact refs.
- Merge would alter source replay reconstruction output.
- Merge is suggested solely by fuzzy text similarity without operator confirmation.

Post-merge guarantees:

- Original nodes remain recoverable through lineage.
- The merge can be displayed, exported, or reversed in review metadata.
- The merge does not alter live traversal or replay behavior.

## Checkpoint Verdict Model

Verdict values:

- `not_reviewed`: no explicit review decision yet.
- `pass`: expected condition is supported by evidence.
- `fail`: expected condition is contradicted or absent where required.
- `inconclusive`: evidence is incomplete or ambiguous.
- `not_applicable`: checkpoint does not apply to this route/run.

Checkpoint categories:

- Prompt checkpoint: expected prompt or prompt pattern appeared.
- State checkpoint: expected IVR state/node was reached.
- Response checkpoint: expected DTMF/speech response was sent.
- Artifact checkpoint: expected report, recording, replay, snapshot, or transcript exists.
- Timing checkpoint: expected event ordering or bounded duration condition held.
- Route checkpoint: expected route path completed.

Verdict rules:

- A verdict must include evidence refs or an explicit explanation for missing evidence.
- A `pass` verdict requires direct supporting evidence.
- A `fail` verdict should identify the missing, mismatched, or contradicted condition.
- `inconclusive` is preferred over speculative pass/fail when artifacts are missing.
- Frontend advisory cues may map to `not_reviewed` candidates, not durable verdicts.

## Artifact Provenance / Index Model

Index scope:

- Reports, recordings, replay traces, snapshots, runtime metrics, runtime diagnostics, transcripts, map exports, and suite reports.

Index semantics:

- The index is a read-only catalog over existing artifacts and bounded previews.
- The index may contain integrity metadata such as size, mtime, and optional content hash.
- The index should distinguish unavailable, pending, present, malformed, and unreadable artifacts.
- The index should include source subsystem and session association when known.
- The index should avoid storing secrets or raw credentials.

Safety rules:

- Indexing must not move, rename, or rewrite artifacts.
- Indexing must not require a storage migration.
- Indexing must be bounded by file count, preview size, and allowed storage roots.
- Artifact paths should be normalized and path traversal protected before frontend exposure.

## Failed Traversal Taxonomy

Suggested categories:

- `missing_response_anchor`: prompt observed without a following configured/operator response.
- `unresolved_branch`: response sent but no destination prompt observed.
- `unexpected_prompt`: observed prompt does not match expected route context.
- `repeated_prompt_loop`: repeated prompt suggests retry, invalid input, or loop.
- `dead_air_or_timeout`: expected prompt/action gap exceeds bounded review threshold.
- `queue_left_pending`: prompt queue/checkpoint items remained pending at review snapshot.
- `runtime_error`: session ended with explicit backend/runtime error.
- `artifact_missing`: expected evidence artifact is absent.
- `recording_incomplete`: recording artifact missing, pending, failed, or incomplete.
- `non_monotonic_timeline`: event timestamps are not monotonic.
- `map_growth_missing`: prompt activity exists without corresponding reconstructed map growth.
- `checkpoint_failed`: formal checkpoint verdict is `fail`.
- `checkpoint_inconclusive`: formal checkpoint verdict is `inconclusive`.

Classification rules:

- Classifications begin as `candidate` unless deterministically derived from explicit verdicts or errors.
- Severity is bounded and deterministic.
- Suggested actions are review instructions only, such as inspect evidence, confirm branch, relabel node, or mark checkpoint inconclusive.
- Classifiers must not call runtime control APIs or mutate traversal state.

## Replay-to-Suite Extraction Boundary

Readiness requirements:

- Route path is reconstructed from deterministic replay/review evidence.
- Required prompt/state checkpoints are `pass` or explicitly marked `not_applicable`.
- Required artifacts are indexed and available, or missing evidence is accepted by operator policy.
- Duplicate prompt merges and relabels are accepted or explicitly deferred.
- Failed traversal findings are resolved, dismissed, or documented as non-blocking.
- Response anchors are complete for the intended suite path.

Extraction boundary:

- Extraction produces a new suite candidate/export artifact only.
- Extraction does not write to active runtime state.
- Extraction does not alter DFS traversal, replay reconstruction, WebSocket behavior, or map discovery behavior.
- Extraction should be reversible by deleting or ignoring the generated suite artifact.
- Any automatic suite draft must remain operator-reviewed before being treated as a regression suite.

## Later Implementation Slices

Slice 1: Review model types and pure validators

- Add review-domain dataclasses or typed dictionaries in an existing backend/domain location.
- Add pure validation helpers for labels, merges, verdicts, and evidence refs.
- No routes, no persistence, no frontend behavior.

Slice 2: Artifact index builder

- Build bounded read-only index over existing artifact directories.
- Add tests for path safety, missing files, preview limits, and malformed artifacts.
- No storage migration and no artifact rewriting.

Slice 3: Checkpoint verdict records

- Add additive verdict model and pure serialization/deserialization.
- Add tests for pass/fail/inconclusive/not-applicable behavior.
- Keep existing runtime checkpoint visibility unchanged.

Slice 4: Route refinement records

- Add additive proposal/decision records for relabels, notes, and route findings.
- Include lineage and before/after fields.
- Do not modify replay output or live maps in this slice.

Slice 5: Duplicate merge planner

- Add a pure merge planner that returns a proposed merged node and conflict list.
- Require operator acceptance before materializing review metadata.
- Add conflict and no-data-loss tests.

Slice 6: Failed traversal classifier

- Add deterministic post-run classifiers that emit candidate findings.
- Use replay chronology, artifact index, queue visibility, and checkpoint verdicts.
- No runtime control calls.

Slice 7: Suite extraction preview

- Add read-only suite candidate preview from accepted review metadata.
- Require explicit later approval before writing generated suites.
- Do not mutate live traversal behavior.

Slice 8: API exposure and frontend consumption

- Add thin route handlers only after backend semantics and tests exist.
- Keep endpoints review-only and explicit.
- Do not change WebSocket protocol, token auth, or GUI topology.

## Required Tests

Pure model tests:

- Review IDs and refs are stable and serializable.
- Relabel rejects empty labels and preserves original observed text.
- Merge preserves lineage, event refs, artifact refs, notes, and branch observations.
- Merge reports conflicts instead of overwriting incompatible branches.
- Checkpoint verdict validation requires evidence or explanation.
- Artifact index entries reject unsafe paths and bound previews.

Artifact index tests:

- Present, missing, unreadable, malformed, and pending artifacts are classified distinctly.
- Indexing does not write, rename, or move artifacts.
- Local path normalization prevents path traversal.
- Content preview limits are enforced.

Classifier tests:

- Missing response anchor produces `missing_response_anchor` candidate.
- Repeated prompt produces `repeated_prompt_loop` candidate.
- Non-monotonic replay produces `non_monotonic_timeline` candidate.
- Prompt activity without graph growth produces `map_growth_missing` candidate.
- Missing expected artifact produces `artifact_missing` candidate.

Checkpoint tests:

- Prompt/state/response/artifact/timing/route checkpoints support all verdict values.
- Existing queue/runtime checkpoint visibility remains separate from durable verdicts.
- Frontend advisory cue equivalents map to candidates, not durable pass/fail verdicts.

Suite extraction tests:

- Extraction readiness blocks on unresolved failed traversal findings.
- Extraction readiness blocks on missing response anchors.
- Extraction readiness requires accepted or deferred merge/relabel decisions.
- Extraction preview does not mutate runtime state, replay output, or source artifacts.

Regression guard tests:

- `replay_trace` output remains unchanged for existing fixtures.
- `inspect_replay_artifact` output remains backward compatible unless separately approved.
- Existing runtime diagnostics contract remains unchanged unless separately approved.
- No WebSocket tests require protocol updates.

## Risks and Guardrails

Risk: review metadata could be mistaken for runtime instruction.

Guardrail:

- Use explicit names such as `ReviewRun`, `RouteRefinement`, and `SuiteExtractionCandidate`.
- Never expose review records to live traversal code paths without a separate approved bridge.

Risk: duplicate prompt merge could erase evidence.

Guardrail:

- Preserve lineage, source texts, event refs, artifact refs, and branch conflicts.
- Use merge proposals and operator decisions, not silent automatic merges.

Risk: checkpoint visibility could be mislabeled as checkpoint verification.

Guardrail:

- Keep runtime checkpoint visibility distinct from `CheckpointVerdict` records.
- Default to `not_reviewed` until evidence-backed verdicts exist.

Risk: artifact indexing could become a storage migration.

Guardrail:

- Index existing artifacts read-only with bounded previews.
- Do not move or rewrite files.

Risk: failed traversal classification could become autonomous route refinement.

Guardrail:

- Findings are candidates with suggested review actions only.
- Operator confirmation is required for durable refinement decisions.

Risk: suite extraction could alter live traversal expectations.

Guardrail:

- Extraction creates a separate suite artifact or preview only.
- It does not modify DFS, replay, WebSocket behavior, runtime state, or live maps.

Risk: backend scope could sprawl into topology or frontend architecture.

Guardrail:

- Keep later route handlers thin.
- Keep GUI topology unchanged.
- Keep frontend consumption optional and read-only until backend semantics are tested.

## Validation Guidance for This Planning Note

Because this file is planning-only, repository tests are not required. Suggested targeted validation:

```bash
test -f .ai/plans/review-replay-analysis-backend-semantics-plan.md
rg -n "planning only|No lifecycle state may enqueue runtime actions|Replay-to-Suite Extraction Boundary|Duplicate Prompt Merge Rules" .ai/plans/review-replay-analysis-backend-semantics-plan.md
git diff --name-only
```
