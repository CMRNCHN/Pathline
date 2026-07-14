import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Pathline crashed:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: "2rem", fontFamily: "system-ui", maxWidth: 640 }}>
          <h1 style={{ fontSize: "1.25rem", marginBottom: "0.5rem" }}>Pathline failed to load</h1>
          <p style={{ color: "#595959", marginBottom: "1rem" }}>
            JavaScript hit an error — buttons will not work until this is fixed.
          </p>
          <pre
            style={{
              background: "#0a0a0b",
              color: "#fafafa",
              padding: "1rem",
              borderRadius: 8,
              fontSize: "0.75rem",
              overflow: "auto",
            }}
          >
            {this.state.error.message}
          </pre>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{
              marginTop: "1rem",
              padding: "0.5rem 1rem",
              background: "#0a0a0b",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              cursor: "pointer",
            }}
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
