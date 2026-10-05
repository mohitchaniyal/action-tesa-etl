from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from action_tesa_etl.models import InvoiceHeader, InvoiceItem, InvoiceSummary


def find_invoices(
    session: Session,
    invoice_no: str | None = None,
    date_of_issue: str | None = None,
) -> list[InvoiceHeader]:
    statement = (
        select(InvoiceHeader)
        .options(
            selectinload(InvoiceHeader.items),
            selectinload(InvoiceHeader.summary_rows),
        )
        .order_by(InvoiceHeader.invoice_no)
    )
    if invoice_no:
        statement = statement.where(InvoiceHeader.invoice_no == invoice_no)
    if date_of_issue:
        statement = statement.where(InvoiceHeader.date_of_issue == date_of_issue)
    return list(session.scalars(statement).unique())



def invoice_to_dict(header: InvoiceHeader) -> dict:
    return {
        "header": _header_dict(header),
        "items": [_item_dict(item) for item in sorted(header.items, key=_item_sort)],
        "summary": [_summary_dict(row) for row in header.summary_rows],
    }


def _item_sort(item: InvoiceItem) -> tuple:
    return (item.no is None, item.no if item.no is not None else 0, item.id)


def _header_dict(header: InvoiceHeader) -> dict:
    return {
        "invoice_no": header.invoice_no,
        "date_of_issue": header.date_of_issue,
        "seller_tax_id": header.seller_tax_id,
        "seller_gstin": header.seller_gstin,
        "seller_name": header.seller_name,
        "seller_address": header.seller_address,
        "client_tax_id": header.client_tax_id,
        "client_name": header.client_name,
        "client_address": header.client_address,
    }


def _item_dict(item: InvoiceItem) -> dict:
    return {
        "invoice_no": item.invoice_no,
        "no": item.no,
        "description": item.description,
        "qty": item.qty,
        "um": item.um,
        "net_price": item.net_price,
        "net_worth": item.net_worth,
        "vat_pct": item.vat_pct,
        "gross_worth": item.gross_worth,
    }


def _summary_dict(row: InvoiceSummary) -> dict:
    return {
        "invoice_no": row.invoice_no,
        "label": row.label,
        "vat_pct": row.vat_pct,
        "net_worth": row.net_worth,
        "vat": row.vat,
        "gross_worth": row.gross_worth,
    }
