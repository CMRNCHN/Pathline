import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { ScriptProvider } from "./context/ScriptContext";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ScriptProvider>
      <App />
    </ScriptProvider>
  </StrictMode>
);
