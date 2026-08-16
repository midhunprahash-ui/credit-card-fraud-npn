import type {
  AlertDetail,
  BatchResponse,
  CompletedStreamEvent,
  FraudAlert,
  Health,
  IntegrationStatus,
  MetricsSummary,
  ModelCatalogItem,
  ModelIdentifier,
  PredictionResponse,
  QueueStreamEvent,
  StreamDataset,
  StreamStatus,
} from "./types";

export const API_URL = (
  import.meta.env.VITE_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    let code = "request_failed";
    let message = `API returned ${response.status}`;
    try {
      const body = (await response.json()) as {
        error?: { code?: string; message?: string };
      };
      code = body.error?.code ?? code;
      message = body.error?.message ?? message;
    } catch {
      // Keep the safe status-only fallback for non-JSON gateway errors.
    }
    throw new ApiClientError(message, response.status, code);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => request<Health>("/health"),
  integrations: () => request<IntegrationStatus>("/integrations"),
  models: () =>
    request<{ versions: string[]; models: ModelCatalogItem[] }>("/models"),
  metrics: () => request<MetricsSummary>("/metrics/summary"),
  demoTransactions: (limit = 20) =>
    request<{
      dataset: string;
      split: string;
      labels_available: boolean;
      transactions: Array<{
        transaction_id: number;
        transaction_dt: number;
        transaction_amount: number | null;
        product_code: string | null;
        has_identity: boolean;
      }>;
    }>(`/demo-transactions?limit=${limit}`),
  transaction: (transactionId: number) =>
    request<{
      labels_available: boolean;
      transaction_payload: Record<string, unknown>;
    }>(`/transactions/${transactionId}`),
  predict: (
    transaction: Record<string, unknown>,
    modelIdentifiers: ModelIdentifier[],
  ) =>
    request<PredictionResponse>("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transaction,
        model_identifiers: modelIdentifiers,
      }),
    }),
  predictFile: async (file: File, modelIdentifiers: ModelIdentifier[]) => {
    const body = new FormData();
    body.append("file", file);
    body.append("models", JSON.stringify(modelIdentifiers));
    return request<PredictionResponse>("/predict/file", {
      method: "POST",
      body,
    });
  },
  predictBatch: async (file: File, modelIdentifiers: ModelIdentifier[]) => {
    const body = new FormData();
    body.append("file", file);
    body.append("models", JSON.stringify(modelIdentifiers));
    body.append("response_format", "json");
    return request<BatchResponse>("/predict/batch", { method: "POST", body });
  },
  streamDatasets: () =>
    request<{ datasets: StreamDataset[] }>("/stream/datasets"),
  streamStart: (
    datasetId: string,
    selectedModels: ModelIdentifier[],
    transactionsPerSecond: number,
  ) =>
    request<StreamStatus>("/stream/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset_id: datasetId,
        selected_models: selectedModels,
        transactions_per_second: transactionsPerSecond,
      }),
    }),
  streamControl: (control: "pause" | "resume" | "stop" | "restart") =>
    request<StreamStatus>(`/stream/${control}`, { method: "POST" }),
  streamStatus: () => request<StreamStatus>("/stream/status"),
  alerts: (query = "") =>
    request<{ alerts: FraudAlert[] }>(`/alerts${query ? `?${query}` : ""}`),
  alert: (alertId: string) => request<AlertDetail>(`/alerts/${alertId}`),
  alertAction: (
    alertId: string,
    payload: {
      action: string;
      analyst_identifier: string;
      note: string | null;
    },
  ) =>
    request<{ analyst_action: AlertDetail["analyst_actions"][number] }>(
      `/alerts/${alertId}/actions`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    ),
};

const STREAM_EVENT_TYPES = [
  "stream_status",
  "stream_started",
  "stream_paused",
  "stream_resumed",
  "stream_stopping",
  "stream_finished",
  "stream_failed",
  "transaction_received",
  "transaction_processing",
  "transaction_completed",
  "transaction_failed",
  "persistence_failed",
] as const;

export type StreamMessage =
  | { type: "transaction_received"; data: QueueStreamEvent }
  | {
      type: "transaction_completed" | "transaction_failed";
      data: CompletedStreamEvent;
    }
  | { type: string; data: StreamStatus | Record<string, unknown> };

export function subscribeToStream(
  onEvent: (message: StreamMessage) => void,
  onConnectionChange: (connected: boolean) => void,
): () => void {
  const source = new EventSource(`${API_URL}/stream/events`);
  source.onopen = () => onConnectionChange(true);
  source.onerror = () => onConnectionChange(false);
  for (const type of STREAM_EVENT_TYPES) {
    source.addEventListener(type, (event) => {
      const message = event as MessageEvent<string>;
      onEvent({
        type,
        data: JSON.parse(message.data) as Record<string, unknown>,
      } as StreamMessage);
    });
  }
  return () => source.close();
}
