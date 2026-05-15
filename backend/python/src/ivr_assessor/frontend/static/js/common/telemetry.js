/**
 * Operator Telemetry (Agent D1).
 *
 * Fire-and-forget POSTs to /api/telemetry. The backend redacts phone numbers
 * and credentials before persisting, but callers should still keep contexts
 * small and avoid passing raw user input.
 *
 * Usage:
 *   Telemetry.track('replay_scrubbed', { sessionId, position });
 *
 * Failures are swallowed silently — telemetry must never break the UI.
 */
(function (global) {
  'use strict';

  function _now() {
    return Date.now() / 1000;
  }

  async function track(actionName, context, sessionId) {
    if (!actionName) return;
    try {
      await fetch('/api/telemetry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: actionName,
          context: context || {},
          ts: _now(),
          session_id: sessionId || null,
        }),
        keepalive: true,
      });
    } catch (_err) {
      // Intentional: telemetry failure is not a UX failure.
    }
  }

  global.Telemetry = { track: track };
})(typeof window !== 'undefined' ? window : globalThis);
