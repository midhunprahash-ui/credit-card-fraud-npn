import { Icon } from "./Icon";

export type PageId =
  "overview" | "live" | "alerts" | "batch" | "models" | "monitoring";

const NAV_ITEMS: Array<{
  id: PageId;
  label: string;
  icon: Parameters<typeof Icon>[0]["name"];
}> = [
  { id: "overview", label: "Overview", icon: "overview" },
  { id: "live", label: "Live Analysis", icon: "live" },
  { id: "alerts", label: "Fraud Alerts", icon: "alerts" },
  { id: "batch", label: "Batch Analysis", icon: "batch" },
  { id: "models", label: "Model Comparison", icon: "models" },
  { id: "monitoring", label: "Monitoring", icon: "monitor" },
];

export function AppShell({
  page,
  onNavigate,
  apiOnline,
  children,
}: {
  page: PageId;
  onNavigate: (page: PageId) => void;
  apiOnline: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <Icon name="shield" size={22} />
          </span>
          <div>
            <strong>NPN</strong>
            <span>Fraud Intelligence</span>
          </div>
        </div>
        <nav aria-label="Primary navigation">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${page === item.id ? "nav-active" : ""}`}
              aria-current={page === item.id ? "page" : undefined}
              onClick={() => onNavigate(item.id)}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span
            className={`connection-dot ${apiOnline ? "online" : "offline"}`}
          />
          <div>
            <strong>{apiOnline ? "API connected" : "API unavailable"}</strong>
            <span>Cloud API · Production</span>
          </div>
        </div>
      </aside>
      <div className="app-main">
        <div className="mobile-brand">
          <div className="brand">
            <span className="brand-mark">
              <Icon name="shield" size={20} />
            </span>
            <strong>NPN Fraud Intelligence</strong>
          </div>
        </div>
        <main className="content">{children}</main>
        <nav className="mobile-nav" aria-label="Mobile navigation">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={page === item.id ? "nav-active" : ""}
              onClick={() => onNavigate(item.id)}
              aria-label={item.label}
            >
              <Icon name={item.icon} />
              <span>{item.label.split(" ")[0]}</span>
            </button>
          ))}
        </nav>
      </div>
    </div>
  );
}
