import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LiveAnalysisPage } from "./LiveAnalysisPage";

describe("Fraud prediction workspace", () => {
  it("offers JSON, CSV, and real-time input without analyst navigation", async () => {
    render(
      <LiveAnalysisPage
        filters={{ versions: ["V2"], models: ["lightgbm.v2"] }}
        onFiltersChange={vi.fn()}
      />,
    );

    expect(screen.getByRole("tab", { name: "Single JSON" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("tab", { name: "CSV Upload" })).toBeVisible();
    expect(screen.getByRole("tab", { name: "Real-time" })).toBeVisible();
    expect(screen.getByLabelText("JSON input")).toBeVisible();

    await userEvent.click(screen.getByRole("tab", { name: "CSV Upload" }));
    expect(screen.getByText("Choose a CSV file")).toBeVisible();
  });
});
