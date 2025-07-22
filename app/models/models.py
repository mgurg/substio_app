import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


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


class Place(BaseModel):
    __tablename__ = "places"
    uuid = sa.Column(UUID(as_uuid=True), autoincrement=False, nullable=True)


class City(BaseModel):
    __tablename__ = "cities"
    uuid = sa.Column(UUID(as_uuid=True), autoincrement=False, nullable=True)
