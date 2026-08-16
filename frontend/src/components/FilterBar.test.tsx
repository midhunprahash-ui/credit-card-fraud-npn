import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FilterBar } from "./FilterBar";

describe("FilterBar", () => {
  it("shows only models from selected versions", () => {
    render(
      <FilterBar
        versions={["V2"]}
        models={["catboost.v2"]}
        locked={false}
        onVersionsChange={vi.fn()}
        onModelsChange={vi.fn()}
      />,
    );
    expect(screen.getByText("CatBoost.V2")).toBeInTheDocument();
    expect(screen.queryByText("CatBoost.V1")).not.toBeInTheDocument();
  });

  it("locks configuration while a stream is running", async () => {
    render(
      <FilterBar
        versions={["V1", "V2"]}
        models={["catboost.v2"]}
        locked
        onVersionsChange={vi.fn()}
        onModelsChange={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByLabelText("V1"));
    expect(screen.getByLabelText("V1")).toBeChecked();
    expect(screen.getByText("Configuration locked")).toBeInTheDocument();
  });
});
