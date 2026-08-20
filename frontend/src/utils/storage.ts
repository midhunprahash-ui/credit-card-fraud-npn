const CLIENT_ID_KEY = "cypher.analysis-client.v1";
const SESSION_PREFIX = "cypher.workspace.v1";

let memoryClientId: string | null = null;
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function createUuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto)
    return crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (value) => {
    const random = Math.floor(Math.random() * 16);
    const digit = value === "x" ? random : (random & 0x3) | 0x8;
    return digit.toString(16);
  });
}

export function getAnalysisClientId(): string {
  if (memoryClientId) return memoryClientId;
  try {
    const stored = window.localStorage.getItem(CLIENT_ID_KEY);
    if (stored && UUID_PATTERN.test(stored)) {
      memoryClientId = stored;
      return stored;
    }
    const created = createUuid();
    window.localStorage.setItem(CLIENT_ID_KEY, created);
    memoryClientId = created;
    return created;
  } catch {
    memoryClientId = createUuid();
    return memoryClientId;
  }
}

export function readSessionState<T>(name: string, fallback: T): T {
  try {
    const value = window.sessionStorage.getItem(`${SESSION_PREFIX}.${name}`);
    return value ? (JSON.parse(value) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function writeSessionState<T>(name: string, value: T): void {
  try {
    window.sessionStorage.setItem(
      `${SESSION_PREFIX}.${name}`,
      JSON.stringify(value),
    );
  } catch {
    // A full or disabled session store must not break prediction workflows.
  }
}

export function publishHistoryChange(): void {
  window.dispatchEvent(new Event("cypher:analysis-history-changed"));
}
