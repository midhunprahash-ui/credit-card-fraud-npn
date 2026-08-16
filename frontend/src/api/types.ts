export type VersionName = "V1" | "V2";

export type ModelIdentifier =
  | "logistic_regression.v1"
  | "lightgbm.v1"
  | "catboost.v1"
  | "neural_network.v1"
  | "logistic_regression.v2"
  | "lightgbm.v2"
  | "catboost.v2"
  | "neural_network.v2";

export type MetricSet = {
  pr_auc: number;
  roc_auc: number;
  precision: number;
  recall: number;
  f1: number;
  threshold: number;
  confusion_matrix: [[number, number], [number, number]];
  rows: number;
};

export type ModelCatalogItem = {
  model_key: string;
  model_identifier: ModelIdentifier;
  model_name: string;
  display_name: string;
  version_name: VersionName;
  run_id: string;
  threshold: number;
  champion: boolean;
  validation_pr_auc: number;
  test_pr_auc: number;
  loading_status: string;
  metrics: {
    validation: MetricSet | null;
    test: MetricSet | null;
    training_seconds: number | null;
    prediction_latency_ms: number | null;
  };
  feature_importance_available: boolean;
  top_features: Array<{ feature: string; value: number; kind: string }>;
};

export type Health = {
  status: string;
  environment: string;
  models_registered: number;
  model_artifacts_available: number;
  supabase_configured: boolean;
  r2_configured: boolean;
  artifact_source: "local" | "r2_lazy_cache";
  behavioral_reference_available: boolean;
};

export type ModelPrediction = {
  model_identifier: ModelIdentifier;
  model_name: string;
  model_version: VersionName;
  run_id: string;
  risk_score: number;
  threshold: number;
  decision: boolean;
  decision_label: "fraud" | "legitimate";
  latency_ms: number;
  champion: boolean;
  processing_status: string;
  important_features: Array<{ feature: string; value: number }> | null;
};

export type Agreement = {
  fraud_vote_count: number;
  selected_model_count: number;
  unanimous: boolean;
  agreement_label: string;
};

export type PredictionResponse = {
  transaction_id: number;
  input_completeness: number;
  results: ModelPrediction[];
  agreement: Agreement;
};

export type BatchResponse = {
  summary: {
    total_rows: number;
    valid_rows: number;
    invalid_rows: number;
    processed_rows: number;
    failed_rows: number;
    fraud_count_by_model: Record<string, number>;
    model_agreement_count: number;
    suspicious_transaction_value: number;
  };
  results: Array<Record<string, unknown>>;
  invalid_row_report: Array<{
    row_number: number;
    transaction_id: string | number | null;
    error_code: string;
    message: string;
  }>;
  processing_status: string;
};

export type StreamDataset = {
  id: string;
  name: string;
  split: string;
  schema_version: string;
  row_count: number;
  fraud_count: number | null;
  fraud_rate: number | null;
  labels_available: boolean;
  description: string | null;
  status: string;
};

export type StreamStatus = {
  stream_run_id: string | null;
  dataset_id: string | null;
  status:
    | "IDLE"
    | "LOADING"
    | "RUNNING"
    | "PAUSED"
    | "STOPPING"
    | "STOPPED"
    | "COMPLETED"
    | "FAILED"
    | "UNAVAILABLE";
  selected_versions: VersionName[];
  selected_models: ModelIdentifier[];
  transactions_per_second: number;
  transactions_received: number;
  transactions_processed: number;
  transactions_queued: number;
  currently_processing: Record<string, unknown> | null;
  current_sequence: number;
  current_throughput: number;
  average_latency_ms: number;
  p95_latency_ms: number;
  fraud_alerts: number;
  suspicious_transaction_value: number;
  failed_transactions: number;
  unpersisted_transactions: number;
  started_at: string | null;
  completed_at: string | null;
};

export type CompletedStreamEvent = {
  sequence_number: number;
  transaction_id: number;
  arrival_time: string;
  queue_position: number;
  processing_started_at: string;
  completed_at: string;
  status: string;
  actual_label: boolean | null;
  results: ModelPrediction[];
  agreement: Agreement | null;
  latency_ms: number;
  queue_length: number;
  error_code: string | null;
  stream?: StreamStatus;
};

export type QueueStreamEvent = {
  sequence_number: number;
  transaction_id: number;
  arrival_time: string;
  queue_position: number;
  status: string;
  queue_length: number;
  stream?: StreamStatus;
};

export type FraudAlert = {
  id: string;
  stream_run_id: string;
  transaction_id: number;
  status: string;
  highest_risk_score: number;
  model_agreement: number;
  selected_model_count: number;
  suspicious_amount: number | null;
  created_at: string;
  updated_at: string;
  stream_runs?: {
    selected_models: ModelIdentifier[];
    selected_versions: VersionName[];
  };
};

export type AlertDetail = FraudAlert & {
  predictions: Array<{
    model_identifier: ModelIdentifier;
    risk_score: number;
    threshold: number;
    decision: boolean;
    actual_label: boolean | null;
    latency_ms: number;
    model_run_id: string;
    created_at: string;
  }>;
  analyst_actions: Array<{
    id: string;
    action: string;
    analyst_identifier: string;
    note: string | null;
    created_at: string;
  }>;
  lifecycle: Record<string, unknown> | null;
  transaction: {
    transaction_payload: Record<string, unknown>;
    transaction_dt: number;
  } | null;
};

export type MetricsSummary = {
  runtime: {
    prediction_requests: number;
    transactions_scored: number;
    model_predictions: number;
    error_count: number;
    average_request_latency_ms: number;
  };
  model_manager: {
    max_loaded_models: number;
    loaded_count: number;
    cache_order: string[];
    models: Array<Record<string, unknown>>;
  };
  stream: StreamStatus | { status: "UNAVAILABLE" };
};

export type IntegrationStatus = {
  supabase: { configured: boolean; reachable: boolean; detail: string };
  cloudflare_r2: { configured: boolean; reachable: boolean; detail: string };
};
