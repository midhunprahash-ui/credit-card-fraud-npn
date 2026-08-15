import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ModelComparisonPage } from "./ModelComparisonPage";

vi.mock("../api/client", () => ({
  api: {
    models: vi.fn(async () => ({
      versions: ["V1", "V2"],
      models: [
        {
          model_key: "catboost",
          model_identifier: "catboost.v2",
          model_name: "CatBoost.V2",
          display_name: "CatBoost",
          version_name: "V2",
          run_id: "run-v2",
          threshold: 0.02,
          champion: true,
          validation_pr_auc: 0.725,
          test_pr_auc: 0.607,
          loading_status: "not_loaded",
          metrics: {
            validation: null,
            test: {
              pr_auc: 0.607,
              roc_auc: 0.922,
              precision: 0.084,
              recall: 0.935,
              f1: 0.154,
              threshold: 0.02,
              confusion_matrix: [
                [53930, 31568],
                [201, 2882],
              ],
              rows: 88581,
            },
            training_seconds: 812,
            prediction_latency_ms: null,
          },
          feature_importance_available: true,
          top_features: [
            { feature: "uid_proxy", value: 8.58, kind: "importance" },
          ],
        },
      ],
    })),
  },
}));

describe("ModelComparisonPage", () => {
  beforeEach(() => vi.clearAllMocks());
  it("explains rare-fraud selection and test-set governance", async () => {
    render(<ModelComparisonPage />);
    expect((await screen.findAllByText("CatBoost.V2")).length).toBeGreaterThan(
      0,
    );
    expect(screen.getByText(/PR-AUC leads/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Test metrics are final reporting only/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Version champion")).toBeInTheDocument();
  });
});
