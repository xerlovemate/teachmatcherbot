from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, List

from database.models import async_session, User, Skill


async def get_user_by_tg_id(tg_id: int) -> Optional[User]:
    """Получить пользователя по tg_id (без связанных данных)."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()


async def get_user_with_skills(tg_id: int) -> Optional[User]:
    """Получить пользователя с предзагруженными навыками."""
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.tg_id == tg_id)
            .options(selectinload(User.skills))
        )
        return result.scalar_one_or_none()


async def create_user(
    tg_id: int,
    tg_username: str,
    name: str,
    is_student: bool,
    description: str,
    price: int,
    online: bool,
    city: Optional[str],
    photo_id: Optional[str]
) -> User:
    """Создать нового пользователя."""
    async with async_session() as session:
        user = User(
            tg_id=tg_id,
            tg_username=tg_username,
            name=name,
            is_student=is_student,
            description=description,
            price=price,
            online=online,
            city=city,
            photo_id=photo_id
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def add_skills_to_user(user_id: int, keywords: List[str]) -> None:
    """
    Добавить навыки пользователю.
    Если навык не существует – создаётся новый.
    """
    async with async_session() as session:
        # Получаем пользователя с его текущими навыками
        result = await session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.skills))
        )
        user = result.scalar_one_or_none()
        if not user:
            return

        existing_names = {skill.name for skill in user.skills}
        for kw in keywords:
            if kw in existing_names:
                continue

            # Ищем навык в базе
            stmt = select(Skill).where(Skill.name == kw)
            res = await session.execute(stmt)
            skill = res.scalar_one_or_none()
            if not skill:
                skill = Skill(name=kw)
                session.add(skill)
                await session.flush()

            user.skills.append(skill)

        await session.commit()


async def delete_user_by_tg_id(tg_id: int) -> None:
    """Удалить пользователя по tg_id."""
    async with async_session() as session:
        user = await get_user_by_tg_id(tg_id)  # используем вспомогательную функцию
        if user:
            await session.delete(user)
            await session.commit()