type IconName =
  | "overview"
  | "live"
  | "alerts"
  | "batch"
  | "models"
  | "monitor"
  | "shield"
  | "search"
  | "chevron"
  | "play"
  | "pause"
  | "stop"
  | "refresh"
  | "upload"
  | "download"
  | "check"
  | "warning"
  | "close";

const paths: Record<IconName, React.ReactNode> = {
  overview: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </>
  ),
  live: (
    <>
      <path d="M4 17l4-5 4 3 5-8 3 2" />
      <path d="M4 4v16h16" />
    </>
  ),
  alerts: (
    <>
      <path d="M18 8a6 6 0 00-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
      <path d="M10 21h4" />
    </>
  ),
  batch: (
    <>
      <path d="M4 4h16v16H4z" />
      <path d="M4 9h16M9 4v16" />
    </>
  ),
  models: (
    <>
      <circle cx="12" cy="5" r="2" />
      <circle cx="5" cy="18" r="2" />
      <circle cx="19" cy="18" r="2" />
      <path d="M12 7v4M7 17l4-4M17 17l-4-4" />
    </>
  ),
  monitor: (
    <>
      <rect x="3" y="4" width="18" height="13" rx="2" />
      <path d="M8 21h8M12 17v4M6 12l3-3 3 2 4-5 2 2" />
    </>
  ),
  shield: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />,
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-4-4" />
    </>
  ),
  chevron: <path d="M9 18l6-6-6-6" />,
  play: <path d="M8 5v14l11-7z" />,
  pause: <path d="M8 5v14M16 5v14" />,
  stop: <rect x="6" y="6" width="12" height="12" rx="1" />,
  refresh: (
    <>
      <path d="M20 7v5h-5" />
      <path d="M18 16a8 8 0 10-1-10l3 6" />
    </>
  ),
  upload: (
    <>
      <path d="M12 16V3M7 8l5-5 5 5" />
      <path d="M4 15v5h16v-5" />
    </>
  ),
  download: (
    <>
      <path d="M12 3v13M7 11l5 5 5-5" />
      <path d="M4 15v5h16v-5" />
    </>
  ),
  check: <path d="M5 12l4 4L19 6" />,
  warning: (
    <>
      <path d="M12 3L2 21h20L12 3z" />
      <path d="M12 9v5M12 18h.01" />
    </>
  ),
  close: <path d="M6 6l12 12M18 6L6 18" />,
};

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}
