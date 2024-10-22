import enum
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import String, DateTime, func, Integer, ForeignKey, Date, Boolean, insert, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from orm import db_manager
from orm.base_model import OrmBase


class Role(OrmBase):
    """
    Роли пользователей
    """
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[int] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())

    @classmethod
    async def create_or_ignore(cls, id: int, name: str):
        async with db_manager.session() as session:
            try:
                await session.execute(insert(Role).values(id=id, name=name))
                await session.commit()
            except Exception as e:
                print(e)


class User(OrmBase):
    """
    Базовая информация о пользователе
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(50))
    birth_date: Mapped[Optional[Date]] = mapped_column(Date)
    gender: Mapped[Optional[int]] = mapped_column(Integer)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_email_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_phone_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VerificationCode(OrmBase):
    """
    Таблица верификации пользователя
    """
    __tablename__ = "verification_codes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    verification_type: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserRoles(OrmBase):
    """
    Роли пользователя
    """
    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RefreshToken(OrmBase):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class File(OrmBase):
    __tablename__ = "files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    hash: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    create_date: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    modify_date: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.now, onupdate=datetime.now
    )


class QRAuthTokens(OrmBase):
    __tablename__ = "qr_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    create_date: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    token: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    user_id: Mapped[str] = mapped_column(Integer, nullable=True)

