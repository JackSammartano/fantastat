import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, HashRouter } from "react-router-dom";
import { App } from "./App";
import { IS_STATIC } from "./api/client";
import { CoachProvider } from "./coach/CoachContext";
import "./styles.css";

const Router = IS_STATIC ? HashRouter : BrowserRouter;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Router>
      <CoachProvider><App /></CoachProvider>
    </Router>
  </StrictMode>
);
