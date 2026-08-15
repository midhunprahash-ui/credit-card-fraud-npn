import { useEffect, useState } from "react";

type Health = {
  status: string;
  environment: string;
  models_registered: number;
  supabase_configured: boolean;
  r2_configured: boolean;
};

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; health: Health }
  | { kind: "error"; message: string };

const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

function StatusPill({ ready, children }: { ready: boolean; children: React.ReactNode }) {
  return <span className={`status-pill ${ready ? "status-ready" : "status-waiting"}`}>{children}</span>;
}

export default function App() {
  const [loadState, setLoadState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    async function loadHealth() {
      try {
        const response = await fetch(`${API_URL}/health`, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`API returned ${response.status}`);
        }
        setLoadState({ kind: "ready", health: (await response.json()) as Health });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setLoadState({
          kind: "error",
          message: error instanceof Error ? error.message : "API connection failed",
        });
      }
    }

    void loadHealth();
    return () => controller.abort();
  }, []);

  return (
    <main className="page-shell">
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">NPN fraud intelligence</p>
        <h1 id="page-title">Fraud Analyst</h1>
        <p className="intro">
          Platform connectivity is being established before the analyst workflows are enabled.
        </p>
      </section>

      <section className="readiness-card" aria-labelledby="readiness-title" aria-live="polite">
        <div className="card-heading">
          <div>
            <p className="section-label">Integration checkpoint</p>
            <h2 id="readiness-title">System readiness</h2>
          </div>
          <StatusPill ready={loadState.kind === "ready"}>
            {loadState.kind === "loading" ? "Checking" : loadState.kind === "ready" ? "API online" : "Needs attention"}
          </StatusPill>
        </div>

        {loadState.kind === "loading" ? <p className="muted">Contacting the Render API…</p> : null}
        {loadState.kind === "error" ? (
          <p className="error-message">Could not reach {API_URL}: {loadState.message}</p>
        ) : null}
        {loadState.kind === "ready" ? (
          <dl className="readiness-grid">
            <div>
              <dt>Model catalog</dt>
              <dd>{loadState.health.models_registered} V1/V2 pipelines</dd>
            </div>
            <div>
              <dt>Supabase</dt>
              <dd>{loadState.health.supabase_configured ? "Configured" : "Awaiting server secret"}</dd>
            </div>
            <div>
              <dt>Cloudflare R2</dt>
              <dd>{loadState.health.r2_configured ? "Configured" : "Awaiting server secret"}</dd>
            </div>
            <div>
              <dt>Environment</dt>
              <dd>{loadState.health.environment}</dd>
            </div>
          </dl>
        ) : null}
      </section>
    </main>
  );
}

