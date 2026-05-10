// Shared cross-panel state. Panel-local state (step statuses, pad buffer, etc.)
// stays in each panel's own script.
const AppState = {
  callRunning:  false,  // a live Twilio call is active
  manualMode:   false,  // manual vs auto-pilot routing mode
  suiteRunning: false,  // a run suite test is in flight
};
