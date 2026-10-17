from uuid import UUID

from anyio import to_thread
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User


class EmailAlreadyRegisteredError(Exception):
    pass


async def register_user(session: AsyncSession, email: str, password: str) -> User:
    normalized_email = email.strip().casefold()
    password_hash = await to_thread.run_sync(hash_password, password)
    user = User(email=normalized_email, hashed_password=password_hash)

    try:
        async with session.begin():
            existing_user = await session.scalar(
                select(User).where(User.email == normalized_email)
            )
            if existing_user is not None:
                raise EmailAlreadyRegisteredError
            session.add(user)
            await session.flush()
    except IntegrityError as exc:
        raise EmailAlreadyRegisteredError from exc

    return user


async def authenticate_user(
    session: AsyncSession, email: str, password: str
) -> User | None:
    normalized_email = email.strip().casefold()
    user = await session.scalar(select(User).where(User.email == normalized_email))
    if user is None or not user.is_active:
        return None
    if not await to_thread.run_sync(verify_password, password, user.hashed_password):
        return None
    return user


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)
