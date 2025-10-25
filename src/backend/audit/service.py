"""
Audit Trail Service - Stage 23
Handles immutable event logging with trace ID and hash verification.
"""
import json
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from .schemas import AuditEvent, EventType, ActorRole, EventReplayTimeline, EventReplayResponse


# Log file paths
LOGS_DIR = Path("logs")
AUDIT_LOG_FILE = LOGS_DIR / "audit_events.json"


def _ensure_logs_dir():
    """Ensure logs directory exists"""
    LOGS_DIR.mkdir(exist_ok=True)


def _compute_event_hash(event_data: Dict[str, Any]) -> str:
    """
    Compute SHA-256 hash of event for immutability verification.
    Hash is computed from: event_id + event_type + actor_id + trace_id + created_at + metadata
    """
    hash_input = (
        str(event_data.get("event_id", "")) +
        str(event_data.get("event_type", "")) +
        str(event_data.get("actor_id", "")) +
        str(event_data.get("trace_id", "")) +
        str(event_data.get("created_at", "")) +
        json.dumps(event_data.get("metadata", {}), sort_keys=True)
    )
    return hashlib.sha256(hash_input.encode()).hexdigest()


def log_event(
    event_type: str,
    actor_id: str,
    actor_role: str,
    trace_id: str,
    previous_status: Optional[str] = None,
    new_status: Optional[str] = None,
    decision_reason: Optional[str] = None,
    evidence_links: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AuditEvent:
    """
    Log an immutable audit event.

    Args:
        event_type: Type of event (e.g., "rfq_created", "award_selected_auto")
        actor_id: ID of actor (e.g., "telegram:123456", "system:auto_engine")
        actor_role: Role of actor (customer, provider, admin, system, etc.)
        trace_id: Trace ID linking all events in RFQ lifecycle
        previous_status: Previous state before this event (optional)
        new_status: New state after this event (optional)
        decision_reason: Human-readable reason for decision (optional)
        evidence_links: Links to supporting evidence (optional)
        metadata: Event-specific data (optional)

    Returns:
        AuditEvent: The logged event

    Example:
        log_event(
            event_type="rfq_created",
            actor_id="telegram:123456",
            actor_role="customer",
            trace_id="7c3a4f21-1234-5678-9abc-def012345678",
            metadata={"rfq_id": "uuid", "amount": 100.0}
        )
    """
    _ensure_logs_dir()

    # Generate event ID
    event_id = str(uuid.uuid4())

    # Create event data (without hash first)
    event_data = {
        "event_id": event_id,
        "event_type": event_type,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "trace_id": trace_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "previous_status": previous_status,
        "new_status": new_status,
        "decision_reason": decision_reason,
        "evidence_links": evidence_links,
        "metadata": metadata or {}
    }

    # Compute hash
    event_hash = _compute_event_hash(event_data)
    event_data["event_hash"] = event_hash

    # Create Pydantic model for validation
    event = AuditEvent(**event_data)

    # Append to JSON Lines file (one event per line)
    with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(event.model_dump_json() + "\n")

    return event


def query_events(
    trace_id: Optional[str] = None,
    event_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    limit: Optional[int] = None
) -> List[AuditEvent]:
    """
    Query events from audit log.

    Args:
        trace_id: Filter by trace ID
        event_type: Filter by event type
        actor_id: Filter by actor ID
        limit: Maximum number of events to return

    Returns:
        List of matching events, ordered by created_at ASC
    """
    if not AUDIT_LOG_FILE.exists():
        return []

    events = []

    with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                event_data = json.loads(line.strip())
                event = AuditEvent(**event_data)

                # Apply filters
                if trace_id and event.trace_id != trace_id:
                    continue
                if event_type and event.event_type != event_type:
                    continue
                if actor_id and event.actor_id != actor_id:
                    continue

                events.append(event)

                # Apply limit
                if limit and len(events) >= limit:
                    break
            except Exception:
                # Skip malformed lines
                continue

    # Sort by created_at
    events.sort(key=lambda e: e.created_at)

    return events


def replay_events(trace_id: str) -> EventReplayResponse:
    """
    Replay all events for a specific trace ID to reconstruct full timeline.

    Args:
        trace_id: Trace ID to replay

    Returns:
        EventReplayResponse with full timeline

    Example:
        >>> replay = replay_events("7c3a4f21-1234-5678-9abc-def012345678")
        >>> for entry in replay.timeline:
        ...     print(f"[{entry.timestamp}] {entry.event_type} → {entry.state_after}")
    """
    events = query_events(trace_id=trace_id)

    timeline = []
    current_state = {"status": "draft"}

    for event in events:
        # Update state if new_status present
        if event.new_status:
            current_state["status"] = event.new_status

        # Add metadata to current state
        if event.metadata:
            for key, value in event.metadata.items():
                if key not in current_state:
                    current_state[key] = value

        timeline.append(EventReplayTimeline(
            timestamp=event.created_at,
            event_type=event.event_type,
            actor=f"{event.actor_role}:{event.actor_id}",
            state_after=current_state.copy(),
            decision_reason=event.decision_reason
        ))

    return EventReplayResponse(
        trace_id=trace_id,
        total_events=len(events),
        timeline=timeline
    )


def verify_event_integrity(event: AuditEvent) -> bool:
    """
    Verify that event has not been tampered with.

    Args:
        event: Event to verify

    Returns:
        True if hash matches, False otherwise
    """
    stored_hash = event.event_hash

    # Recreate event data without hash (use mode='json' to serialize enums to values)
    event_data = event.model_dump(mode='json')
    event_data.pop("event_hash", None)

    # created_at is already serialized to ISO string by mode='json'

    computed_hash = _compute_event_hash(event_data)

    return computed_hash == stored_hash


def get_event_statistics() -> Dict[str, Any]:
    """
    Get statistics about logged events.

    Returns:
        Dictionary with event counts by type, unique traces, etc.
    """
    if not AUDIT_LOG_FILE.exists():
        return {"total_events": 0, "unique_traces": 0, "events_by_type": {}}

    events = query_events()

    event_types = {}
    unique_traces = set()

    for event in events:
        # Count by type
        event_type_str = str(event.event_type)
        event_types[event_type_str] = event_types.get(event_type_str, 0) + 1

        # Collect unique traces
        unique_traces.add(event.trace_id)

    return {
        "total_events": len(events),
        "unique_traces": len(unique_traces),
        "events_by_type": event_types
    }
