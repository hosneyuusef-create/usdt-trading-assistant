"""
Analytics and Reporting API endpoints (Stage 21).
"""
from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .schemas import (
    RFQSummaryResponse,
    SettlementKPIResponse,
    DisputeOutcomesResponse,
    TelemetryMetricsResponse,
    TimeRangeFilter,
    ExportRequest,
)
from .service import (
    generate_rfq_summary,
    generate_settlement_kpi,
    generate_dispute_outcomes,
    get_telemetry_metrics,
    export_report_to_csv,
)


router = APIRouter(prefix="/analytics", tags=["Analytics"])

REPORTS_DIR = Path(__file__).parent.parent.parent.parent / "reports" / "kpi_dashboard"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/rfq-summary", response_model=RFQSummaryResponse)
def get_rfq_summary(time_filter: TimeRangeFilter | None = None):
    """
    RFQ Summary Report.

    Includes:
    - تعداد کل RFQها
    - میانگین زمان انتخاب برنده
    - درصد RFQهای دارای ≥3 پیشنهاد
    - حجم معاملات به تفکیک شبکه

    Data sources:
    - logs/award_events.json
    - logs/quote_events.json

    Cross-check:
    - Compares unique rfq_id from logs with DB (when available)
    """
    return generate_rfq_summary(time_filter)


@router.post("/settlement-kpi", response_model=SettlementKPIResponse)
def get_settlement_kpi(time_filter: TimeRangeFilter | None = None):
    """
    Settlement KPI Report.

    Includes:
    - نرخ انجام موفق
    - زمان متوسط تسویه
    - نرخ نقض SLA

    Data sources:
    - DB settlements table

    Cross-check:
    - Compares settlement counts from DB with audit logs
    """
    return generate_settlement_kpi(time_filter)


@router.post("/dispute-outcomes", response_model=DisputeOutcomesResponse)
def get_dispute_outcomes(time_filter: TimeRangeFilter | None = None):
    """
    Dispute Outcomes Report.

    Includes:
    - تعداد و نرخ حل اختلافات
    - تفکیک بر اساس تصمیم
    - عملکرد پرووایدرها

    Data sources:
    - DB disputes table
    - DB dispute_actions table

    Cross-check:
    - Compares dispute counts from DB with dispute logs
    """
    return generate_dispute_outcomes(time_filter)


@router.get("/telemetry", response_model=TelemetryMetricsResponse)
def get_telemetry():
    """
    Telemetry Metrics.

    Returns key telemetry metrics from Telemetry_Config.json:
    - notification_latency_p95_ms
    - notification_failure_rate
    - dispute_escalation_rate

    In production, this would query live monitoring system.
    """
    return get_telemetry_metrics()


@router.post("/export")
def export_report(request: ExportRequest):
    """
    Export report to CSV/Excel format.

    Args:
        request: Export request with report type, format, and time range

    Returns:
        File download response
    """
    if request.report_type == "rfq_summary":
        data = generate_rfq_summary(request.time_range)
    elif request.report_type == "settlement_kpi":
        data = generate_settlement_kpi(request.time_range)
    elif request.report_type == "dispute_outcomes":
        data = generate_dispute_outcomes(request.time_range)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown report type: {request.report_type}")

    # Convert to dict
    data_dict = data.model_dump()

    # Generate filename
    timestamp = data.period_end.strftime("%Y%m%d_%H%M%S")
    filename = f"{request.report_type}_{timestamp}.{request.format}"
    output_path = REPORTS_DIR / filename

    # Export to CSV (Excel export would require additional library like openpyxl)
    if request.format == "csv":
        export_report_to_csv(request.report_type, data_dict, output_path)
    elif request.format == "excel":
        # Placeholder: In production, use openpyxl or pandas to export to Excel
        export_report_to_csv(request.report_type, data_dict, output_path.with_suffix(".csv"))
        output_path = output_path.with_suffix(".csv")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")

    return FileResponse(
        path=output_path,
        filename=filename,
        media_type="text/csv" if request.format == "csv" else "application/vnd.ms-excel"
    )
