"""User persistence and business logic, isolated from the transport layer."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password
from users.models import User, UserRole
from users.schemas import UserCreate


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def list_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
    result = await db.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    user = User(
        email=str(data.email),
        hashed_password=hash_password(data.password),
        role=data.role or UserRole.VIEWER,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update_phone(db: AsyncSession, user: User, phone: str | None) -> User:
    """Set (or clear) the user's SMS contact number."""
    user.phone = phone.strip() if phone else None
    await db.flush()
    await db.refresh(user)
    return user
