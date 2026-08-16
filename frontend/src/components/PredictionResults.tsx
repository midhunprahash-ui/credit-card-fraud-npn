import type { PredictionResponse } from "../api/types";
import { PredictionTable } from "./PredictionTable";

export function PredictionResults({
  prediction,
  input,
}: {
  prediction: PredictionResponse;
  input: Record<string, unknown>;
}) {
  return (
    <div className="prediction-output" aria-live="polite">
      <PredictionTable
        rows={prediction.results.map((result) => ({
          key: `${prediction.transaction_id}-${result.model_identifier}`,
          transactionId: prediction.transaction_id,
          modelIdentifier: result.model_identifier,
          modelName: result.model_name,
          decision: result.decision,
          score: result.risk_score,
          threshold: result.threshold,
          input,
        }))}
      />
    </div>
  );
}
