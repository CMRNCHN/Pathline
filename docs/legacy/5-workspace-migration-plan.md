# IVRSuite 5-Workspace Migration Plan (Revised)

## Executive Summary
This plan outlines the evolution of the IVRSuite product architecture into a coherent 5-workspace lifecycle: Prep, Discover, Live, Review, and Run. The transition moves the system from a modal/drawer-heavy interface to a dedicated multi-screen workstation designed for clear operational phases.

## Governance Sources Reviewed
- `.ai/PROJECT_STATE.md`
- `.ai/ARCHITECTURE_RULES.md`
- `.ai/AI_AGENT_RULES.md`
- `.ai/plans/ivr-phase-operations-anchor.md`

## Revised Workspace Constraints

### 1. Prep
- **Purpose**: Configure and validate everything before a session.
- **Data Persistence**: Must NOT become a credentials authority. Persist only reusable operator configuration (IVR profiles, trigger phrases, ready responses, non-secret run preferences).
- **Ownership**: Owns target phone number, caller ID, IVR profile, language, max duration, recording toggle, etc.

### 2. Discover
- **Purpose**: Explore unknown/partially known IVRs to build the initial menu map.
- **Probing Controls**: Must remain bounded and deterministic. Configures max depth, retry, silence, invalid-input, transfer-avoidance, and loop-detection.
- **Constraint**: No autonomous reasoning or hidden traversal orchestration beyond deterministic DFS.

### 3. Live
- **Purpose**: Operate and control an active call in real time.
- **Layout**: 
  - Top: Active Call Status Card (state-level summary).
  - Main: 65% IVR Map / 35% Live Transcript + Controls.
  - Bottom: 50% Recent Events / 50% Unresolved States.
- **Unified Injection**: Numeric becomes DTMF; Word/text becomes AI speech injection.

### 4. Review
- **Purpose**: Analyze completed calls and convert raw evidence into reusable templates.
- **Surface Consumption**: Must first consume existing replay, report, recording, and inspection surfaces.
- **Constraint**: Read-only unless separately approved. Must not steer live traversal.

### 5. Run
- **Purpose**: Background execution of approved reusable suites.
- **Constraint**: Bounded/deterministic background execution only. Not open-ended autonomous calling.

## Current Repo Capability Map

| Workspace | Existing Capabilities | Partially Implemented | Missing |
| :--- | :--- | :--- | :--- |
| **Prep** | Target input, Route checks, Reusable inputs | Reusable operator config | Readiness checklist, Ready responses |
| **Discover** | IVR Map, Deterministic Traversal | Probing config | Coverage metrics, Exploration queue |
| **Live** | Transcript, Map, Smart Input, Conference | Unified injection bar, Call status card | Push-to-talk, 3-tier layout |
| **Review** | Log-based replay, Checkpoint verification | - | Call selector, Integrated surface consumption |
| **Run** | Suite library, Progress tracking | - | Background-only execution mode |

## Incremental Implementation Slices

### Slice 1: Shell & Navigation (Frontend Only)
- **Scope**: Implement header navigation, workspace switching logic, and empty layout containers.
- **Focus**: UI structure and navigation state. No functional logic migration.

### Slice 2: Live Workspace Refactor
- **Scope**: Re-organize existing Live components into the required 65/35 and 50/50 layout.

### Slice 3: Prep Workspace Migration
- **Scope**: Move "Suite Planning" modal content into a dedicated Prep workspace. Implement non-secret config persistence.

### Slice 4: Run Workspace Migration
- **Scope**: Move "Suite Execution" modal into a dedicated Run workspace for background-only execution.

### Slice 5: Discover & Review Expansion
- **Scope**: Consolidate existing replay/report surfaces into Review. Implement Discover probing UI controls.

## Risks and Guardrails
- **Guardrail**: Preserve current backend/runtime/websocket/replay semantics exactly.
- **Guardrail**: No introduction of frontend frameworks or build steps.
- **Risk**: Fragmentation of user experience during incremental slices.

## Test Plan
- **Navigation**: Verify workspace buttons correctly toggle visibility of all panels.
- **Layout**: Verify 65/35 and 50/50 splits in Live workspace.
- **Regressions**: Ensure `pytest` passes with 250+ tests.
- **Protocol**: Verify WebSocket messages continue to flow correctly to the Live workspace.
