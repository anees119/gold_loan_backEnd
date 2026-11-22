from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Numeric, Text, String, Integer, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Loan(db.Model):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # ── Customer / KYC ──────────────────────────────────────────────────────
    customer_name:      Mapped[str]            = mapped_column(String(150), nullable=False, index=True)
    relation_type:      Mapped[Optional[str]]  = mapped_column(String(50),  nullable=True)
    relation_name:      Mapped[Optional[str]]  = mapped_column(String(150), nullable=True)
    contact_number:     Mapped[str]            = mapped_column(String(20),  nullable=False, index=True)
    alternative_number: Mapped[Optional[str]]  = mapped_column(String(20),  nullable=True)
    date_of_birth:      Mapped[Optional[date]] = mapped_column(Date,        nullable=True)
    gender:             Mapped[Optional[str]]  = mapped_column(String(30),  nullable=True)
    email:              Mapped[Optional[str]]  = mapped_column(String(150), nullable=True)
    aadhaar_number:     Mapped[Optional[str]]  = mapped_column(Text,        nullable=True)  # encrypted
    pan_number:         Mapped[Optional[str]]  = mapped_column(Text,        nullable=True)  # encrypted
    nominee_name:       Mapped[Optional[str]]  = mapped_column(String(150), nullable=True)
    current_address:    Mapped[Optional[str]]  = mapped_column(Text,        nullable=True)
    permanent_address:  Mapped[Optional[str]]  = mapped_column(Text,        nullable=True)

    # ── File uploads ─────────────────────────────────────────────────────────
    customer_photo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    items_image:    Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ── Loan financials ──────────────────────────────────────────────────────
    loan_amount:    Mapped[Decimal]           = mapped_column(Numeric(14, 2), nullable=False, default=0)
    loan_type:      Mapped[Optional[str]]     = mapped_column(String(50),     nullable=True, default="Normal")
    article_value:  Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True, default=0)
    interest_rate:  Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 2),  nullable=True, default=0)
    total_interest: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True, default=0)
    interest_mode:  Mapped[Optional[str]]     = mapped_column(String(50),     nullable=True)
    loan_tenure:    Mapped[Optional[str]]     = mapped_column(String(50),     nullable=True)
    payment_type:   Mapped[Optional[str]]     = mapped_column(String(50),     nullable=True)

    # ── Weight summary (computed from items) ─────────────────────────────────
    total_quantity:     Mapped[Optional[int]]     = mapped_column(Integer,        nullable=True, default=0)
    total_gross_weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3), nullable=True, default=0)
    total_deduction:    Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3), nullable=True, default=0)
    total_net_weight:   Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3), nullable=True, default=0)

    # ── Misc ─────────────────────────────────────────────────────────────────
    remarks:     Mapped[Optional[str]]  = mapped_column(Text,       nullable=True)
    notes:       Mapped[Optional[str]]  = mapped_column(Text,       nullable=True)
    loan_date:   Mapped[Optional[date]] = mapped_column(Date,       nullable=True)
    loan_status: Mapped[str]            = mapped_column(String(30),  nullable=False, default="active")

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(),
                                                           onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────────────────────
    items: Mapped[list[LoanItem]] = relationship("LoanItem", cascade="all, delete-orphan",
                                                 lazy=True, backref="loan")


class LoanItem(db.Model):
    """One gold article row inside a loan (the items table in the UI)."""
    __tablename__ = "loan_items"

    id:           Mapped[int]           = mapped_column(Integer, primary_key=True)
    loan_id:      Mapped[int]           = mapped_column(Integer, ForeignKey("loans.id", ondelete="CASCADE"),
                                                        nullable=False, index=True)
    product_name: Mapped[str]           = mapped_column(String(180), nullable=False)
    quantity:     Mapped[int]           = mapped_column(Integer,       nullable=False, default=1)
    gross_weight: Mapped[Decimal]       = mapped_column(Numeric(12, 3), nullable=False, default=0)
    deduction:    Mapped[Decimal]       = mapped_column(Numeric(12, 3), nullable=False, default=0)
    net_weight:   Mapped[Decimal]       = mapped_column(Numeric(12, 3), nullable=False, default=0)
    purity:       Mapped[Optional[str]] = mapped_column(String(30), nullable=True)