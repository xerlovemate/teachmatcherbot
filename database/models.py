from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Column, Boolean, ForeignKey, Text, UniqueConstraint, Float
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3')
async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    tg_username: Mapped[str] = mapped_column(String, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    name: Mapped[str] = mapped_column(String, nullable=True)
    is_student: Mapped[bool] = mapped_column(Boolean)          # True = наставляемый, False = наставник
    description: Mapped[str] = mapped_column(String, nullable=True)
    about: Mapped[str] = mapped_column(Text, nullable=True)
    work_style: Mapped[str] = mapped_column(String, nullable=True)

    price: Mapped[int] = mapped_column(Integer, nullable=True)
    online: Mapped[bool] = mapped_column(Boolean)
    city: Mapped[str] = mapped_column(String, nullable=True)
    photo_id: Mapped[str] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    skills = relationship('Skill', secondary='user_skills', back_populates='users')


class Skill(Base):
    __tablename__ = 'skills'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    users = relationship('User', secondary='user_skills', back_populates='skills')


class UserSkill(Base):
    __tablename__ = 'user_skills'

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey('skills.id'), primary_key=True)


class Recommendation(Base):
    __tablename__ = 'recommendations'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    candidate_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String, default='pending')
    viewed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('user_id', 'candidate_id', name='unique_recommendation'),)


class Like(Base):
    __tablename__ = 'likes'

    id: Mapped[int] = mapped_column(primary_key=True)
    from_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    to_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('from_user_id', 'to_user_id', name='unique_like'),)


class Match(Base):
    __tablename__ = 'matches'

    id: Mapped[int] = mapped_column(primary_key=True)
    user1_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    user2_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('user1_id', 'user2_id', name='unique_match'),)


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)