"""
Configuration UI schemas for Stage 22 (M22)
Provides versioned configuration management with rollback capability
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Literal, Optional
from enum import Enum


class SettlementOrder(str, Enum):
    """Order of settlement legs"""
    FIAT_FIRST = "fiat_first"
    CRYPTO_FIRST = "crypto_first"


class ScoringWeights(BaseModel):
    """Weights for automatic provider scoring (Stage 20)"""
    success_rate: float = Field(0.4, ge=0, le=1, description="Weight for successful settlement rate")
    on_time_settlement: float = Field(0.3, ge=0, le=1, description="Weight for on-time settlement")
    dispute_ratio: float = Field(0.2, ge=0, le=1, description="Weight for dispute ratio (lower is better)")
    manual_alerts: float = Field(0.1, ge=0, le=1, description="Weight for manual alert ratio")

    @field_validator('success_rate', 'on_time_settlement', 'dispute_ratio', 'manual_alerts')
    @classmethod
    def check_sum(cls, v, info):
        """Ensure weights sum to 1.0"""
        return v

    def validate_sum(self) -> bool:
        """Check if all weights sum to 1.0"""
        total = self.success_rate + self.on_time_settlement + self.dispute_ratio + self.manual_alerts
        return abs(total - 1.0) < 0.001


class SystemConfiguration(BaseModel):
    """All configurable system parameters (Stage 22)"""

    # RFQ and bidding settings
    bidding_deadline_minutes: int = Field(10, ge=1, le=60, description="Default bidding deadline in minutes")
    min_valid_quotes: int = Field(2, ge=1, le=10, description="Minimum valid quotes required")
    allow_deadline_extension: bool = Field(True, description="Allow one-time deadline extension")

    # Settlement settings
    settlement_order: SettlementOrder = Field(SettlementOrder.FIAT_FIRST, description="Order of settlement legs")
    fiat_settlement_timeout_minutes: int = Field(15, ge=5, le=60, description="Timeout for fiat leg")
    crypto_settlement_timeout_minutes: int = Field(15, ge=5, le=60, description="Timeout for crypto leg")
    min_blockchain_confirmations: int = Field(1, ge=1, le=12, description="Minimum confirmations for blockchain transfers")

    # Network settings
    allowed_networks: List[str] = Field(["TRC20", "BEP20", "ERC20"], description="Allowed blockchain networks")

    # Provider eligibility settings
    min_provider_score: int = Field(60, ge=0, le=100, description="Minimum provider score for participation")
    min_provider_collateral: int = Field(0, ge=0, description="Minimum provider collateral (if applicable)")

    # Scoring model weights
    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights, description="Provider scoring weights")

    # Message template version
    message_template_version: str = Field("M19-2025-10-24", description="Active message template version")

    # SLA and dispute settings
    dispute_evidence_deadline_minutes: int = Field(30, ge=10, le=120, description="Deadline for submitting dispute evidence")
    dispute_resolution_deadline_hours: int = Field(4, ge=1, le=24, description="Admin deadline for dispute resolution")

    # Telemetry thresholds
    notification_latency_warning_ms: int = Field(5000, ge=1000, le=10000, description="Warning threshold for notification latency p95")
    notification_failure_warning_rate: float = Field(0.05, ge=0.01, le=0.2, description="Warning threshold for notification failure rate")


class ConfigurationVersion(BaseModel):
    """Versioned configuration with audit trail"""
    version: int = Field(..., description="Sequential version number")
    configuration: SystemConfiguration = Field(..., description="Configuration snapshot")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    created_by: str = Field(..., description="User/admin who created this version")
    rollback_token: str = Field(..., description="Token for rollback authentication")
    change_reason: Optional[str] = Field(None, description="Reason for configuration change")


class ConfigurationUpdateRequest(BaseModel):
    """Request to update system configuration"""
    configuration: SystemConfiguration = Field(..., description="New configuration to apply")
    change_reason: str = Field(..., min_length=10, max_length=500, description="Reason for change (required for audit)")
    created_by: str = Field(..., description="Admin username making the change")


class ConfigurationHistoryEntry(BaseModel):
    """Single entry in configuration history"""
    version: int
    created_at: datetime
    created_by: str
    change_reason: Optional[str]
    rollback_token: str


class ConfigurationHistoryResponse(BaseModel):
    """List of configuration history entries"""
    total_versions: int
    current_version: int
    history: List[ConfigurationHistoryEntry]


class RollbackRequest(BaseModel):
    """Request to rollback to a previous configuration version"""
    target_version: int = Field(..., ge=1, description="Version number to rollback to")
    rollback_token: str = Field(..., description="Rollback authentication token")
    rollback_by: str = Field(..., description="Admin username performing rollback")
    rollback_reason: str = Field(..., min_length=10, max_length=500, description="Reason for rollback")


class RollbackResponse(BaseModel):
    """Response after successful rollback"""
    success: bool
    rolled_back_from: int
    rolled_back_to: int
    new_version: int
    message: str


class CurrentConfigResponse(BaseModel):
    """Response containing current active configuration"""
    version: int
    configuration: SystemConfiguration
    created_at: datetime
    created_by: str
    is_latest: bool
