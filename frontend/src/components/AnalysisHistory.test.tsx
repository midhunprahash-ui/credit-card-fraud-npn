import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AnalysisHistory } from "./AnalysisHistory";

const apiMocks = vi.hoisted(() => ({
  history: vi.fn(),
  historyRun: vi.fn(),
  explainHistoryPrediction: vi.fn(),
  exportHistory: vi.fn(),
}));

vi.mock("../api/client", () => ({ api: apiMocks }));

const run = {
  id: "run-1",
  input_mode: "single" as const,
  source_name: null,
  stream_run_id: null,
  selected_models: ["catboost.v2" as const, "lightgbm.v2" as const],
  status: "COMPLETED" as const,
  total_transactions: 1,
  successful_transactions: 1,
  failed_transactions: 0,
  summary: {},
  created_at: "2026-08-20T00:00:00Z",
  updated_at: "2026-08-20T00:00:00Z",
};

describe("AnalysisHistory", () => {
  it("loads every model explanation when a transaction is expanded", async () => {
    apiMocks.history.mockResolvedValue({ runs: [run], limit: 50, offset: 0 });
    apiMocks.historyRun.mockResolvedValue({
      run,
      transactions: [
        {
          id: "transaction-1",
          ordinal: 0,
          transaction_id: 100,
          raw_transaction_id: "100",
          input_payload: { TransactionID: 100, TransactionAmt: 25 },
          status: "COMPLETED",
          error_code: null,
          error_message: null,
          created_at: run.created_at,
          predictions: ["catboost.v2", "lightgbm.v2"].map(
            (identifier, index) => ({
              id: `prediction-${index + 1}`,
              analysis_transaction_id: "transaction-1",
              model_identifier: identifier,
              model_name:
                identifier === "catboost.v2" ? "CatBoost.V2" : "LightGBM.V2",
              model_version: "V2",
              model_run_id: `model-run-${index + 1}`,
              risk_score: 0.9 - index * 0.2,
              threshold: 0.4,
              decision: index === 0,
              latency_ms: 2,
              explanation_status: "NOT_GENERATED",
              explanation_technique: null,
              explanation_technique_label: null,
              top_contributed_features: null,
              reasoning: null,
              reasoning_source: null,
              explanation_error: null,
              explained_at: null,
              created_at: run.created_at,
            }),
          ),
        },
      ],
    });
    apiMocks.explainHistoryPrediction.mockImplementation(
      async (predictionId: string) => ({
        transaction_id: 100,
        model_identifier:
          predictionId === "prediction-1" ? "catboost.v2" : "lightgbm.v2",
        method: "local_feature_contribution",
        explanation_technique: "shap",
        explanation_technique_label: "SHAP feature contributions",
        important_features: [],
        behavioral_explanation: null,
        behavioral_explanation_source: null,
      }),
    );

    render(<AnalysisHistory mode="single" />);
    await userEvent.click(
      await screen.findByRole("button", { name: /Single JSON/ }),
    );
    expect(await screen.findByText("FRAUD")).toBeVisible();
    await userEvent.click(await screen.findByRole("button", { name: /100/ }));

    await waitFor(() =>
      expect(apiMocks.explainHistoryPrediction).toHaveBeenCalledTimes(2),
    );
    expect(screen.getByText("CatBoost.V2")).toBeVisible();
    expect(screen.getByText("LightGBM.V2")).toBeVisible();
    expect(
      screen.getByRole("columnheader", { name: "Analyzed at" }),
    ).toBeVisible();
  });
});
