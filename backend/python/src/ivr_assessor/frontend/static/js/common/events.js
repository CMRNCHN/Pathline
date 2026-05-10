const RUN_EVENTS = {
  STEP_STARTED:        'StepStarted',
  STEP_UPDATED:        'StepUpdated',
  STEP_PASSED:         'StepPassed',
  STEP_FAILED:         'StepFailed',
  STEP_TIMED_OUT:      'StepTimedOut',
  RUN_SUITE_COMPLETED: 'RunSuiteCompleted',
};

// Pub/sub bus — ready for websocket push when the backend gains /ws/events.
// Currently unused; the GUI polls via HTTP.
const EventBus = {
  _l: {},
  on(type, fn)  { (this._l[type] = this._l[type] || []).push(fn); },
  off(type, fn) { this._l[type] = (this._l[type] || []).filter(f => f !== fn); },
  emit(type, data) { (this._l[type] || []).forEach(fn => { try { fn(data); } catch(_) {} }); },
};
