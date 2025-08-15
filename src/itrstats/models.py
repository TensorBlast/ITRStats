from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Raw fields from endpoint
    indv_reg_users: Mapped[int] = mapped_column(BigInteger, nullable=False)
    e_verified_returns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_aadhar_linked_pan: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_processed_refund: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Provider timestamp if present
    provider_last_updated_raw: Mapped[Optional[String]] = mapped_column(String(64), nullable=True)

    # When we captured it
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Convenient derived fields (date partition)
    collected_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return (
            f"Snapshot(id={self.id}, indv_reg_users={self.indv_reg_users}, "
            f"e_verified_returns={self.e_verified_returns}, total_aadhar_linked_pan={self.total_aadhar_linked_pan}, "
            f"total_processed_refund={self.total_processed_refund}, provider_last_updated_raw={self.provider_last_updated_raw}, "
            f"collected_at={self.collected_at}, collected_date={self.collected_date})"
        )
