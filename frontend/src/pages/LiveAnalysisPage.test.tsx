import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { StreamMessage } from "../api/client";
import { LiveAnalysisPage } from "./LiveAnalysisPage";

const apiMocks = vi.hoisted(() => ({
  streamEventHandler: null as ((message: StreamMessage) => void) | null,
  streamStart: vi.fn(),
}));

vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  const streamStatus = {
    stream_run_id: null,
    dataset_id: "demo",
    status: "IDLE" as const,
    selected_versions: [],
    selected_models: [],
    transactions_per_second: 1,
    transactions_received: 0,
    transactions_processed: 0,
    transactions_queued: 0,
    currently_processing: null,
    current_sequence: -1,
    current_throughput: 0,
    average_latency_ms: 0,
    p95_latency_ms: 0,
    fraud_alerts: 0,
    suspicious_transaction_value: 0,
    failed_transactions: 0,
    unpersisted_transactions: 0,
    started_at: null,
    completed_at: null,
  };
  apiMocks.streamStart.mockResolvedValue({
    ...streamStatus,
    stream_run_id: "run-1",
    status: "RUNNING",
  });
  return {
    ...original,
    api: {
      ...original.api,
      demoTransactions: vi.fn().mockResolvedValue({
        dataset: "kaggle_inference_sample",
        split: "kaggle_inference",
        labels_available: false,
        transactions: [{ transaction_id: 3663549 }],
      }),
      transaction: vi.fn().mockResolvedValue({
        labels_available: false,
        transaction_payload: {
          TransactionID: 3663549,
          TransactionDT: 18403224,
          TransactionAmt: 31.95,
          ProductCD: "W",
        },
      }),
      streamDatasets: vi.fn().mockResolvedValue({
        datasets: [
          {
            id: "demo",
            name: "Demo",
            split: "held_out",
            schema_version: "v1",
            row_count: 600,
            fraud_count: 21,
            fraud_rate: 0.035,
            labels_available: true,
            description: null,
            status: "READY",
          },
        ],
      }),
      streamStatus: vi.fn().mockResolvedValue(streamStatus),
      streamStart: apiMocks.streamStart,
    },
    subscribeToStream: vi.fn((handler: (message: StreamMessage) => void) => {
      apiMocks.streamEventHandler = handler;
      return vi.fn();
    }),
  };
});

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
    await waitFor(() =>
      expect(
        screen.getByDisplayValue(/"TransactionID": 3663549/),
      ).toBeVisible(),
    );

    await userEvent.click(screen.getByRole("tab", { name: "CSV Upload" }));
    expect(screen.getByText("Choose a CSV file")).toBeVisible();
  });

  it("stays rendered when a transaction-processing SSE event arrives", async () => {
    render(
      <LiveAnalysisPage
        filters={{ versions: ["V2"], models: ["lightgbm.v2"] }}
        onFiltersChange={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("tab", { name: "Real-time" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Start" })).toBeEnabled(),
    );
    await userEvent.click(screen.getByRole("button", { name: "Start" }));

    await waitFor(() => expect(screen.getByText("RUNNING")).toBeVisible());
    act(() => {
      apiMocks.streamEventHandler?.({
        type: "transaction_processing",
        data: {
          sequence_number: 0,
          transaction_id: 3488959,
          processing_started_at: "2026-08-16T00:00:00Z",
          status: "PROCESSING",
        },
      });
    });

    expect(screen.getByText("RUNNING")).toBeVisible();
    expect(screen.getByText("0.00 TPS")).toBeVisible();

    act(() => {
      apiMocks.streamEventHandler?.({
        type: "transaction_completed",
        data: {
          sequence_number: 0,
          transaction_id: 3663549,
          arrival_time: "2026-08-16T00:00:00Z",
          queue_position: 1,
          processing_started_at: "2026-08-16T00:00:00Z",
          completed_at: "2026-08-16T00:00:01Z",
          status: "COMPLETED",
          actual_label: null,
          results: [],
          agreement: null,
          latency_ms: 10,
          queue_length: 0,
          error_code: null,
        },
      });
    });
    expect(screen.getByText("Not available")).toBeVisible();
  });
});
