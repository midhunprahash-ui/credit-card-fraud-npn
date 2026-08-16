import type { ModelIdentifier, VersionName } from "../api/types";
import { MODEL_OPTIONS } from "../config/models";
import { StatusBadge } from "./ui";

export function FilterBar({
  versions,
  models,
  locked,
  onVersionsChange,
  onModelsChange,
}: {
  versions: VersionName[];
  models: ModelIdentifier[];
  locked: boolean;
  onVersionsChange: (versions: VersionName[]) => void;
  onModelsChange: (models: ModelIdentifier[]) => void;
}) {
  const visibleModels = MODEL_OPTIONS.filter((model) =>
    versions.includes(model.version),
  );
  function toggleVersion(version: VersionName) {
    if (locked) return;
    const next = versions.includes(version)
      ? versions.filter((item) => item !== version)
      : [...versions, version];
    if (!next.length) return;
    onVersionsChange(next);
    onModelsChange(
      models.filter((identifier) => {
        const option = MODEL_OPTIONS.find((item) => item.id === identifier);
        return option ? next.includes(option.version) : false;
      }),
    );
  }
  function toggleModel(identifier: ModelIdentifier) {
    if (locked) return;
    onModelsChange(
      models.includes(identifier)
        ? models.filter((item) => item !== identifier)
        : [...models, identifier],
    );
  }
  return (
    <section
      className={`filter-bar ${locked ? "filter-locked" : ""}`}
      aria-label="Prediction configuration"
    >
      <fieldset>
        <legend>Version</legend>
        <div className="chip-group">
          {(["V1", "V2"] as VersionName[]).map((version) => (
            <label
              className={`filter-chip ${versions.includes(version) ? "selected" : ""}`}
              key={version}
            >
              <input
                type="checkbox"
                checked={versions.includes(version)}
                disabled={locked}
                onChange={() => toggleVersion(version)}
              />
              {version}
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset className="model-filter">
        <legend>Models</legend>
        <div className="chip-group scroll-chips">
          {visibleModels.map((model) => (
            <label
              className={`filter-chip model-chip ${models.includes(model.id) ? "selected" : ""}`}
              key={model.id}
            >
              <input
                type="checkbox"
                checked={models.includes(model.id)}
                disabled={locked}
                onChange={() => toggleModel(model.id)}
              />
              {model.name}
            </label>
          ))}
        </div>
      </fieldset>
      {locked ? (
        <StatusBadge tone="review">Configuration locked</StatusBadge>
      ) : null}
    </section>
  );
}
