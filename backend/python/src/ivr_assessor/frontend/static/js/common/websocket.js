// WebSocket manager — ready for a /ws/events push channel when the backend gains one.
// Currently unused; the GUI polls via HTTP. Drop in connect() when the endpoint exists.
class WsManager {
  constructor(url, onMessage) {
    this._url = url;
    this._onMessage = onMessage;
    this._ws = null;
    this._dead = false;
  }

  connect() {
    if (this._dead) return;
    this._ws = new WebSocket(this._url);
    this._ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        // Dispatch by message type so subscribers can listen via EventBus.on(type, fn).
        if (msg && msg.type) EventBus.emit(msg.type, msg);
        if (this._onMessage) this._onMessage(msg);
      } catch(_) {}
    };
    this._ws.onclose = () => {
      if (!this._dead) setTimeout(() => this.connect(), 2000);
    };
    this._ws.onerror = () => this._ws.close();
  }

  send(obj) {
    if (this._ws && this._ws.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify(obj));
    }
  }

  close() {
    this._dead = true;
    if (this._ws) this._ws.close();
  }
}
