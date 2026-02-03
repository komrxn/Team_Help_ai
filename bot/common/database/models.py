from datetime import datetime
from sqlalchemy import BigInteger, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from bot.common.database.core import Base

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    full_name: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    zelle: Mapped[str] = mapped_column(String, nullable=True)
    dl_photo_id: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending") # active, banned, pending
    language: Mapped[str] = mapped_column(String, default="en")
    
    # Rating fields
    rating_score: Mapped[float] = mapped_column(Float, default=4.0)
    rating_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    location: Mapped["Location"] = relationship("Location", back_populates="user", uselist=False)
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="driver")

class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), unique=True)
    city: Mapped[str] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="location")

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    admin_id: Mapped[int] = mapped_column(BigInteger)
    route_from: Mapped[str] = mapped_column(String)
    route_to: Mapped[str] = mapped_column(String)
    is_good: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    driver: Mapped["User"] = relationship("User", back_populates="orders")
