import type { ModelIdentifier, VersionName } from "../api/types";

export const MODEL_OPTIONS: Array<{
  id: ModelIdentifier;
  name: string;
  version: VersionName;
}> = [
  {
    id: "logistic_regression.v1",
    name: "LogisticRegression.V1",
    version: "V1",
  },
  { id: "lightgbm.v1", name: "LightGBM.V1", version: "V1" },
  { id: "catboost.v1", name: "CatBoost.V1", version: "V1" },
  { id: "neural_network.v1", name: "NeuralNetwork.V1", version: "V1" },
  {
    id: "logistic_regression.v2",
    name: "LogisticRegression.V2",
    version: "V2",
  },
  { id: "lightgbm.v2", name: "LightGBM.V2", version: "V2" },
  { id: "catboost.v2", name: "CatBoost.V2", version: "V2" },
  { id: "neural_network.v2", name: "NeuralNetwork.V2", version: "V2" },
];

export const DEFAULT_MODELS: ModelIdentifier[] = [];

export function modelName(identifier: string): string {
  return (
    MODEL_OPTIONS.find((item) => item.id === identifier)?.name ?? identifier
  );
}
