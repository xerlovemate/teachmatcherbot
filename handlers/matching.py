from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database.requests import (
    get_user_by_tg_id, get_user_with_skills, get_user_by_id,
    get_user_by_id_with_skills,
    generate_recommendations_for_user, save_recommendations,
    get_next_recommendation, mark_recommendation_viewed,
    create_like, get_matches, update_recommendation_status, delete_likes
)

router = Router()


class FindMentor(StatesGroup):
    browsing = State()


async def send_profile_with_actions(chat_id: int, user_to_show, bot: Bot, action_prefix="like_user"):
    """Отправляет профиль пользователя с кнопками 👍 и 👎 в указанный чат."""
    role = "Наставляемый" if user_to_show.is_student else "Наставник"
    caption = f"<b>{role}: {user_to_show.name}</b>\n"
    if user_to_show.about:
        caption += f"📝 <b>О себе:</b>\n{user_to_show.about}\n"
    if user_to_show.description:
        caption += f"📋 <b>Детали:</b>\n{user_to_show.description}\n"
    if user_to_show.work_style:
        caption += f"🧠 <b>Стиль работы:</b> {user_to_show.work_style}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍", callback_data=f"like_user_{user_to_show.id}"),
            InlineKeyboardButton(text="👎", callback_data=f"dislike_user_{user_to_show.id}")
        ]
    ])

    if user_to_show.photo_id:
        await bot.send_photo(chat_id=chat_id, photo=user_to_show.photo_id, caption=caption, reply_markup=kb, parse_mode="HTML")
    else:
        await bot.send_message(chat_id=chat_id, text=caption, reply_markup=kb, parse_mode="HTML")


@router.message(Command("find"))
async def cmd_find(message: Message, state: FSMContext):
    user = await get_user_by_tg_id(message.from_user.id)
    if not user:
        await message.answer("Сначала заполните анкету через /start")
        return

    await message.answer("🔍 ИИ анализирует Ваши данные и подбирает наиболее подходящие анкеты...")
    recommendations = await generate_recommendations_for_user(user)
    if not recommendations:
        await message.answer("К сожалению, пока нет подходящих анкет. Попробуйте позже.")
        return

    await save_recommendations(user.id, recommendations)
    await state.set_state(FindMentor.browsing)
    await show_next_recommendation_for_user(message, user.id, state)


async def show_next_recommendation_for_user(message: Message, user_id: int, state: FSMContext):
    """Показывает следующую рекомендацию для пользователя с указанным ID."""
    rec = await get_next_recommendation(user_id)
    if not rec:
        await message.answer("Вы просмотрели все рекомендации. Чтобы обновить список, используйте /find снова.")
        await state.clear()
        return

    candidate = await get_user_by_id_with_skills(rec.candidate_id)
    if not candidate:
        await mark_recommendation_viewed(rec.id)
        await show_next_recommendation_for_user(message, user_id, state)
        return

    role = "Наставляемый" if candidate.is_student else "Наставник"
    caption = f"<b>{role}: {candidate.name}</b>\n"
    if candidate.about:
        caption += f"📝 <b>О себе:</b>\n{candidate.about}\n"
    if candidate.description:
        caption += f"📋 <b>Детали:</b>\n{candidate.description}\n"
    if candidate.work_style:
        caption += f"🧠 <b>Стиль работы:</b> {candidate.work_style}\n"
    caption += f"\n✨ <b>Совпадение:</b> {rec.score*100:.1f}%"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍", callback_data=f"like_{rec.id}"),
            InlineKeyboardButton(text="👎", callback_data=f"dislike_{rec.id}"),
            InlineKeyboardButton(text="➡️", callback_data=f"skip_{rec.id}")
        ],
        [InlineKeyboardButton(text="❌ Завершить поиск", callback_data="stop_find")]
    ])

    if candidate.photo_id:
        await message.answer_photo(photo=candidate.photo_id, caption=caption, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(caption, reply_markup=kb, parse_mode="HTML")

    await mark_recommendation_viewed(rec.id)


@router.callback_query(FindMentor.browsing, F.data.startswith("like_"))
async def like_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    rec_id = int(callback.data.split("_")[1])

    user = await get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.message.edit_text("Ошибка: пользователь не найден. Начните заново /start")
        await state.clear()
        return

    from database.models import Recommendation
    from database.requests import async_session
    async with async_session() as session:
        rec = await session.get(Recommendation, rec_id)
        if not rec:
            await callback.answer("Ошибка: рекомендация не найдена")
            return
        candidate_id = rec.candidate_id

    is_mutual = await create_like(user.id, candidate_id)

    candidate = await get_user_by_id(candidate_id)
    if not candidate:
        await callback.answer("Ошибка: кандидат не найден")
        return

    if is_mutual:
        user_kb = None
        candidate_kb = None
        if candidate.tg_id:
            user_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✉️ Написать", url=f"tg://user?id={candidate.tg_id}")]
            ])
        if user.tg_id:
            candidate_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✉️ Написать", url=f"tg://user?id={user.tg_id}")]
            ])

        await bot.send_message(
            user.tg_id,
            f"🎉 У Вас взаимный интерес с <b>{candidate.name}</b>!",
            reply_markup=user_kb,
            parse_mode="HTML"
        )
        await bot.send_message(
            candidate.tg_id,
            f"🎉 У Вас взаимный интерес с <b>{user.name}</b>!",
            reply_markup=candidate_kb,
            parse_mode="HTML"
        )
    else:
        await send_profile_with_actions(candidate.tg_id, user, bot)

    await callback.answer("👍")
    await show_next_recommendation_for_user(callback.message, user.id, state)


