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
};
