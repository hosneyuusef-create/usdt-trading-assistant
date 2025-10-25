"""
Audit Trail API - Stage 23
Provides endpoints for querying audit events and replaying scenarios.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query

from ..security.rbac.dependencies import require_permission
from .service import (
    query_events, replay_events, get_event_statistics,
    verify_event_integrity, get_dashboard_metrics
)
from .schemas import AuditEvent, EventReplayResponse, DashboardResponse

router = APIRouter(prefix="/audit", tags=["Audit Trail"])


@router.get("/events", response_model=List[AuditEvent])
def get_events(
    trace_id: Optional[str] = Query(None, description="Filter by trace ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
    _: None = Depends(require_permission("audit:read"))
):
    """
    Query audit events with filters.

    **Permissions required:** audit:read (admin, operations, compliance)

    **Examples:**
    - Get all events for a trace: `GET /audit/events?trace_id=7c3a4f21...`
    - Get all RFQ creations: `GET /audit/events?event_type=rfq_created&limit=50`
    - Get all events by an actor: `GET /audit/events?actor_id=telegram:123456`
    """
    events = query_events(
        trace_id=trace_id,
        event_type=event_type,
        actor_id=actor_id,
        limit=limit
    )
    return events


@router.get("/replay/{trace_id}", response_model=EventReplayResponse)
def replay_scenario(
    trace_id: str,
    _: None = Depends(require_permission("audit:read"))
):
    """
    Replay all events for a specific RFQ/order trace to reconstruct full timeline.

    **Permissions required:** audit:read (admin, operations, compliance)

    **Use cases:**
    - Dispute investigation: Reconstruct full RFQ lifecycle
    - Debugging: Understand state transitions
    - Compliance: Audit trail verification

    **Example:**
    ```
    GET /audit/replay/7c3a4f21-1234-5678-9abc-def012345678

    Response:
    {
      "trace_id": "7c3a4f21...",
      "total_events": 8,
      "timeline": [
        {
          "timestamp": "2025-10-24T12:00:00Z",
          "event_type": "rfq_created",
          "actor": "customer:telegram:123456",
          "state_after": {"status": "open"},
          "decision_reason": null
        },
        ...
      ]
    }
    ```
    """
    return replay_events(trace_id)


@router.get("/statistics")
def get_statistics(
    _: None = Depends(require_permission("audit:read"))
):
    """
    Get audit log statistics.

    **Permissions required:** audit:read (admin, operations, compliance)

    Returns:
    - Total events logged
    - Unique trace IDs (RFQs/orders)
    - Event counts by type
    """
    return get_event_statistics()


@router.post("/verify")
def verify_integrity(
    event: AuditEvent,
    _: None = Depends(require_permission("audit:read"))
):
    """
    Verify integrity of an event by checking its hash.

    **Permissions required:** audit:read

    Returns:
    - `valid`: True if event hash matches computed hash
    - `message`: Verification result message
    """
    is_valid = verify_event_integrity(event)

    return {
        "valid": is_valid,
        "message": "Event integrity verified" if is_valid else "Event hash mismatch - possible tampering"
    }


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    _: None = Depends(require_permission("audit:read"))
):
    """
    Get notification performance dashboard with metrics and threshold alerts.

    **Permissions required:** audit:read (admin, operations, compliance)

    Returns:
    - Notification metrics: p95/p99/avg latency, failure rate
    - Active alerts: threshold violations (warning, critical)

    **Thresholds:**
    - Failure rate: warning @ 5%, critical @ 10%
    - P95 latency: warning @ 2000ms, critical @ 5000ms

    **Example response:**
    ```json
    {
      "notification_metrics": {
        "total_sent": 1000,
        "total_delivered": 950,
        "total_failed": 50,
        "failure_rate": 0.05,
        "p95_latency_ms": 1500.5,
        "p99_latency_ms": 2300.2,
        "avg_latency_ms": 800.1
      },
      "alerts": [
        {
          "metric_name": "notification_failure_rate",
          "current_value": 0.05,
          "threshold_value": 0.05,
          "severity": "warning",
          "message": "WARNING: Notification failure rate is 5.00%, exceeds warning threshold of 5.00%"
        }
      ]
    }
    ```
    """
    return get_dashboard_metrics()