@router.callback_query(FindMentor.browsing, F.data.startswith("dislike_"))
async def dislike_callback(callback: CallbackQuery, state: FSMContext):
    rec_id = int(callback.data.split("_")[1])
    await update_recommendation_status(rec_id, "rejected")

    user = await get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.message.edit_text("Ошибка: пользователь не найден. Начните заново /start")
        await state.clear()
        return

    await callback.answer("👎")
    await show_next_recommendation_for_user(callback.message, user.id, state)


@router.callback_query(FindMentor.browsing, F.data.startswith("skip_"))
async def skip_callback(callback: CallbackQuery, state: FSMContext):
    rec_id = int(callback.data.split("_")[1])
    await update_recommendation_status(rec_id, "skipped")

    user = await get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.message.edit_text("Ошибка: пользователь не найден. Начните заново /start")
        await state.clear()
        return

    await callback.answer("➡️")
    await show_next_recommendation_for_user(callback.message, user.id, state)


@router.callback_query(F.data.startswith("like_user_"))
async def like_user_callback(callback: CallbackQuery, bot: Bot):
    """Обработчик ответного лайка на профиль пользователя."""
    target_id = int(callback.data.split("_")[2])
    current_user = await get_user_by_tg_id(callback.from_user.id)
    if not current_user:
        await callback.answer("Ошибка: пользователь не найден")
        return

    target_user = await get_user_by_id(target_id)
    if not target_user:
        await callback.answer("Ошибка: целевой пользователь не найден")
        return

    is_mutual = await create_like(current_user.id, target_id)

    if is_mutual:
        current_kb = None
        target_kb = None
        if target_user.tg_id:
            current_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✉️ Написать", url=f"tg://user?id={target_user.tg_id}")]
            ])
        if current_user.tg_id:
            target_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✉️ Написать", url=f"tg://user?id={current_user.tg_id}")]
            ])

        await bot.send_message(
            current_user.tg_id,
            f"🎉 У Вас взаимный интерес с <b>{target_user.name}</b>!",
            reply_markup=current_kb,
            parse_mode="HTML"
        )
        await bot.send_message(
            target_user.tg_id,
            f"🎉 У Вас взаимный интерес с <b>{current_user.name}</b>!",
            reply_markup=target_kb,
            parse_mode="HTML"
        )
    else:
        await send_profile_with_actions(target_user.tg_id, current_user, bot)

    await callback.answer("👍")
    await callback.message.delete()


@router.callback_query(F.data.startswith("dislike_user_"))
async def dislike_user_callback(callback: CallbackQuery):
    """Обработчик дизлайка на профиль пользователя."""
    target_id = int(callback.data.split("_")[2])
    current_user = await get_user_by_tg_id(callback.from_user.id)
    if not current_user:
        await callback.answer("Ошибка: пользователь не найден")
        return

    await delete_likes(current_user.id, target_id)

    await callback.answer("👎")
    await callback.message.delete()


@router.callback_query(F.data == "stop_find")
async def stop_find(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Поиск завершен.")


@router.callback_query(F.data.startswith("view_user_"))
async def view_user_callback(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    user = await get_user_by_id(user_id)
    if not user:
        await callback.answer("Пользователь не найден")
        return

    role = "Наставляемый" if user.is_student else "Наставник"
    caption = f"<b>{role}: {user.name}</b>\n"
    if user.about:
        caption += f"📝 <b>О себе:</b>\n{user.about}\n"
    if user.description:
        caption += f"📋 <b>Детали:</b>\n{user.description}\n"
    if user.work_style:
        caption += f"🧠 <b>Стиль работы:</b> {user.work_style}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Написать", url=f"tg://user?id={user.tg_id}")]
    ]) if user.tg_id else None

    if user.photo_id:
        await callback.message.answer_photo(photo=user.photo_id, caption=caption, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.answer(caption, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.message(Command("matches"))
async def cmd_matches(message: Message):
    user = await get_user_by_tg_id(message.from_user.id)
    if not user:
        await message.answer("Сначала заполните анкету")
        return

    matches = await get_matches(user.id)
    if not matches:
        await message.answer("У Вас пока нет совпадений.")
        return

    text = "🎉 Ваши совпадения:\n"
    for match in matches:
        other_id = match.user2_id if match.user1_id == user.id else match.user1_id
        other = await get_user_by_id(other_id)
        if other:
            username = f"@{other.tg_username}" if other.tg_username else "нет логина"
            text += f"• {other.name} – {username}\n"
    await message.answer(text)