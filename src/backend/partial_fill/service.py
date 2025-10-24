from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List

from ..award_engine.schemas import AwardResult
from ..notifications.service import get_quote_registry
from .schemas import CancelRequest, PartialFillResponse, PartialLeg, ReallocateRequest

PARTIAL_LOG = Path("logs/partial_fill_events.json")
RECONCILIATION_FILE = Path("artefacts/Order_Reconciliation.xlsx")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _log(payload: Dict[str, object]) -> None:
    PARTIAL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with PARTIAL_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _write_xlsx(path: Path, rows: List[List[str]]) -> None:
    from zipfile import ZipFile, ZIP_DEFLATED

    path.parent.mkdir(parents=True, exist_ok=True)
    created = _now().replace(microsecond=0).isoformat().replace("+00:00", "Z")

    content_types = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">
  <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>
  <Default Extension=\"xml\" ContentType=\"application/xml\"/>
  <Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>
  <Override PartName=\"/xl/worksheets/sheet1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>
  <Override PartName=\"/docProps/core.xml\" ContentType=\"application/vnd.openxmlformats-package.core-properties+xml\"/>
  <Override PartName=\"/docProps/app.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.extended-properties+xml\"/>
  <Override PartName=\"/xl/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml\"/>
</Types>
""".strip()

    rels = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/>
  <Relationship Id=\"rId2\" Type=\"http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties\" Target=\"docProps/core.xml\"/>
  <Relationship Id=\"rId3\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties\" Target=\"docProps/app.xml\"/>
</Relationships>
""".strip()

    workbook_rels = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet1.xml\"/>
  <Relationship Id=\"rId2\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" Target=\"styles.xml\"/>
</Relationships>
""".strip()

    workbook = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">
  <sheets>
    <sheet name=\"Order Reconciliation\" sheetId=\"1\" r:id=\"rId1\"/>
  </sheets>
</workbook>
""".strip()

    styles = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<styleSheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">
  <fonts count=\"1\"><font><sz val=\"11\"/><color theme=\"1\"/><name val=\"Calibri\"/><family val=\"2\"/></font></fonts>
  <fills count=\"1\"><fill><patternFill patternType=\"none\"/></fill></fills>
  <borders count=\"1\"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\"/></cellStyleXfs>
  <cellXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\"/></cellXfs>
  <cellStyles count=\"1\"><cellStyle name=\"Normal\" xfId=\"0\" builtinId=\"0\"/></cellStyles>
</styleSheet>
""".strip()

    def col_letter(idx: int) -> str:
        result = ""
        n = idx
        while True:
            n, rem = divmod(n, 26)
            result = chr(65 + rem) + result
            if n == 0:
                break
            n -= 1
        return result

    sheet_rows = []
    for r_idx, values in enumerate(rows, start=1):
        cells = []
        for c_idx, value in enumerate(values):
            cell_ref = f"{col_letter(c_idx)}{r_idx}"
            safe_value = str(value)
            cells.append(f"<c r=\"{cell_ref}\" t=\"inlineStr\"><is><t>{safe_value}</t></is></c>")
        sheet_rows.append(f"<row r=\"{r_idx}\">{''.join(cells)}</row>")

    sheet = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">
  <sheetViews><sheetView workbookViewId=\"0\"/></sheetViews>
  <sheetFormatPr defaultRowHeight=\"15\"/>
  <sheetData>{''.join(sheet_rows)}</sheetData>
</worksheet>
""".strip()

    core = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<cp:coreProperties xmlns:cp=\"http://schemas.openxmlformats.org/package/2006/metadata/core-properties\" xmlns:dc=\"http://purl.org/dc/elements/1.1/\" xmlns:dcterms=\"http://purl.org/dc/terms/\" xmlns:dcmitype=\"http://purl.org/dc/dcmitype/\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
  <dc:title>Stage 17 Order Reconciliation</dc:title>
  <dc:creator>Codex Agent</dc:creator>
  <cp:lastModifiedBy>Codex Agent</cp:lastModifiedBy>
  <dcterms:created xsi:type=\"dcterms:W3CDTF\">{created}</dcterms:created>
  <dcterms:modified xsi:type=\"dcterms:W3CDTF\">{created}</dcterms:modified>
