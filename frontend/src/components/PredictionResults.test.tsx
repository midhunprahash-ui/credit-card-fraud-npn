import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { PredictionResponse } from "../api/types";
import { PredictionResults } from "./PredictionResults";

vi.mock("../api/client", () => ({
  api: {
    explain: vi.fn().mockResolvedValue({
      transaction_id: 3488959,
      model_identifier: "lightgbm.v1",
      method: "local_feature_contribution",
      explanation_technique: "shap",
      explanation_technique_label: "SHAP feature contributions",
      important_features: [
        {
          feature: "TransactionAmt",
          contribution: 0.12,
          direction: "toward_fraud",
        },
      ],
    }),
  },
}));

const prediction: PredictionResponse = {
  transaction_id: 3488959,
  input_completeness: 0.82,
  agreement: {
    fraud_vote_count: 1,
    selected_model_count: 2,
    unanimous: false,
    agreement_label: "disagreement",
  },
  results: [
    {
      model_identifier: "lightgbm.v1",
      model_name: "LightGBM.V1",
      model_version: "V1",
      run_id: "run-1",
      risk_score: 0.91,
      threshold: 0.1,
      decision: true,
      decision_label: "fraud",
      latency_ms: 4.2,
      champion: false,
      processing_status: "completed",
      important_features: null,
    },
    {
      model_identifier: "catboost.v2",
      model_name: "CatBoost.V2",
      model_version: "V2",
      run_id: "run-2",
      risk_score: 0.31,
      threshold: 0.4,
      decision: false,
      decision_label: "legitimate",
      latency_ms: 5.1,
      champion: true,
      processing_status: "completed",
      important_features: null,
    },
  ],
};

describe("PredictionResults", () => {
  it("shows every selected model in one simple classification table", () => {
    render(
      <PredictionResults
        prediction={prediction}
        input={{ TransactionID: 3488959, TransactionDT: 100 }}
      />,
    );
    expect(screen.getByRole("columnheader", { name: "Fraud" })).toBeVisible();
    expect(
      screen.getByRole("columnheader", { name: "Not fraud" }),
    ).toBeVisible();
    expect(screen.getByText("● FRAUD")).toBeVisible();
    expect(screen.getByText("● NOT FRAUD")).toBeVisible();
    expect(screen.getByText("CatBoost.V2")).toBeInTheDocument();
  });

  it("reveals transaction inputs and local features when a row is opened", async () => {
    render(
      <PredictionResults
        prediction={prediction}
        input={{
          TransactionID: 3488959,
          TransactionDT: 100,
          TransactionAmt: 57.95,
        }}
      />,
    );

    await userEvent.click(
      screen.getAllByRole("button", { name: /3488959/ })[0],
    );

    expect(
      await screen.findByText("Strongest decision features"),
    ).toBeVisible();
    expect(screen.getByText("Transaction inputs (3)")).toBeVisible();
    expect(screen.getAllByText("TransactionAmt")).toHaveLength(2);
    expect(await screen.findByText("Toward fraud")).toBeVisible();
    expect(
      screen.getByText("Explanation method: SHAP feature contributions"),
    ).toBeVisible();
  });
});
