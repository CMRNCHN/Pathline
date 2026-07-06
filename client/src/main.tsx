import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { ScriptStoreProvider } from "./store/ScriptStore";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ScriptStoreProvider>
      <App />
    </ScriptStoreProvider>
  </StrictMode>
);
