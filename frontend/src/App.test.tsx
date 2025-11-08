import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const dualControlResponse = [
  {
    id: "req-1",
    entityId: "user-1",
    entityType: "user",
    action: "user_activation",
    requestedBy: "ops@example.com",
    context: { email: "pending@example.com" },
  },
];

const approvedUsers = [
  {
    id: "approver-1",
    firstName: "Ops",
    lastName: "Lead",
    email: "lead@example.com",
  },
  {
    id: "approver-2",
    firstName: "Ops",
    lastName: "Backup",
    email: "backup@example.com",
  },
];

const mockResponse = (
  body: unknown,
  ok = true,
  status = 200,
): Response =>
  ({
    ok,
    status,
    json: async () => body,
  }) as Response;

describe("Ops console", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("validates approval reason", async () => {
    fetchMock
      .mockResolvedValueOnce(mockResponse(dualControlResponse))
      .mockResolvedValueOnce(mockResponse(approvedUsers));

    render(<App />);

    await waitFor(() =>
      expect(screen.getByText(/pending@example.com/i)).toBeInTheDocument(),
    );

    await userEvent.click(
      screen.getByRole("button", { name: /approve request/i }),
    );

    expect(
      await screen.findByText(/reason must be at least 5 characters/i),
    ).toBeVisible();
  });

  it("submits approval and refreshes list", async () => {
    fetchMock
      .mockResolvedValueOnce(mockResponse(dualControlResponse)) // initial requests
      .mockResolvedValueOnce(mockResponse(approvedUsers)) // initial approvers
      .mockResolvedValueOnce(mockResponse({ id: "user-1" })) // approve POST
      .mockResolvedValueOnce(mockResponse([])) // refresh requests
      .mockResolvedValueOnce(mockResponse(approvedUsers)); // refresh approvers

    render(<App />);
    await waitFor(() =>
      expect(screen.getByText(/pending@example.com/i)).toBeInTheDocument(),
    );

    await userEvent.type(
      screen.getByLabelText(/approval reason/i),
      "Need coverage",
    );
    await userEvent.click(
      screen.getByRole("button", { name: /approve request/i }),
    );

    await waitFor(() =>
      expect(
        screen.getByText(/request approved and audit log updated/i),
      ).toBeInTheDocument(),
    );

    // ensure POST call payload contains reason and secondary approver
    const payloads = fetchMock.mock.calls
      .map(([, init]) => init?.body)
      .filter((body): body is string => typeof body === "string");
    expect(
      payloads.some((body) => body.includes("Need coverage")),
    ).toBe(true);
  });
});
