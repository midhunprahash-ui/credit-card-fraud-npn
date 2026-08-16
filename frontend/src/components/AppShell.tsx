import { Icon } from "./Icon";

export function AppShell({
  apiOnline,
  children,
}: {
  apiOnline: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="simple-app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">
            <Icon name="shield" size={22} />
          </span>
          <div>
            <strong>CYPHER</strong>
            <span>Fraud Intelligence</span>
          </div>
        </div>
        <div className="api-status">
          <span
            className={`connection-dot ${apiOnline ? "online" : "offline"}`}
          />
          <div>
            <strong>{apiOnline ? "API connected" : "API unavailable"}</strong>
            <span>Cloud API · Production</span>
          </div>
        </div>
      </header>
      <main className="simple-content">{children}</main>
    </div>
  );
}
