import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ScriptStoreProvider } from "./store/ScriptStore";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <ScriptStoreProvider>
        <App />
      </ScriptStoreProvider>
    </ErrorBoundary>
  </StrictMode>
);
