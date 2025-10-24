"""
Pydantic schemas for Analytics and Reporting endpoints (Stage 21).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class TimeRangeFilter(BaseModel):
    """Time range filter for reports."""
    start_date: Optional[date] = Field(None, description="Start date (inclusive)")
    end_date: Optional[date] = Field(None, description="End date (inclusive)")
    last_n_days: Optional[int] = Field(None, description="Last N days (7/30/90)", ge=1, le=365)


class RFQSummaryResponse(BaseModel):
    """RFQ Summary Report Response."""
    total_rfqs: int = Field(..., description="تعداد کل RFQها")
    avg_award_time_minutes: float = Field(..., description="میانگین زمان انتخاب برنده (دقیقه)")
    rfqs_with_3plus_quotes: int = Field(..., description="تعداد RFQهای دارای ≥3 پیشنهاد")
    rfqs_with_3plus_quotes_percentage: float = Field(..., description="درصد RFQهای دارای ≥3 پیشنهاد")
    volume_by_network: List[NetworkVolume] = Field(..., description="حجم معاملات به تفکیک شبکه")
    period_start: datetime
    period_end: datetime


class NetworkVolume(BaseModel):
    """Volume breakdown by network."""
    network: str
    total_usdt_amount: float
    total_fiat_amount: float
    rfq_count: int


class SettlementKPIResponse(BaseModel):
    """Settlement KPI Report Response."""
    total_settlements: int = Field(..., description="تعداد کل تسویه‌ها")
    successful_settlements: int = Field(..., description="تعداد تسویه‌های موفق")
    success_rate_percentage: float = Field(..., description="نرخ موفقیت (%)")
    avg_settlement_time_minutes: float = Field(..., description="زمان متوسط تسویه (دقیقه)")
    sla_breach_count: int = Field(..., description="تعداد نقض SLA")
    sla_breach_rate_percentage: float = Field(..., description="نرخ نقض SLA (%)")
    period_start: datetime
    period_end: datetime


class DisputeOutcomesResponse(BaseModel):
    """Dispute Outcomes Report Response."""
    total_disputes: int = Field(..., description="تعداد کل اختلافات")
    resolved_disputes: int = Field(..., description="تعداد اختلافات حل‌شده")
    resolution_rate_percentage: float = Field(..., description="نرخ حل (%)")
    avg_resolution_time_hours: float = Field(..., description="زمان متوسط حل (ساعت)")
    outcomes_by_decision: List[DisputeDecisionBreakdown] = Field(..., description="تفکیک بر اساس تصمیم")
    provider_performance: List[ProviderDisputePerformance] = Field(..., description="عملکرد پرووایدرها")
    period_start: datetime
    period_end: datetime


class DisputeDecisionBreakdown(BaseModel):
    """Breakdown by dispute decision type."""
    decision_type: str = Field(..., description="favor_claimant | favor_respondent | partial_favor | inconclusive")
    count: int
    percentage: float


class ProviderDisputePerformance(BaseModel):
    """Provider performance in disputes."""
    provider_telegram_id: int
    total_disputes_involved: int = Field(..., description="تعداد کل اختلافات")
    disputes_against_provider: int = Field(..., description="اختلافات علیه پرووایدر")
    favor_provider_count: int = Field(..., description="تصمیمات به نفع پرووایدر")
    against_provider_count: int = Field(..., description="تصمیمات علیه پرووایدر")


class TelemetryMetricsResponse(BaseModel):
    """Telemetry metrics from Telemetry_Config.json."""
    notification_latency_p95_ms: Optional[float] = Field(None, description="p95 تأخیر اعلان (ms)")
    notification_failure_rate: Optional[float] = Field(None, description="نرخ شکست اعلان (0-1)")
    dispute_escalation_rate: Optional[float] = Field(None, description="نرخ Escalation اختلاف (0-1)")
    period: str = Field(..., description="بازه زمانی")


class ExportRequest(BaseModel):
    """Request for exporting report to CSV/Excel."""
    report_type: str = Field(..., description="rfq_summary | settlement_kpi | dispute_outcomes")
    format: str = Field("csv", description="csv | excel")
    time_range: Optional[TimeRangeFilter] = None
