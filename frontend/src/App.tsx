import { useEffect, useMemo, useState } from "react";
import "./App.css";

type DualControlRequest = {
  id: string;
  entityId: string;
  entityType: string;
  action: string;
  requestedBy: string;
  context?: Record<string, unknown>;
};

type UserSummary = {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:9090/api";

async function apiFetch<TResponse>(
  path: string,
  init?: RequestInit,
): Promise<TResponse> {
  const headers =
    init?.body !== undefined
      ? { "Content-Type": "application/json", ...(init.headers ?? {}) }
      : init?.headers;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      if (payload?.message) {
        message = payload.message;
      }
    } catch {
      // ignore JSON parsing errors for non-JSON responses
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}

const initialFormState = {
  reason: "",
  approverId: "",
  secondaryApproverId: "",
  rejectReason: "",
};

export default function App() {
  const [requests, setRequests] = useState<DualControlRequest[]>([]);
  const [approvers, setApprovers] = useState<UserSummary[]>([]);
  const [selectedRequestId, setSelectedRequestId] = useState<string>("");
  const [formState, setFormState] = useState(initialFormState);
  const [isLoading, setIsLoading] = useState(true);
  const [approveLoading, setApproveLoading] = useState(false);
  const [rejectLoading, setRejectLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [rejectError, setRejectError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const selectedRequest = useMemo(
    () => requests.find((req) => req.id === selectedRequestId),
    [requests, selectedRequestId],
  );

  const humanLabel = (user: UserSummary) =>
    `${user.firstName} ${user.lastName} (${user.email})`;

  const loadData = async () => {
    setIsLoading(true);
    setServerError(null);
    try {
      const [pending, approved] = await Promise.all([
        apiFetch<DualControlRequest[]>("/dual-control/requests"),
        apiFetch<UserSummary[]>("/users/approved"),
      ]);
      setRequests(pending);
      setApprovers(approved);
      if (!selectedRequestId && pending.length) {
        setSelectedRequestId(pending[0].id);
      } else if (pending.length === 0) {
        setSelectedRequestId("");
      }
    } catch (error) {
      setServerError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!approvers.length) {
      return;
    }
    setFormState((prev) => {
      const primary = prev.approverId || approvers[0].id;
      const fallbackSecondary =
        approvers.find((user) => user.id !== primary)?.id ?? "";
      const secondary =
        prev.secondaryApproverId && prev.secondaryApproverId !== primary
          ? prev.secondaryApproverId
          : fallbackSecondary;
      return {
        ...prev,
        approverId: primary,
        secondaryApproverId: secondary,
      };
    });
  }, [approvers]);

  const resetMessages = () => {
    setFormError(null);
    setRejectError(null);
    setServerError(null);
    setSuccessMessage(null);
  };

  const handleApprove = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    resetMessages();
    if (!selectedRequest) {
      setFormError("Please select a request first.");
      return;
    }
    if (!formState.reason || formState.reason.trim().length < 5) {
      setFormError("Reason must be at least 5 characters.");
      return;
    }
    if (!formState.approverId || !formState.secondaryApproverId) {
      setFormError("Both primary and secondary approvers are required.");
      return;
    }
    if (formState.approverId === formState.secondaryApproverId) {
      setFormError("Secondary approver must differ from the primary approver.");
      return;
    }

    setApproveLoading(true);
    try {
      await apiFetch(`/users/${selectedRequest.entityId}/approve`, {
        method: "POST",
        body: JSON.stringify({
          dualControlRequestId: selectedRequest.id,
          approverId: formState.approverId,
          secondaryApproverId: formState.secondaryApproverId,
          reason: formState.reason.trim(),
        }),
      });
      setSuccessMessage("Request approved and audit log updated.");
      setFormState((prev) => ({ ...prev, reason: "", rejectReason: "" }));
      await loadData();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : String(error));
    } finally {
      setApproveLoading(false);
    }
  };

  const handleReject = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    resetMessages();
    if (!selectedRequest) {
      setRejectError("Please select a request first.");
      return;
    }
    if (!formState.approverId) {
      setRejectError("Primary approver is required.");
      return;
    }
    if (!formState.rejectReason || formState.rejectReason.trim().length < 5) {
      setRejectError("Rejection reason must be at least 5 characters.");
      return;
    }

    setRejectLoading(true);
    try {
      await apiFetch(`/users/${selectedRequest.entityId}/reject`, {
        method: "POST",
        body: JSON.stringify({
          dualControlRequestId: selectedRequest.id,
          approverId: formState.approverId,
          reason: formState.rejectReason.trim(),
        }),
      });
      setSuccessMessage("Request rejected and audit log updated.");
      setFormState((prev) => ({ ...prev, rejectReason: "" }));
      await loadData();
    } catch (error) {
      setRejectError(error instanceof Error ? error.message : String(error));
    } finally {
      setRejectLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">USDT Trading Assistant</p>
          <h1>Dual-Control Ops Console</h1>
          <p className="subtitle">
            Every approval now requires a reason and a secondary approver.
          </p>
        </div>
        <button className="ghost-button" onClick={loadData} disabled={isLoading}>
          Refresh Data
        </button>
      </header>

      {serverError && <div className="error-banner">{serverError}</div>}
      {successMessage && <div className="success-banner">{successMessage}</div>}

      <section className="panel">
        <h2>Pending Requests</h2>
        {isLoading ? (
          <p className="muted">Loading pending requests…</p>
        ) : requests.length === 0 ? (
          <p className="muted">No outstanding requests 🎉</p>
        ) : (
          <ul className="request-list">
            {requests.map((request) => {
              const rawEmail = request.context?.email;
              const contextEmail =
                typeof rawEmail === "string" ? rawEmail : undefined;
              return (
                <li key={request.id}>
                  <label>
                    <input
                      type="radio"
                      name="selectedRequest"
                      value={request.id}
                      checked={selectedRequestId === request.id}
                      onChange={(event) =>
                        setSelectedRequestId(event.target.value)
                      }
                    />
                    <div>
                      <strong>{contextEmail ?? request.entityId}</strong>
                      <span>
                        {request.action} ??? Requested by {request.requestedBy}
                      </span>
                    </div>
                  </label>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="panel">
        <h2>Dual Approval Form</h2>
        <form className="form-grid" onSubmit={handleApprove}>
          <label>
            Primary approver
            <select
              value={formState.approverId}
              onChange={(event) => {
                const newApprover = event.target.value;
                setFormState((prev) => ({
                  ...prev,
                  approverId: newApprover,
                  secondaryApproverId:
                    prev.secondaryApproverId === newApprover
                      ? approvers.find((user) => user.id !== newApprover)?.id ??
                        ""
                      : prev.secondaryApproverId,
                }));
              }}
            >
              {approvers.map((user) => (
                <option key={user.id} value={user.id}>
                  {humanLabel(user)}
                </option>
              ))}
            </select>
          </label>

          <label>
            Secondary approver
            <select
              value={formState.secondaryApproverId}
              onChange={(event) =>
                setFormState((prev) => ({
                  ...prev,
                  secondaryApproverId: event.target.value,
                }))
              }
            >
              <option value="">Select an approver</option>
              {approvers
                .filter((user) => user.id !== formState.approverId)
                .map((user) => (
                  <option key={user.id} value={user.id}>
                    {humanLabel(user)}
                  </option>
                ))}
            </select>
          </label>

          <label className="full-width">
            Approval reason
            <textarea
              value={formState.reason}
              placeholder="Example: 24/7 coverage required for settlements"
              onChange={(event) =>
                setFormState((prev) => ({ ...prev, reason: event.target.value }))
              }
            />
          </label>

          {formError && <p className="error-text">{formError}</p>}

          <button
            type="submit"
            className="primary-button"
            disabled={approveLoading || !requests.length}
          >
            {approveLoading ? "Submitting…" : "Approve request"}
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>Reject Request</h2>
        <form className="form-grid" onSubmit={handleReject}>
          <label className="full-width">
            Rejection reason
            <textarea
              value={formState.rejectReason}
              placeholder="Example: Missing documentation or escalated risk"
              onChange={(event) =>
                setFormState((prev) => ({
                  ...prev,
                  rejectReason: event.target.value,
                }))
              }
            />
          </label>
          {rejectError && <p className="error-text">{rejectError}</p>}
          <button
            type="submit"
            className="danger-button"
            disabled={rejectLoading || !requests.length}
          >
            {rejectLoading ? "Rejecting…" : "Reject and log"}
          </button>
        </form>
      </section>
    </main>
  );
}