</cp:coreProperties>
""".strip()

    app = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Properties xmlns=\"http://schemas.openxmlformats.org/officeDocument/2006/extended-properties\" xmlns:vt=\"http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes\">
  <Application>Codex Generator</Application>
  <DocSecurity>0</DocSecurity>
  <HeadingPairs><vt:vector size=\"2\" baseType=\"variant\"><vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant><vt:variant><vt:i4>1</vt:i4></vt:variant></vt:vector></HeadingPairs>
  <TitlesOfParts><vt:vector size=\"1\" baseType=\"lpstr\"><vt:lpstr>Order Reconciliation</vt:lpstr></vt:vector></TitlesOfParts>
  <Company>USDT Auction</Company>
  <LinksUpToDate>false</LinksUpToDate>
  <SharedDoc>false</SharedDoc>
  <AppVersion>1.0</AppVersion>
</Properties>
""".strip()

    with ZipFile(path, "w", ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/styles.xml", styles)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)


@dataclass
class PartialLegRecord:
    leg_id: str
    quote_id: str
    provider_telegram_id: int
    amount: Decimal
    status: str
    updated_at: datetime = field(default_factory=_now)
    reason: str | None = None


@dataclass
class PartialFillRecord:
    rfq_id: str
    award_id: str
    total_awarded: Decimal
    status: str = "active"
    legs: List[PartialLegRecord] = field(default_factory=list)

    @property
    def remaining_amount(self) -> Decimal:
        active_total = sum(leg.amount for leg in self.legs if leg.status in {"active", "partial"})
        return self.total_awarded - active_total

    def refresh_status(self) -> None:
        statuses = {leg.status for leg in self.legs}
        if statuses == {"active"}:
            self.status = "active"
        elif "cancelled" in statuses or "reallocated" in statuses or "partial" in statuses:
            self.status = "adjusting"
        else:
            self.status = "active"


class PartialFillRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, PartialFillRecord] = {}

    def start(self, award: AwardResult) -> PartialFillRecord:
        total = sum(Decimal(str(leg.awarded_amount)) for leg in award.legs)
        record = PartialFillRecord(rfq_id=award.rfq_id, award_id=award.award_id, total_awarded=total)
        for leg in award.legs:
            leg_record = PartialLegRecord(
                leg_id=f"{leg.quote_id}-partial",
                quote_id=leg.quote_id,
                provider_telegram_id=leg.provider_telegram_id,
                amount=Decimal(str(leg.awarded_amount)),
                status="active",
            )
            record.legs.append(leg_record)
        record.refresh_status()
        self._records[record.rfq_id] = record
        _log({
            "event": "partial_fill_started",
            "rfq_id": record.rfq_id,
            "award_id": record.award_id,
            "target_amount": float(record.total_awarded),
            "timestamp": _now().isoformat(),
        })
        self._write_reconciliation()
        return record

    def reallocate(self, rfq_id: str, request: ReallocateRequest) -> PartialFillRecord:
        record = self._records.get(rfq_id)
        if not record:
            raise KeyError("RFQ not found")
        source = next((leg for leg in record.legs if leg.quote_id == request.from_quote_id), None)
        if source is None:
            raise KeyError("Source quote not found")
        if source.status not in {"active", "partial"}:
            raise ValueError("source_leg_not_available")
        realloc_amount = Decimal(str(request.reallocated_amount))
        if realloc_amount <= 0 or realloc_amount > source.amount:
            raise ValueError("invalid_reallocation_amount")

        source.amount -= realloc_amount
        source.updated_at = _now()
        if source.amount == 0:
            source.status = "reallocated"
        else:
            source.status = "partial"

        new_leg = PartialLegRecord(
            leg_id=f"realloc-{uuid.uuid4().hex[:8]}",
            quote_id=f"realloc-{uuid.uuid4().hex[:8]}",
            provider_telegram_id=request.to_provider_telegram_id,
            amount=realloc_amount,
            status="active",
        )
        record.legs.append(new_leg)
        record.refresh_status()

        _log({
            "event": "partial_fill_reallocated",
            "rfq_id": rfq_id,
            "from_quote_id": request.from_quote_id,
            "to_provider": request.to_provider_telegram_id,
            "amount": float(realloc_amount),
            "timestamp": _now().isoformat(),
        })
        self._write_reconciliation()
        return record

    def cancel_leg(self, rfq_id: str, request: CancelRequest) -> PartialFillRecord:
        record = self._records.get(rfq_id)
        if not record:
            raise KeyError("RFQ not found")
        leg = next((leg for leg in record.legs if leg.quote_id == request.quote_id), None)
        if not leg:
            raise KeyError("Quote not found")
        leg.status = "cancelled"
        leg.reason = request.reason or "cancelled"
        leg.amount = Decimal("0")
        leg.updated_at = _now()
        record.refresh_status()
        _log({
            "event": "partial_fill_cancelled",
            "rfq_id": rfq_id,
            "quote_id": request.quote_id,
            "reason": leg.reason,
            "timestamp": _now().isoformat(),
        })
        self._write_reconciliation()
        return record

    def get(self, rfq_id: str) -> PartialFillRecord:
        record = self._records.get(rfq_id)
        if not record:
            raise KeyError("RFQ not found")
        return record

    def list(self) -> List[PartialFillRecord]:
        return list(self._records.values())

    def _write_reconciliation(self) -> None:
        rows = [["RFQ", "Award", "Leg ID", "Provider", "Status", "Amount", "Updated At", "Reason", "Remaining"]]
        for record in self._records.values():
            remain = float(record.remaining_amount)
            for leg in record.legs:
                rows.append([
                    record.rfq_id,
                    record.award_id,
                    leg.leg_id,
                    str(leg.provider_telegram_id),
                    leg.status,
                    str(float(leg.amount)),
                    leg.updated_at.isoformat(),
                    leg.reason or "",
                    str(remain),
                ])
        _write_xlsx(RECONCILIATION_FILE, rows)


REGISTRY = PartialFillRegistry()


def get_registry() -> PartialFillRegistry:
    return REGISTRY


def to_response(record: PartialFillRecord) -> PartialFillResponse:
    return PartialFillResponse(
        rfq_id=record.rfq_id,
        award_id=record.award_id,
        status=record.status,
        remaining_amount=record.remaining_amount,
        legs=[
            PartialLeg(
                leg_id=leg.leg_id,
                quote_id=leg.quote_id,
                provider_telegram_id=leg.provider_telegram_id,
                amount=leg.amount,
                status=leg.status,
                updated_at=leg.updated_at,
            )
            for leg in record.legs
        ],
    )
