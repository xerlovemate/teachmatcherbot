import re
from typing import Optional, List, Tuple
from sqlalchemy import delete, select, and_, desc, or_
from sqlalchemy.orm import selectinload
from database.models import async_session, User, Skill, Recommendation, Like, Match
from sqlalchemy import select, and_, desc, or_, delete

async def get_user_by_tg_id(tg_id: int) -> Optional[User]:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()

async def get_user_by_id_with_skills(user_id: int) -> Optional[User]:
    """Получить пользователя по ID с предзагруженными навыками."""
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.skills))
        )
        return result.scalar_one_or_none()
    
async def get_user_by_id(user_id: int) -> Optional[User]:
    async with async_session() as session:
        return await session.get(User, user_id)


async def get_user_with_skills(tg_id: int) -> Optional[User]:
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
    about: Optional[str],
    price: int,
    online: bool,
    city: Optional[str],
    photo_id: Optional[str]
) -> User:
    async with async_session() as session:
        user = User(
            tg_id=tg_id,
            tg_username=tg_username,
            name=name,
            is_student=is_student,
            description=description,
            about=about,
            price=price,
            online=online,
            city=city,
            photo_id=photo_id
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def update_user_work_style(tg_id: int, work_style: str) -> None:
    async with async_session() as session:
        stmt = select(User).where(User.tg_id == tg_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            user.work_style = work_style
            await session.commit()


async def add_skills_to_user(user_id: int, keywords: List[str]) -> None:
    async with async_session() as session:
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
    async with async_session() as session:
        user = await get_user_by_tg_id(tg_id)
        if user:
            await session.delete(user)
            await session.commit()


async def get_all_users() -> List[User]:
    async with async_session() as session:
        result = await session.execute(select(User))
        return result.scalars().all()


def extract_keywords(text: str) -> List[str]:
    if not text:
        return []
    words = re.findall(r'\w+', text.lower())
    return list(set(words))


def calculate_match_score(user1: User, user2: User) -> float:
    """
    Вычисляет процент совпадения между двумя пользователями.
    Учитывает:
    - общие ключевые слова из навыков, about, description (коэффициент Жаккара)
    - совпадение стиля работы (work_style) даёт бонус +0.2, если стили совпадают и не равны None.
    Итоговый результат ограничен 1.0.
    """
    keywords1 = set()
    if user1.skills:
        keywords1.update(skill.name.lower() for skill in user1.skills if skill.name)
    if user1.about:
        keywords1.update(extract_keywords(user1.about))
    if user1.description:
        keywords1.update(extract_keywords(user1.description))

    keywords2 = set()
    if user2.skills:
        keywords2.update(skill.name.lower() for skill in user2.skills if skill.name)
    if user2.about:
        keywords2.update(extract_keywords(user2.about))
    if user2.description:
        keywords2.update(extract_keywords(user2.description))

    base_score = 0.0
    if keywords1 and keywords2:
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)
        base_score = len(intersection) / len(union) if union else 0.0

    style_bonus = 0.0
    if user1.work_style and user2.work_style and user1.work_style == user2.work_style:
        style_bonus = 0.2

    total = base_score + style_bonus
    return round(min(total, 1.0), 4)


async def generate_recommendations_for_user(user: User, limit: int = 50) -> List[Tuple[User, float]]:
    """
    Генерирует рекомендации для пользователя.
    ВАЖНО: Эта функция создает свою сессию и возвращает список кортежей (User, score),
           где User - это объект со всеми необходимыми данными (навыки загружены).
    """
    async with async_session() as session:
        stmt = (
            select(User)
            .where(User.is_student != user.is_student)
            .options(selectinload(User.skills))
        )
        result = await session.execute(stmt)
        candidates = result.scalars().all()

        user_with_skills = await session.get(User, user.id, options=[selectinload(User.skills)])
        if not user_with_skills:
            return []

        scored = []
        for cand in candidates:
            if cand.id == user_with_skills.id:
                continue

            score = calculate_match_score(user_with_skills, cand)
            if score > 0:
                scored.append((cand, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]


async def save_recommendations(user_id: int, recommendations: List[Tuple[User, float]]):
    async with async_session() as session:
        for cand, score in recommendations:
            stmt = select(Recommendation).where(
                and_(Recommendation.user_id == user_id, Recommendation.candidate_id == cand.id)
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                existing.score = score
                existing.viewed = False
            else:
                rec = Recommendation(user_id=user_id, candidate_id=cand.id, score=score)
                session.add(rec)
        await session.commit()


async def get_next_recommendation(user_id: int) -> Optional[Recommendation]:
    """Получает следующую непросмотренную рекомендацию для пользователя."""
    async with async_session() as session:
        stmt = (
            select(Recommendation)
            .where(
                and_(Recommendation.user_id == user_id, Recommendation.viewed == False)
            )
            .order_by(desc(Recommendation.score))
            .limit(1)
        )
        result = await session.execute(stmt)
        rec = result.scalar_one_or_none()
        return rec

async def mark_recommendation_viewed(rec_id: int):
    async with async_session() as session:
        rec = await session.get(Recommendation, rec_id)
        if rec:
            rec.viewed = True
            await session.commit()


async def update_recommendation_status(rec_id: int, status: str):
    async with async_session() as session:
        rec = await session.get(Recommendation, rec_id)
        if rec:
            rec.status = status
            rec.viewed = True
            await session.commit()


# ---------- Лайки и мэтчи ----------
async def create_like(from_user_id: int, to_user_id: int) -> bool:
    """Returns True if a mutual like (match) exists or is created."""
    async with async_session() as session:
        stmt_like = select(Like).where(
            and_(Like.from_user_id == from_user_id, Like.to_user_id == to_user_id)
        )
        existing_like = await session.execute(stmt_like)
        if existing_like.scalar_one_or_none():
            pass
        else:
            like = Like(from_user_id=from_user_id, to_user_id=to_user_id)
            session.add(like)
            await session.flush()

        stmt_reverse = select(Like).where(
            and_(Like.from_user_id == to_user_id, Like.to_user_id == from_user_id)
        )
        reverse_like_result = await session.execute(stmt_reverse)
        reverse_like = reverse_like_result.scalar_one_or_none()

        if reverse_like:
            user1, user2 = min(from_user_id, to_user_id), max(from_user_id, to_user_id)

            stmt_match = select(Match).where(
                and_(Match.user1_id == user1, Match.user2_id == user2)
            )
            existing_match = await session.execute(stmt_match)
            match = existing_match.scalar_one_or_none()

            if not match:
                match = Match(user1_id=user1, user2_id=user2)
                session.add(match)

            if 'like' in locals():
                await session.delete(like)
            if reverse_like:
                await session.delete(reverse_like)

            await session.commit()
            return True

        else:
            await session.commit()
            return False

async def delete_likes(user1_id: int, user2_id: int):
    async with async_session() as session:
        await session.execute(
            delete(Like).where(
                or_(
                    and_(Like.from_user_id == user1_id, Like.to_user_id == user2_id),
                    and_(Like.from_user_id == user2_id, Like.to_user_id == user1_id)
                )
            )
        )
        await session.commit()


async def get_matches(user_id: int) -> List[Match]:
    async with async_session() as session:
        result = await session.execute(
            select(Match).where(
                or_(Match.user1_id == user_id, Match.user2_id == user_id)
            )
        )
        return result.scalars().all()