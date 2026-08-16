import type { PredictionResponse } from "../api/types";
import { formatLatency } from "../utils/format";
import { Panel, RiskScore, StatusBadge } from "./ui";

export function PredictionResults({
  prediction,
}: {
  prediction: PredictionResponse;
}) {
  return (
    <div className="prediction-output" aria-live="polite">
      <Panel
        title="Prediction"
        eyebrow={`Transaction ${prediction.transaction_id}`}
      >
        <div className="prediction-summary">
          <strong>
            {prediction.agreement.fraud_vote_count} of{" "}
            {prediction.agreement.selected_model_count} models predicted fraud
          </strong>
          <StatusBadge tone={prediction.agreement.unanimous ? "low" : "review"}>
            {prediction.agreement.unanimous ? "Models agree" : "Models differ"}
          </StatusBadge>
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
              <StatusBadge tone={result.decision ? "high" : "low"}>
                {result.decision ? "Fraud" : "Legitimate"}
              </StatusBadge>
            </header>
            <div className="result-score">
              <span>Fraud-risk score</span>
              <RiskScore score={result.risk_score} />
            </div>
            <dl className="result-details">
              <div>
                <dt>Decision</dt>
                <dd>{result.decision ? "Fraud" : "Legitimate"}</dd>
              </div>
              <div>
                <dt>Saved threshold</dt>
                <dd>{result.threshold.toFixed(6)}</dd>
              </div>
              <div>
                <dt>Prediction latency</dt>
                <dd>{formatLatency(result.latency_ms)}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </div>
  );
}
