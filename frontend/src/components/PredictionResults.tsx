import type { PredictionResponse } from "../api/types";
import { formatLatency, formatPercent } from "../utils/format";
import { Panel, RiskScore, StatusBadge } from "./ui";

export function PredictionResults({
  prediction,
}: {
  prediction: PredictionResponse;
}) {
  return (
    <div className="prediction-output" aria-live="polite">
      <Panel
        title="Model agreement"
        eyebrow={`Transaction ${prediction.transaction_id}`}
      >
        <div className="agreement-row">
          <div
            className="vote-ring"
            style={
              {
                "--votes":
                  prediction.agreement.fraud_vote_count /
                  prediction.agreement.selected_model_count,
              } as React.CSSProperties
            }
          >
            <strong>
              {prediction.agreement.fraud_vote_count}/
              {prediction.agreement.selected_model_count}
            </strong>
            <span>flag fraud</span>
          </div>
          <div>
            <StatusBadge
              tone={prediction.agreement.unanimous ? "low" : "review"}
            >
              {prediction.agreement.unanimous
                ? "Models agree"
                : "Model disagreement"}
            </StatusBadge>
            <p className="muted">
              Visual vote summary only—not a trained ensemble.
            </p>
            <p className="muted">
              Input completeness: {formatPercent(prediction.input_completeness)}
            </p>
          </div>
        </div>
      </Panel>
      <div className="result-grid">
        {prediction.results.map((result) => (
          <article
            className={`result-card ${result.decision ? "result-high" : "result-low"}`}
            key={result.model_identifier}
          >
            <header>
              <div>
                <span className="model-version">{result.model_version}</span>
                <h3>{result.model_name}</h3>
              </div>
              {result.champion ? (
                <StatusBadge tone="high">Champion</StatusBadge>
              ) : null}
            </header>
            <div className="result-score">
              <span>Fraud-risk score</span>
              <RiskScore score={result.risk_score} />
            </div>
            <dl className="result-details">
              <div>
                <dt>Decision</dt>
                <dd>
                  <StatusBadge tone={result.decision ? "high" : "low"}>
                    {result.decision ? "Fraud" : "Legitimate"}
                  </StatusBadge>
                </dd>
              </div>
              <div>
                <dt>Saved threshold</dt>
                <dd>{result.threshold.toFixed(6)}</dd>
              </div>
              <div>
                <dt>Prediction latency</dt>
                <dd>{formatLatency(result.latency_ms)}</dd>
              </div>
              <div>
                <dt>Run ID</dt>
                <dd className="mono">{result.run_id}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </div>
  );
}
