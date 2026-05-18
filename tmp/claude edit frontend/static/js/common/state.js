// Shared cross-panel state. Panel-local state (step statuses, pad buffer, etc.)
// stays in each panel's own script.
const AppState = {
  currentWorkspace: 'live',
  callRunning: false,
  manualMode: false,
  suiteRunning: false,
  runtimeDiagnostics: null,
  runtimeMetrics: null,
  diagnose: null,
  mode: 'live', // 'live' or 'replay'
  replayState: null,
  savedMaps: [],
  latestStatus: null,
  latestGraph: {},
  legacyLogs: [],
  selectedTimelineFilter: 'all',
  selectedTimelineEvent: null,
  drawerOpen: false,
  activeDrawerTab: 'session',
  sessionElapsedMs: 0,
  lastElapsedSyncAt: 0,
  lastDiagnoseAt: 0,
  // Prep Workspace State
  prep: {
    target: '',
    callerId: '',
    profile: 'default',
    record: true,
    transcript: true,
    injectionMode: 'auto',
    silenceTimeout: 3000,
    retryLimit: 3,
    triggers: [
      { phrase: 'Press 1 for billing', response: '1' },
      { phrase: 'How can I help you?', response: 'billing support' }
    ]
  },
  // Review Workspace State
  review: {
    selectedCallId: null,
    availableCalls: [],
    transcript: [],
    timeline: [],
    template: {
      name: '',
      provider: '',
      intent: '',
      inputs: [],
      states: []
    }
  },
  // Discover Workspace State
  discover: {
    activeSessionId: null,
    targetIvr: '',
    stats: {
      statesFound: 0,
      unknownStates: 0,
      coverage: 0,
      currentDepth: 0,
      runtime: '00:00',
      confidence: 0
    },
    probeMode: 'Balanced',
    explorationQueue: [],
    events: [],
    unknownPrompts: [],
    selectedStateId: null
  },
  // Run Workspace State
  run: {
    stats: {
      activeRuns: 0,
      queuedRuns: 0,
      successRate: '0%',
      failedRuns: 0,
      escalations: 0,
      avgConfidence: '0%',
      driftAlerts: 0,
      workerAvailability: 'Ready'
    },
    suiteLibrary: [
      { id: 's1', name: 'Comcast Billing', provider: 'Comcast', intent: 'Billing Support', successRate: '98%', confidence: '99%', driftStatus: 'Stable', lastRun: '2h ago', version: 'v1.4' },
      { id: 's2', name: 'Verizon Support', provider: 'Verizon', intent: 'Technical Support', successRate: '94%', confidence: '92%', driftStatus: 'Stable', lastRun: '5h ago', version: 'v2.1' },
      { id: 's3', name: 'Insurance Claim', provider: 'State Farm', intent: 'Claims Filing', successRate: '89%', confidence: '85%', driftStatus: 'Drift Detected', lastRun: '1d ago', version: 'v1.0' }
    ],
    activeRuns: [],
    selectedRunId: null,
    intelligence: {
      currentDecision: 'Awaiting selection',
      detectedPrompt: 'None',
      selectedResponse: 'None',
      confidence: '0%',
      fallbackPlan: 'None',
      predictions: []
    }
  }
};
