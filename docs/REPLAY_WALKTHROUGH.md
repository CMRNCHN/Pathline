# Replay Walkthrough: A Step-by-Step Example

## Scenario
We've just completed a discovery run on a billing IVR. The session recorded 8 states and 12 transitions. Now let's replay the session to understand what happened and refine the map.

## Step 1: Select Session to Replay

**In Review Workspace:**
```
Replay Session Selector
┌─────────────────────────────────────────────────────┐
│ Select a session to replay...                      ▼ │
│ 2026-05-15 10:32:14 - sess_abc123def (12 events)    │
│ 2026-05-15 09:45:22 - sess_xyz789abc (8 events)     │
│ 2026-05-14 16:18:30 - sess_test001 (24 events)      │
└─────────────────────────────────────────────────────┘
```

**Select** the first session (most recent). The GUI shows:
- Skeleton loaders briefly appear
- Progress bar: "Initializing timeline... 25%"
- Graph panel skeleton
- Transcript list skeleton
- Progress advances: "Hydrating state... 50%", "Rendering graph... 75%"
- Full session loads

## Step 2: Inspect the Graph

Once loaded, the Graph Panel shows:

```
Graph: Entry → State 1 → State 2 → State 3
                              ↓
                          State 4
                          
States Found: 8
Transitions: 12
Call Duration: 2:34
Reconstructed From: Snapshot (offset 4/12)
```

**Annotations:**
- **Snapshot offset 4/12**: This session resumed from a saved snapshot at event 4, then replayed 8 more events
- **Entry node** (diamond shape): The initial system prompt
- **State nodes** (circles): Detected IVR prompts
- **Edges** (arrows): Transitions triggered by responses

## Step 3: Navigate the Timeline

The Timeline Controls appear:

```
Timeline Position: |◄  ◄  Event 0/12 (00:00)  ▸  ▸|
                   └─ Cursor position slider ───────┘
```

**Try these movements:**

### Jump to Start: Click **|<**
- Cursor moves to event 0 (session begins)
- Transcript Panel highlights: "IVR: 'Welcome to billing...'
- Graph shows entry state only (no transitions yet)

### Step Forward: Click **>** (next transcript)
- Cursor moves to event 2 (user response)
- Transcript highlights: "User: '1'" (DTMF response)
- Graph updates to show State 1 with incoming transition

### Scrub to Middle: Click position slider, drag to 50%
- Cursor jumps to event 6
- Transcript highlights conversation at this point
- Graph expands; you can see multiple states and transitions
- Observed: Graph shows 5 states discovered so far

### Jump to End: Click **>|**
- Cursor moves to final event (event 12)
- Transcript shows the last IVR prompt and outcome
- Graph fully expanded: all 8 states visible
- Timeline shows "Event 12/12 (02:34)" — session duration

## Step 4: Sync Transcript to Timeline

In the Transcript Panel:

```
Transcripts
─────────────────────────────────
| IVR: Welcome to billing...     |  ← Highlighted (current transcript)
| User: 1                        |
| IVR: Account holder?           |
| User: [speech] I'm the account |
| IVR: Confirm 4155552222? 1/2   |
| User: 1                        |
| IVR: Thank you, call ending    |
| User: [disconnect]             |
─────────────────────────────────
```

**Click on a transcript item** (e.g., "User: [speech] I'm the account holder"):
- Timeline cursor jumps to that event
- Graph updates to show state at that moment
- Helps identify where conversation took unexpected turns

## Step 5: Analyze Metrics

Operational Metrics display:

```
Runtime Diagnostics
─────────────────────────────────
Call Started: 2026-05-15 10:32:14
Duration: 2m 34s
Recording ID: rec_abc123
Total Events: 12
States Discovered: 8
Transitions: 12
Reconstruction: Snapshot @ event 4 + 8 events
Last Checkpoint: "Call complete"
Status: ✓ Completed
─────────────────────────────────
```

**Key observations:**
- **Reconstruction method**: Shows snapshot was used (fast forward)
- **Total events**: All 12 events processed
- **Status badge**: Green checkmark = clean completion

## Step 6: Export for Review

Click **Export** button:

```
Export Format
┌────────┬─────────┬──────────┐
│ JSON   │ Mermaid │ Markdown │
└────────┴─────────┴──────────┘

Exporting Markdown...
✓ Markdown saved to:
  ~/.ivr_assessor/reports/sessions/result-20260515-103214.md

Download files below:
 · ivr_billing_session.json (2.4 KB)
 · ivr_billing_session.mmd (1.1 KB) 
 · ivr_billing_session.md (3.7 KB)
```

**Markdown export shows:**
```markdown
# Billing IVR Session Review

## Summary
- **Date:** 2026-05-15 10:32:14
- **Duration:** 2m 34s
- **States:** 8 detected
- **Status:** Completed

## State Machine
1. Entry → "Welcome to billing"
2. "Press 1 for account, 2 for service"
   - Press 1 → Account prompt
   - Press 2 → Service prompt
...

## Transcript
[Full conversation including IVR and user responses]

## Observations
- [Auto-generated notes on unexpected states, drift, etc.]
```

## Step 7: Refine the Map

Back in the **Review** workspace:

1. **Edit state names:** Double-click a state to rename
   - "State 3" → "Account Verification"
2. **Add notes:** Click state, add annotation
   - "State 4: Language selection (unexpected, not documented)"
3. **Save as refined map:**
   - File menu → "Save Map" → name it "billing_v2_refined"
4. **Update suite:** Use refined map in next suite run

## Key Insights from This Walkthrough

| Pattern | What It Means |
|---------|---------------|
| Snapshot reconstruct | Session resumed from earlier; fast/efficient replay |
| All states visible | Full coverage of this call path |
| Transcript sync works | Timeline updates when you click transcripts |
| Metrics complete | No errors detected during replay |
| Export successful | Data ready for sharing, analysis, or suite refinement |

## Common Next Steps

1. **Drift Detected:** If you see an unexpected state, export and add to "Known Variations" doc
2. **New Route Found:** Save refined map, create suite to test that route next time
3. **Call Failed:** Review final transcript and metrics; check logs for error reason
4. **Confidence Low:** Run more sessions on same IVR to build confidence in state stability

---

**Replay is deterministic**: Same session always produces the same state sequence, making it ideal for incremental map refinement and regression testing.
