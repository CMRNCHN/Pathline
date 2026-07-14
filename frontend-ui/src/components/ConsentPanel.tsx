import { useState } from "react";

interface ConsentPanelProps {
  onAccept: () => void;
  onDecline: () => void;
}

export function ConsentPanel({ onAccept, onDecline }: ConsentPanelProps) {
  const [checked, setChecked] = useState(false);

  return (
    <div className="consent-panel">
      <h2>Consent & Authorization</h2>
      <p className="consent-intro">
        Pathline v1 uses a client-mediated architecture. Your device places the call,
        holds your secrets, and processes audio locally. The server only receives encrypted status blobs.
      </p>

      <div className="consent-terms">
        <ul>
          <li>Your secrets and target number stay on this device — never sent to our servers</li>
          <li>Speech recognition runs locally when available</li>
          <li>Only encrypted status is reported to Pathline</li>
          <li>Session data is auto-purged; you can revoke and delete anytime</li>
          <li>Carriers still see calling/called numbers, times, and duration</li>
          <li>You confirm lawful usage and authorization for third-party IVR interactions</li>
        </ul>
      </div>

      <label className="consent-checkbox">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
        />
        <span>I have read and accept these terms (v1.0)</span>
      </label>

      <div className="consent-actions">
        <button className="btn btn-secondary" onClick={onDecline}>
          Decline
        </button>
        <button className="btn btn-primary" disabled={!checked} onClick={onAccept}>
          Accept & Continue
        </button>
      </div>
    </div>
  );
}
