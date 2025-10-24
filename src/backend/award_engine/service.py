from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Tuple

from ..notifications.service import get_quote_registry, QuoteRegistry
from ..rfq.service import get_registry as get_rfq_registry, RFQRegistry
from ..rfq.schemas import SpecialConditions
from ..notifications.service import QuoteRecord  # type: ignore
from .schemas import AwardLeg, AwardResult

AWARD_LOG = Path("logs/award_events.json")
AUDIT_FILE = Path("artefacts/Award_Audit.xlsx")


class AwardEngine:
    """
    Award engine for Stage 15. Selects winning quotes based on effective price and tie-break rules.
    """

    def __init__(self, quote_registry: QuoteRegistry, rfq_registry: RFQRegistry) -> None:
        self._quote_registry = quote_registry
        self._rfq_registry = rfq_registry

    def auto_award(self, rfq_id: str) -> AwardResult:
        rfq = self._rfq_registry.get(rfq_id)
        records: List[QuoteRecord] = self._quote_registry.list_records(rfq_id)
        if not records:
            raise ValueError("no_quotes_submitted")

        amount_needed = Decimal(str(rfq.amount))
        split_allowed = False
        if rfq.special_conditions and isinstance(rfq.special_conditions, SpecialConditions):
            split_allowed = bool(rfq.special_conditions.split_allowed)

        scored = self._score_quotes(rfq.rfq_type, records)
        winners: List[Tuple[QuoteRecord, Decimal]] = []

        for record in scored:
            if amount_needed <= 0:
                break
            if not split_allowed and Decimal(record.capacity) < amount_needed:
                continue
            awarded = min(Decimal(record.capacity), amount_needed)
            winners.append((record, awarded))
            amount_needed -= awarded
            if not split_allowed:
                break

        if not winners:
            raise ValueError("no_suitable_quote")

        award_id = uuid.uuid4().hex
        award_map: Dict[str, Decimal] = {record.quote_id: awarded for record, awarded in winners}
        self._quote_registry.mark_awards(rfq_id, award_map)
        self._rfq_registry.mark_awarded(rfq_id)

        event = {
            "award_id": award_id,
            "rfq_id": rfq_id,
            "selection_mode": "auto",
            "tie_break_rule": "price_then_submission_time",
            "decision_reason": "auto_selection",
            "reviewer": "auto_engine",
            "approver": "auto_engine",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "legs": [
                {
                    "quote_id": record.quote_id,
                    "provider_telegram_id": record.provider_telegram_id,
                    "awarded_amount": float(awarded),
                    "unit_price": float(record.unit_price),
                }
                for record, awarded in winners
            ],
        }
        self._append_award_event(event)
        self._write_audit_sheet()

        legs = [
            AwardLeg(
                quote_id=record.quote_id,
                provider_telegram_id=record.provider_telegram_id,
                awarded_amount=awarded,
                unit_price=record.unit_price,
                submitted_at=record.submitted_at,
            )
            for record, awarded in winners
        ]
        total_awarded = sum((leg.awarded_amount for leg in legs), Decimal("0"))

        return AwardResult(
            award_id=award_id,
            rfq_id=rfq_id,
            tie_break_rule="price_then_submission_time",
            total_awarded=total_awarded,
            remaining_amount=max(Decimal("0"), Decimal(str(rfq.amount)) - total_awarded),
            legs=legs,
            generated_at=datetime.now(timezone.utc),
        )

    def _score_quotes(self, rfq_type: str, records: List[QuoteRecord]) -> List[QuoteRecord]:
        if rfq_type == "buy":
            def key(record: QuoteRecord):
                return (Decimal(record.unit_price), record.submitted_at)
        else:
            def key(record: QuoteRecord):
                return (-Decimal(record.unit_price), record.submitted_at)
        return sorted(records, key=key)

    def _append_award_event(self, event: Dict[str, object]) -> None:
        AWARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AWARD_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=True) + "\n")

    def _write_audit_sheet(self) -> None:
        AWARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        if not AWARD_LOG.exists():
            return
        entries = [
            json.loads(line)
            for line in AWARD_LOG.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        header = [
            "award_id",
            "rfq_id",
            "selection_mode",
            "reviewer",
            "approver",
            "decision_reason",
            "tie_break_rule",
            "timestamp",
        ]
        rows = [header]
        for entry in entries:
            rows.append(
                [
                    entry.get("award_id", ""),
                    entry.get("rfq_id", ""),
                    entry.get("selection_mode", ""),
                    entry.get("reviewer", ""),
                    entry.get("approver", ""),
                    entry.get("decision_reason", ""),
                    entry.get("tie_break_rule", ""),
                    entry.get("timestamp", ""),
                ]
            )
        _write_xlsx(AUDIT_FILE, rows)


def _write_xlsx(path: Path, rows: List[List[str]]) -> None:
    from zipfile import ZipFile, ZIP_DEFLATED

    path.parent.mkdir(parents=True, exist_ok=True)
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>
""".strip()

    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
""".strip()

    workbook_rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
""".strip()

    workbook = """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Award Audit" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
""".strip()

    styles = """<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><color theme="1"/><name val="Calibri"/><family val="2"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
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
            cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{safe_value}</t></is></c>')
        sheet_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')

    sheet = f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView workbookViewId="0"/></sheetViews>
  <sheetFormatPr defaultRowHeight="15"/>
  <sheetData>{''.join(sheet_rows)}</sheetData>
</worksheet>
""".strip()

    core = f"""<?xml version="1.0" encoding="UTF-8"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Stage 15 Award Audit</dc:title>
  <dc:creator>Codex Agent</dc:creator>
  <cp:lastModifiedBy>Codex Agent</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>
""".strip()

    app = """<?xml version="1.0" encoding="UTF-8"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex Generator</Application>
  <DocSecurity>0</DocSecurity>
  <HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant><vt:variant><vt:i4>1</vt:i4></vt:variant></vt:vector></HeadingPairs>
  <TitlesOfParts><vt:vector size="1" baseType="lpstr"><vt:lpstr>Award Audit</vt:lpstr></vt:vector></TitlesOfParts>
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


_AWARD_ENGINE = AwardEngine(get_quote_registry(), get_rfq_registry())


def get_award_engine() -> AwardEngine:
    return _AWARD_ENGINE
