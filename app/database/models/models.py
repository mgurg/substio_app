from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Numeric, String, Table, Text, Time, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base
from app.database.models.enums import OfferStatus, SourceType


class BaseModel(Base):
    __abstract__ = True
    """
    Base model for all tables

    Attributes:
        id (int): Primary key for all tables
        created_at (datetime): Date and time of creation
        updated_at (datetime): Date and time of last update
    """

    id: Mapped[int] = mapped_column(sa.INTEGER(), sa.Identity(), primary_key=True, autoincrement=True, nullable=False)


class LegalRole(BaseModel):
    __tablename__ = "legal_roles"

    uuid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(Text(), nullable=False)

    offers: Mapped[list["Offer"]] = relationship(
        back_populates="legal_roles",
        secondary="offers_legal_roles_link"
    )


offers_legal_roles_link = Table(
    "offers_legal_roles_link",
    Base.metadata,
    Column("offer_id", ForeignKey("offers.id"), primary_key=True),
    Column("legal_role_id", ForeignKey("legal_roles.id"), primary_key=True)
)


class Place(BaseModel):
    __tablename__ = "places"
    uuid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class City(BaseModel):
    __tablename__ = "cities"
    uuid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class Offer(BaseModel):
    __tablename__ = "offers"
    uuid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    raw_data: Mapped[str | None] = mapped_column(String(1024))
    offer_uid: Mapped[str | None] = mapped_column(String(1024))
    author: Mapped[str] = mapped_column(String(96))
    author_uid: Mapped[str | None] = mapped_column(String(1024))
    source: Mapped[SourceType] = mapped_column(Enum(SourceType))
    status: Mapped[OfferStatus] = mapped_column(Enum(OfferStatus), default=OfferStatus.NEW)

    place_id: Mapped[str | None] = mapped_column(Text())
    place_name: Mapped[str | None] = mapped_column(Text())
    email: Mapped[str | None] = mapped_column(Text())
    url: Mapped[str | None] = mapped_column(Text())
    date: Mapped[Date | None] = mapped_column(Date())
    hour: Mapped[Time | None] = mapped_column(Time())
    price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    description: Mapped[str | None] = mapped_column(Text())
    invoice: Mapped[bool | None] = mapped_column(Boolean())

    visible: Mapped[bool | None] = mapped_column(Boolean())
    added_at: Mapped[datetime | None] = mapped_column(DateTime())
    valid_to: Mapped[datetime | None] = mapped_column(DateTime())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime(), default=func.now(), onupdate=func.now())
    created_at: Mapped[DateTime | None] = mapped_column(DateTime(), default=func.now())

    legal_roles: Mapped[list[LegalRole]] = relationship(
        back_populates="offers",
        secondary=offers_legal_roles_link
    )
