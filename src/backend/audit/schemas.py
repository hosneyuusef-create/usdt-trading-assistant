"""
Pydantic schemas for Audit Events - Stage 23
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ActorRole(str, Enum):
    """Actor role enum"""
    CUSTOMER = "customer"
    PROVIDER = "provider"
    ADMIN = "admin"
    OPERATIONS = "operations"
    COMPLIANCE = "compliance"
    SYSTEM = "system"


class EventType(str, Enum):
    """Event type enum - all business events"""
    # RFQ events
    RFQ_CREATED = "rfq_created"
    RFQ_CANCELLED = "rfq_cancelled"

    # Quote events
    QUOTE_SUBMITTED = "quote_submitted"
    QUOTE_REJECTED = "quote_rejected"

    # Award events
    AWARD_SELECTED_AUTO = "award_selected_auto"
    AWARD_SELECTED_MANUAL = "award_selected_manual"

    # Settlement events
    SETTLEMENT_STARTED = "settlement_started"
    SETTLEMENT_FIAT_SUBMITTED = "settlement_fiat_submitted"
    SETTLEMENT_CRYPTO_SUBMITTED = "settlement_crypto_submitted"
    SETTLEMENT_COMPLETED = "settlement_completed"
    SETTLEMENT_FAILED = "settlement_failed"

    # Dispute events
    DISPUTE_OPENED = "dispute_opened"
    DISPUTE_EVIDENCE_SUBMITTED = "dispute_evidence_submitted"
    DISPUTE_RESOLVED = "dispute_resolved"

    # Config events
    CONFIG_UPDATED = "config_updated"
    CONFIG_ROLLED_BACK = "config_rolled_back"

    # Provider events
    PROVIDER_REGISTERED = "provider_registered"
    PROVIDER_SCORE_UPDATED = "provider_score_updated"

    # RBAC events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"


class AuditEvent(BaseModel):
    """
    Unified audit event schema for immutable event log.
    All events must conform to this schema.
    """
    # Required fields
    event_id: str = Field(..., description="Unique UUID for this event")
    event_type: EventType = Field(..., description="Type of business event")
    actor_id: str = Field(..., description="ID of actor (telegram:123456, system:auto_engine)")
    actor_role: ActorRole = Field(..., description="Role of the actor")
    trace_id: str = Field(..., description="Trace ID linking all events in RFQ lifecycle")
    created_at: datetime = Field(..., description="Event timestamp (UTC)")
    event_hash: str = Field(..., description="SHA-256 hash for immutability")

    # Optional fields for state transitions
    previous_status: Optional[str] = Field(None, description="Previous state")
    new_status: Optional[str] = Field(None, description="New state after event")
    decision_reason: Optional[str] = Field(None, description="Reason for decision/action")
    evidence_links: Optional[List[str]] = Field(None, description="Links to supporting evidence")

    # Event-specific metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Event-specific data")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EventReplayTimeline(BaseModel):
    """Timeline entry for event replay"""
    timestamp: datetime
    event_type: EventType
    actor: str
    state_after: Dict[str, Any]
    decision_reason: Optional[str] = None


class EventReplayResponse(BaseModel):
    """Response for event replay query"""
    trace_id: str
    total_events: int
    timeline: List[EventReplayTimeline]
