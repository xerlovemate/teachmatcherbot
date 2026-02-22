from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Integer, Column, Boolean, ForeignKey, Text, UniqueConstraint, \
    Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

# Создание движка для асинхронного взаимодействия с базой данных SQLite
engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3')

# Создание асинхронной сессии для работы с базой данных
async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


class User(Base):
    """Класс пользователей"""
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)  # id в базе данных

    tg_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)  # tg id юзера
    tg_username: Mapped[str] = mapped_column(String, nullable=True)  # юзернейм тг

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)  # является ли администратором

    name: Mapped[str] = mapped_column(String, nullable=True)  # имя
    is_student: Mapped[bool] = mapped_column(Boolean)  # является ли студентом (ищет преподавателя)
    description: Mapped[str] = mapped_column(String, nullable=True)  # описание анкеты

    price: Mapped[int] = mapped_column(Integer, nullable=True)  # цена за занятие (для преподавателя) или бюджет (для студента)
    online: Mapped[bool] = mapped_column(Boolean)  # только онлайн или возможны очные занятия
    city: Mapped[str] = mapped_column(String, nullable=True)  # город (для очных занятий)

    photo_id: Mapped[str] = mapped_column(String, nullable=True) # id фотки

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # дата создания записи
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # дата обновления

    # Связь многие-ко-многим с навыками
    skills = relationship('Skill', secondary='user_skills', back_populates='users')


class Skill(Base):
    """Класс навыков (предметов/тематик)"""
    __tablename__ = 'skills'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)  # название навыка

    # Обратная связь
    users = relationship('User', secondary='user_skills', back_populates='skills')


class UserSkill(Base):
    """Связующая таблица между пользователями и навыками"""
    __tablename__ = 'user_skills'

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey('skills.id'), primary_key=True)


async def async_main():
    """Создание таблиц в базе данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)