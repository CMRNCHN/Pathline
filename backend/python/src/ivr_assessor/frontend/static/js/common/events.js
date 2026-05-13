/**
 * Operational event types for Pathline.
 * Aligned with backend/python/src/ivr_assessor/events/event_types.py
 */
const EventType = {
    // Call Lifecycle
    CALL_STARTED: "CALL_STARTED",
    CALL_TRANSFERRED: "CALL_TRANSFERRED",
    CALL_ENDED: "CALL_ENDED",

    // Topology & Discovery
    STATE_DISCOVERED: "STATE_DISCOVERED",
    STATE_RESOLVED: "STATE_RESOLVED",
    STATE_UNRESOLVED: "STATE_UNRESOLVED",
    ROUTE_COMPLETED: "ROUTE_COMPLETED",
    LOOP_DETECTED: "LOOP_DETECTED",
    DRIFT_DETECTED: "DRIFT_DETECTED",

    // Interaction
    PROMPT_DETECTED: "PROMPT_DETECTED",
    DTMF_SENT: "DTMF_SENT",
    SPEECH_SENT: "SPEECH_SENT",
    TRANSCRIPT_FINAL: "TRANSCRIPT_FINAL",

    // Automation & Escalation
    RUN_ESCALATED: "RUN_ESCALATED",
    REVIEW_VERIFIED: "REVIEW_VERIFIED",
    CONFIDENCE_CHANGED: "CONFIDENCE_CHANGED",

    // System
    ERROR_RAISED: "ERROR_RAISED",
    TEMPLATE_CREATED: "TEMPLATE_CREATED",
};

/**
 * Unified Event Bus for the Pathline frontend.
 * Supports cross-workspace operational telemetry and event lineage.
 */
const EventBus = {
    _listeners: {},
    _globalListeners: [],

    /**
     * Subscribe to a specific event type.
     * @param {string} type 
     * @param {Function} callback 
     */
    on(type, callback) {
        if (!this._listeners[type]) {
            this._listeners[type] = [];
        }
        this._listeners[type].push(callback);
    },

    /**
     * Subscribe to all events.
     * @param {Function} callback 
     */
    onAny(callback) {
        this._globalListeners.push(callback);
    },

    /**
     * Unsubscribe from a specific event type.
     * @param {string} type 
     * @param {Function} callback 
     */
    off(type, callback) {
        if (this._listeners[type]) {
            this._listeners[type] = this._listeners[type].filter(cb => cb !== callback);
        }
    },

    /**
     * Emit an event to all subscribers.
     * @param {string} type 
     * @param {Object} data - Should follow { payload: {}, meta: {} } structure
     */
    emit(type, data = {}) {
        // Ensure data follows the unified model if possible
        const event = {
            type: type,
            payload: data.payload || data,
            meta: data.meta || { timestamp: Date.now() / 1000 }
        };

        // Notify specific listeners
        if (this._listeners[type]) {
            this._listeners[type].forEach(callback => {
                try {
                    callback(event);
                } catch (err) {
                    console.error(`Error in EventBus listener for ${type}:`, err);
                }
            });
        }

        // Notify global listeners
        this._globalListeners.forEach(callback => {
            try {
                callback(event);
            } catch (err) {
                console.error(`Error in EventBus global listener:`, err);
            }
        });
    }
};

// Legacy compatibility for run_suites.js if needed
const RUN_EVENTS = {
    STEP_STARTED: 'StepStarted',
    STEP_UPDATED: 'StepUpdated',
    STEP_PASSED: 'StepPassed',
    STEP_FAILED: 'StepFailed',
    STEP_TIMED_OUT: 'StepTimedOut',
    RUN_SUITE_COMPLETED: 'RunSuiteCompleted',
};
