"""Invoice tables shared by the ingestor and the exposor."""

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class InvoiceHeader(Base):
    __tablename__ = "invoice_header"

    invoice_no: Mapped[str] = mapped_column(String, primary_key=True)
    date_of_issue: Mapped[str | None] = mapped_column(String, nullable=True)
    seller_tax_id: Mapped[str | None] = mapped_column(String, nullable=True)
    seller_gstin: Mapped[str | None] = mapped_column(String, nullable=True)
    seller_name: Mapped[str | None] = mapped_column(String, nullable=True)
    seller_address: Mapped[str | None] = mapped_column(String, nullable=True)
    client_tax_id: Mapped[str | None] = mapped_column(String, nullable=True)
    client_name: Mapped[str | None] = mapped_column(String, nullable=True)
    client_address: Mapped[str | None] = mapped_column(String, nullable=True)

    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="header",
        cascade="all, delete-orphan",
    )
    summary_rows: Mapped[list["InvoiceSummary"]] = relationship(
        back_populates="header",
        cascade="all, delete-orphan",
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_no: Mapped[str] = mapped_column(
        ForeignKey("invoice_header.invoice_no", ondelete="CASCADE"),
        index=True,
    )
    no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    um: Mapped[str | None] = mapped_column(String, nullable=True)
    net_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_worth: Mapped[float | None] = mapped_column(Float, nullable=True)
    vat_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross_worth: Mapped[float | None] = mapped_column(Float, nullable=True)

    header: Mapped[InvoiceHeader] = relationship(back_populates="items")


class InvoiceSummary(Base):
    __tablename__ = "invoice_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_no: Mapped[str] = mapped_column(
        ForeignKey("invoice_header.invoice_no", ondelete="CASCADE"),
        index=True,
    )
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    vat_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_worth: Mapped[float | None] = mapped_column(Float, nullable=True)
    vat: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross_worth: Mapped[float | None] = mapped_column(Float, nullable=True)

    header: Mapped[InvoiceHeader] = relationship(back_populates="summary_rows")
