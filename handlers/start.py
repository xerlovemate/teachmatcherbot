import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from database.requests import (
    get_user_by_tg_id,
    get_user_with_skills,
    create_user,
    add_skills_to_user,
    delete_user_by_tg_id
)

router = Router()

# ---------- Состояния ----------
class RegistrationStart(StatesGroup):
    name = State()

class StudentRegistration(StatesGroup):
    goal = State()
    purpose = State()
    level = State()
    format = State()
    city = State()
    budget = State()
    deadline = State()
    skills = State()
    photo = State()

class TeacherRegistration(StatesGroup):
    subject = State()
    experience = State()
    audience = State()
    methodology = State()
    format = State()
    city = State()
    price = State()
    skills = State()
    photo = State()


# ---------- Вспомогательные функции ----------
def parse_keywords(text: str):
    return [kw.strip().lower() for kw in text.split(',') if kw.strip()]


# ---------- Клавиатуры со стилями ----------
def role_keyboard():
    buttons = [
        [InlineKeyboardButton(text="Я студент", callback_data="role_student", icon_custom_emoji_id='5291873250291229791')],
        [InlineKeyboardButton(text="Я преподаватель", callback_data="role_teacher", icon_custom_emoji_id='5373039692574893940')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cancel_keyboard():
    buttons = [[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def level_keyboard(selected_callback_data: str = None):
    levels = [
        ("0", "level_0"),
        ("1", "level_1"),
        ("2", "level_2"),
        ("3", "level_3"),
        ("4", "level_4"),
        ("5", "level_5"),
    ]
    buttons = []
    row = []
    for text, cb in levels:
        style = "success" if cb == selected_callback_data else None
        row.append(InlineKeyboardButton(text=text, callback_data=cb, style=style))
    buttons.append(row)
    buttons.append([
        InlineKeyboardButton(text="Продолжить", callback_data="level_save", icon_custom_emoji_id='5253767677670862169')
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def format_keyboard(selected_callback_data: str = None):
    options = [
        ("🌍 Онлайн", "format_online"),
        ("🏢 Оффлайн", "format_offline")
    ]
    buttons = []
    row = []
    for text, cb in options:
        style = "success" if cb == selected_callback_data else None
        row.append(InlineKeyboardButton(text=text, callback_data=cb, style=style))
    buttons.append(row)
    buttons.append([
        InlineKeyboardButton(text="Продолжить", callback_data="format_save", icon_custom_emoji_id='5253767677670862169'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def experience_keyboard(selected_callback_data: str = None):
    options = [
        ("Менее года", "exp_1"),
        ("1–3 года", "exp_2"),
        ("3–5 лет", "exp_3"),
        ("Более 5 лет", "exp_4")
    ]
    buttons = []
    for text, cb in options:
        style = "success" if cb == selected_callback_data else None
        buttons.append([InlineKeyboardButton(text=text, callback_data=cb, style=style)])
    buttons.append([
        InlineKeyboardButton(text="Продолжить", callback_data="exp_save", icon_custom_emoji_id='5253767677670862169'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def skills_keyboard(selected_skills: list = None):
    if selected_skills is None:
        selected_skills = []
    all_skills = [
        "Python", "JavaScript", "Java", "C++", "SQL", "HTML/CSS",
        "Математика", "Физика", "Английский язык", "История",
        "Рисование", "Музыка", "Подготовка к ЕГЭ", "Программирование"
    ]
    buttons = []
    row = []
    for skill in all_skills:
        style = "success" if skill in selected_skills else None
        row.append(InlineKeyboardButton(text=skill, callback_data=f"skill_{skill}", style=style))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton(text="Продолжить", callback_data="skills_save", icon_custom_emoji_id='5253767677670862169'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def profile_keyboard():
    buttons = [[InlineKeyboardButton(text="📝 Заполнить анкету заново", callback_data="reprofile")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------- Команда /start ----------
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    user = await get_user_by_tg_id(tg_id)
    if user:
        await show_profile(message, tg_id)
    else:
        await state.clear()
        await state.set_state(RegistrationStart.name)
        await message.answer('<tg-emoji emoji-id="5343984088493599366">👋</tg-emoji> Привет! Как тебя зовут?', parse_mode='HTML')


@router.message(RegistrationStart.name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя должно быть не короче 2 символов. Попробуй ещё раз.")
        return
    await state.update_data(name=name)
    await message.answer("Кто ты?", reply_markup=role_keyboard())


# ---------- Обработка роли ----------
@router.callback_query(F.data.startswith("role_"))
async def process_role(callback: CallbackQuery, state: FSMContext):
    role = callback.data
    data = await state.get_data()
    name = data.get('name')
    if not name:
        await callback.message.edit_text("Ошибка. Начни заново /start")
        await state.clear()
        return

    if role == "role_student":
        await state.set_state(StudentRegistration.goal)
        await callback.message.edit_text(
            "<b>Отлично! Давай заполним анкету.</b>\n\n"
            "1. Что ты хочешь изучить? (например, Python для GameDev)",
            parse_mode='HTML'
        )
    else:
        await state.set_state(TeacherRegistration.subject)
        await callback.message.edit_text(
            "<b>Отлично! Давай заполним анкету.</b>\n\n"
            "1. Чему ты учишь? (например, Python, игровые механики, Pygame)",
            parse_mode='HTML'
        )
    await callback.answer()


# ---------- Студент ----------
@router.message(StudentRegistration.goal)
async def student_goal(message: Message, state: FSMContext):
    await state.update_data(goal=message.text)
    await state.set_state(StudentRegistration.purpose)
    await message.answer("2. Для чего тебе это? (экзамен, работа, хобби)")

@router.message(StudentRegistration.purpose)
async def student_purpose(message: Message, state: FSMContext):
    await state.update_data(purpose=message.text)
    await state.set_state(StudentRegistration.level)
    await message.answer(
        "3. Твой уровень знаний (0–5), где 0 — новичок, 5 — эксперт",
        reply_markup=level_keyboard()
    )

@router.callback_query(StudentRegistration.level, F.data.startswith("level_"))
async def student_level_callback(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "level_save":
        user_data = await state.get_data()
        selected = user_data.get('selected_level')
        if selected is None:
            await callback.answer("Сначала выбери уровень!", show_alert=True)
            return
        level = int(selected.split('_')[1])
        await state.update_data(level=level)
        await state.set_state(StudentRegistration.format)
        await callback.message.edit_text(
            "4. Какой формат занятий предпочитаешь?\nВыбери один вариант.",
            reply_markup=format_keyboard()
        )
        await callback.answer()
    else:
        await state.update_data(selected_level=data)
        await callback.message.edit_reply_markup(reply_markup=level_keyboard(selected_callback_data=data))
        await callback.answer()

@router.callback_query(StudentRegistration.format, F.data.in_(["format_online", "format_offline"]))
async def student_format_callback(callback: CallbackQuery, state: FSMContext):
    await state.update_data(selected_format=callback.data)
    await callback.message.edit_reply_markup(reply_markup=format_keyboard(selected_callback_data=callback.data))
    await callback.answer()

@router.callback_query(StudentRegistration.format, F.data == "format_save")
async def student_format_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get('selected_format')
    if selected is None:
        await callback.answer("Сначала выбери формат!", show_alert=True)
        return
    online = (selected == "format_online")
    await state.update_data(online=online)
    if not online:
        await state.set_state(StudentRegistration.city)
        await callback.message.edit_text("В каком городе планируешь заниматься оффлайн?")
    else:
        await state.update_data(city=None)
        await state.set_state(StudentRegistration.budget)
        await callback.message.edit_text("5. Какой бюджет в месяц (в рублях)?")
    await callback.answer()

@router.message(StudentRegistration.city)
async def student_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(StudentRegistration.budget)
    await message.answer("5. Какой бюджет в месяц (в рублях)?")

@router.message(StudentRegistration.budget)
async def student_budget(message: Message, state: FSMContext):
    try:
        budget = int(message.text)
        if budget <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Бюджет должен быть положительным числом. Попробуй ещё раз.")
        return
    await state.update_data(budget=budget)
    await state.set_state(StudentRegistration.deadline)
    await message.answer("6. В какие сроки планируешь достичь цели? (например, 3 месяца)")

@router.message(StudentRegistration.deadline)
async def student_deadline(message: Message, state: FSMContext):
    await state.update_data(deadline=message.text)
    await state.set_state(StudentRegistration.skills)
    await message.answer(
        "7. Выбери ключевые навыки, которые важны в преподавателе (можно несколько):",
        reply_markup=skills_keyboard()
    )

@router.callback_query(StudentRegistration.skills, F.data.startswith("skill_"))
async def student_skills_toggle(callback: CallbackQuery, state: FSMContext):
    skill = callback.data.replace("skill_", "")
    data = await state.get_data()
    selected = data.get('selected_skills', [])
    if skill in selected:
        selected.remove(skill)
    else:
        selected.append(skill)
    await state.update_data(selected_skills=selected)
    await callback.message.edit_reply_markup(reply_markup=skills_keyboard(selected))
    await callback.answer()

@router.callback_query(StudentRegistration.skills, F.data == "skills_save")
async def student_skills_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get('selected_skills', [])
    if not selected:
        await callback.answer("Выбери хотя бы один навык!", show_alert=True)
        return
    await state.update_data(skills_text=", ".join(selected))
    await state.set_state(StudentRegistration.photo)
    await callback.message.edit_text("Последний шаг — отправь своё фото (или фото-аватар).")
    await callback.answer()

@router.message(StudentRegistration.photo, F.photo)
async def student_photo(message: Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()

    goal = data['goal']
    purpose = data['purpose']
    level = data['level']
    deadline = data['deadline']
    online = data['online']
    city = data.get('city', 'не указан')
    budget = data['budget']
    skills_text = data['skills_text']

    format_text = "онлайн" if online else f"оффлайн ({city})"
    description = (
        f"🎯 Цель: {goal}\n"
        f"📌 Для чего: {purpose}\n"
        f"📊 Уровень: {level}/5\n"
        f"⏳ Сроки: {deadline}\n"
        f"💻 Формат: {format_text}\n"
        f"💰 Бюджет: {budget} руб/мес\n"
        f"🔑 Ключевые навыки: {skills_text}"
    )

    # Создаём пользователя в БД
    user = await create_user(
        tg_id=message.from_user.id,
        tg_username=message.from_user.username,
        name=data['name'],
        is_student=True,
        description=description,
        price=budget,
        online=online,
        city=city if not online else None,
        photo_id=photo_id
    )

    # Добавляем навыки
    kw_list = parse_keywords(skills_text)
    goal_words = parse_keywords(goal)
    all_keywords = list(set(kw_list + goal_words))
    await add_skills_to_user(user.id, all_keywords)

    await state.clear()
    await message.answer(
        '<tg-emoji emoji-id="5316827280863934685">✅</tg-emoji> Анкета студента успешно создана!',
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='HTML'
    )
    await show_profile(message, message.from_user.id)


# ---------- Преподаватель ----------
@router.message(TeacherRegistration.subject)
async def teacher_subject(message: Message, state: FSMContext):
    await state.update_data(subject=message.text)
    await state.set_state(TeacherRegistration.experience)
    await message.answer("2. Какой у тебя опыт?", reply_markup=experience_keyboard())

@router.callback_query(TeacherRegistration.experience, F.data.startswith("exp_"))
async def teacher_experience_callback(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "exp_save":
        user_data = await state.get_data()
        selected = user_data.get('selected_experience')
        if selected is None:
            await callback.answer("Сначала выбери опыт!", show_alert=True)
            return
        exp_map = {
            "exp_1": "Менее года",
            "exp_2": "1–3 года",
            "exp_3": "3–5 лет",
            "exp_4": "Более 5 лет"
        }
        experience = exp_map[selected]
        await state.update_data(experience=experience)
        await state.set_state(TeacherRegistration.audience)
        await callback.message.edit_text("3. Кому ты подходишь? (школьники, студенты, начинающие и т.д.)")
        await callback.answer()
    else:
        await state.update_data(selected_experience=data)
        await callback.message.edit_reply_markup(reply_markup=experience_keyboard(selected_callback_data=data))
        await callback.answer()

@router.message(TeacherRegistration.audience)
async def teacher_audience(message: Message, state: FSMContext):
    await state.update_data(audience=message.text)
    await state.set_state(TeacherRegistration.methodology)
    await message.answer("4. Какая у тебя методика обучения?")

@router.message(TeacherRegistration.methodology)
async def teacher_methodology(message: Message, state: FSMContext):
    await state.update_data(methodology=message.text)
    await state.set_state(TeacherRegistration.format)
    await message.answer(
        "5. Какой формат занятий предлагаешь?\nВыбери один вариант.",
        reply_markup=format_keyboard()
    )

@router.callback_query(TeacherRegistration.format, F.data.in_(["format_online", "format_offline"]))
async def teacher_format_callback(callback: CallbackQuery, state: FSMContext):
    await state.update_data(selected_format=callback.data)
    await callback.message.edit_reply_markup(reply_markup=format_keyboard(selected_callback_data=callback.data))
    await callback.answer()

@router.callback_query(TeacherRegistration.format, F.data == "format_save")
async def teacher_format_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get('selected_format')
    if selected is None:
        await callback.answer("Сначала выбери формат!", show_alert=True)
        return
    online = (selected == "format_online")
    await state.update_data(online=online)
    if not online:
        await state.set_state(TeacherRegistration.city)
        await callback.message.edit_text("В каком городе проводишь очные занятия?")
    else:
        await state.update_data(city=None)
        await state.set_state(TeacherRegistration.price)
        await callback.message.edit_text("6. Какая стоимость одного занятия (в рублях)?")
    await callback.answer()

@router.message(TeacherRegistration.city)
async def teacher_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(TeacherRegistration.price)
    await message.answer("6. Какая стоимость одного занятия (в рублях)?")

@router.message(TeacherRegistration.price)
async def teacher_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Цена должна быть положительным числом. Попробуй ещё раз.")
        return
    await state.update_data(price=price)
    await state.set_state(TeacherRegistration.skills)
    await message.answer(
        "7. Выбери ключевые навыки (можно несколько):",
        reply_markup=skills_keyboard()
    )

@router.callback_query(TeacherRegistration.skills, F.data.startswith("skill_"))
async def teacher_skills_toggle(callback: CallbackQuery, state: FSMContext):
    skill = callback.data.replace("skill_", "")
    data = await state.get_data()
    selected = data.get('selected_skills', [])
    if skill in selected:
        selected.remove(skill)
    else:
        selected.append(skill)
    await state.update_data(selected_skills=selected)
    await callback.message.edit_reply_markup(reply_markup=skills_keyboard(selected))
    await callback.answer()

@router.callback_query(TeacherRegistration.skills, F.data == "skills_save")
async def teacher_skills_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get('selected_skills', [])
    if not selected:
        await callback.answer("Выбери хотя бы один навык!", show_alert=True)
        return
    await state.update_data(skills_text=", ".join(selected))
    await state.set_state(TeacherRegistration.photo)
    await callback.message.edit_text("Последний шаг — отправь своё фото (или фото-аватар).")
    await callback.answer()

@router.message(TeacherRegistration.photo, F.photo)
async def teacher_photo(message: Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()

    subject = data['subject']
    experience = data['experience']
    audience = data['audience']
    methodology = data['methodology']
    online = data['online']
    city = data.get('city', 'не указан')
    price = data['price']
    skills_text = data['skills_text']

    format_text = "онлайн" if online else f"оффлайн ({city})"
    description = (
        f"📚 Предметы: {subject}\n"
        f"⏳ Опыт: {experience}\n"
        f"👥 Кому подходит: {audience}\n"
        f"🧠 Методика: {methodology}\n"
        f"💻 Формат: {format_text}\n"
        f"💰 Цена: {price} руб/занятие\n"
        f"🔑 Ключевые навыки: {skills_text}"
    )

    user = await create_user(
        tg_id=message.from_user.id,
        tg_username=message.from_user.username,
        name=data['name'],
        is_student=False,
        description=description,
        price=price,
        online=online,
        city=city if not online else None,
        photo_id=photo_id
    )

    kw_list = parse_keywords(skills_text)
    subject_words = parse_keywords(subject)
    all_keywords = list(set(kw_list + subject_words))
    await add_skills_to_user(user.id, all_keywords)

    await state.clear()
    await message.answer(
        "✅ Анкета преподавателя успешно создана!",
        reply_markup=ReplyKeyboardRemove()
    )
    await show_profile(message, message.from_user.id)


# ---------- Отмена ----------
@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Регистрация отменена. Если захочешь начать заново, нажми /start")
    await callback.answer()


# ---------- Показ профиля ----------
async def show_profile(message: Message, tg_id: int):
    user = await get_user_with_skills(tg_id)
    if not user:
        await message.answer("Профиль не найден.")
        return

    role = "Студент" if user.is_student else "Преподаватель"

    parts = []
    parts.append(f"👤 <b>{user.name}</b>  |  <i>{role}</i>")
    parts.append("─────────────")

    if user.description:
        parts.append(f"📝 <b>О себе:</b>\n<blockquote>{user.description}</blockquote>")
    else:
        parts.append("📝 <b>О себе:</b> не указано")

    price_label = "Бюджет" if user.is_student else "Цена"
    price_value = f"{user.price} руб." if user.price else "не указано"
    parts.append(f"💰 <b>{price_label}:</b> {price_value}")

    if user.online:
        format_text = "🌍 Онлайн"
    else:
        city_text = user.city if user.city else "город не указан"
        format_text = f"🏢 Оффлайн ({city_text})"
    parts.append(f"💻 <b>Формат:</b> {format_text}")

    caption = "\n".join(parts)

    if user.photo_id:
        await message.answer_photo(
            photo=user.photo_id,
            caption=caption,
            reply_markup=profile_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            caption,
            reply_markup=profile_keyboard(),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "reprofile")
async def reprofile_callback(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    await delete_user_by_tg_id(tg_id)
    await state.clear()
    await state.set_state(RegistrationStart.name)
    await callback.message.edit_text("👋 Давай заполним анкету заново. Как тебя зовут?")
    await callback.answer()


# ---------- Заглушки для неверных сообщений ----------
@router.message(StudentRegistration.photo)
async def student_photo_invalid(message: Message):
    await message.answer("Пожалуйста, отправьте фото.")

@router.message(TeacherRegistration.photo)
async def teacher_photo_invalid(message: Message):
    await message.answer("Пожалуйста, отправьте фото.")