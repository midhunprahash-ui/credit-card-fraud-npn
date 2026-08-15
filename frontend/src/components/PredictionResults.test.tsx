import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { PredictionResponse } from "../api/types";
import { PredictionResults } from "./PredictionResults";

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
  it("labels model disagreement as a visual summary, not an ensemble", () => {
    render(<PredictionResults prediction={prediction} />);
    expect(screen.getByText("Model disagreement")).toBeInTheDocument();
    expect(screen.getByText(/not a trained ensemble/i)).toBeInTheDocument();
    expect(screen.getAllByText("Fraud-risk score")).toHaveLength(2);
    expect(screen.getByText("CatBoost.V2")).toBeInTheDocument();
  });
});
