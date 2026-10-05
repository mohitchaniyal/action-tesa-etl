import pandas as pd
from sqlalchemy.orm import Session

from action_tesa_etl.core.invoice_extractor import to_num
from action_tesa_etl.models import InvoiceHeader, InvoiceItem, InvoiceSummary


def _missing(value) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(value, str) and value.strip() == ""


def _text(value) -> str | None:
    if _missing(value):
        return None
    return str(value)


def _number(value):
    if _missing(value):
        return None
    converted = to_num(value) if isinstance(value, str) else value
    if _missing(converted):
        return None
    if isinstance(converted, str):
        raise ValueError(f"not a number: {value!r}")
    return converted


def _float(value) -> float | None:
    converted = _number(value)
    if converted is None:
        return None
    return float(converted)


def _int(value) -> int | None:
    converted = _number(value)
    if converted is None:
        return None
    return int(converted)


def _row(df: pd.DataFrame, index: int) -> dict:
    return df.iloc[index].to_dict()


def invoice_from_frames(frames: dict[str, pd.DataFrame]) -> InvoiceHeader:
    header_df = frames.get("invoice_header")
    if header_df is None or header_df.empty:
        raise ValueError("invoice_header is missing")

    header_row = _row(header_df, 0)
    invoice_no = _text(header_row.get("invoice_no"))
    if not invoice_no:
        raise ValueError("invoice_no is missing")

    header = InvoiceHeader(
        invoice_no=invoice_no,
        date_of_issue=_text(header_row.get("date_of_issue")),
        seller_tax_id=_text(header_row.get("seller_tax_id")),
        seller_gstin=_text(header_row.get("seller_gstin")),
        seller_name=_text(header_row.get("seller_name")),
        seller_address=_text(header_row.get("seller_address")),
        client_tax_id=_text(header_row.get("client_tax_id")),
        client_name=_text(header_row.get("client_name")),
        client_address=_text(header_row.get("client_address")),
    )

    items_df = frames.get("invoice_items")
    if items_df is not None:
        header.items = [
            InvoiceItem(
                invoice_no=invoice_no,
                no=_int(row.get("no")),
                description=_text(row.get("description")),
                qty=_float(row.get("qty")),
                um=_text(row.get("um")),
                net_price=_float(row.get("net_price")),
                net_worth=_float(row.get("net_worth")),
                vat_pct=_float(row.get("vat_pct")),
                gross_worth=_float(row.get("gross_worth")),
            )
            for row in (_row(items_df, i) for i in range(len(items_df)))
        ]

    summary_df = frames.get("invoice_summary")
    if summary_df is not None:
        header.summary_rows = [
            InvoiceSummary(
                invoice_no=invoice_no,
                label=_text(row.get("label")),
                vat_pct=_float(row.get("vat_pct")),
                net_worth=_float(row.get("net_worth")),
                vat=_float(row.get("vat")),
                gross_worth=_float(row.get("gross_worth")),
            )
            for row in (_row(summary_df, i) for i in range(len(summary_df)))
        ]

    return header


def replace_invoice(session: Session, header: InvoiceHeader) -> None:
    existing = session.get(InvoiceHeader, header.invoice_no)
    if existing is not None:
        session.delete(existing)
        session.flush()
    session.add(header)
