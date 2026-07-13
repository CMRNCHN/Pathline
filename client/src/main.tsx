import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { TooltipProvider } from "./components/ui/tooltip";
import { ScriptStoreProvider } from "./store/ScriptStore";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <TooltipProvider>
        <ScriptStoreProvider>
          <App />
        </ScriptStoreProvider>
      </TooltipProvider>
    </ErrorBoundary>
  </StrictMode>
);
