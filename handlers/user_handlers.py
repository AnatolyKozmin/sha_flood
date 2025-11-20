from aiogram import Router, F
from aiogram.types import Message, ChatPermissions
from aiogram.filters import Command
from aiogram.utils.markdown import hbold
from sqlalchemy import select, update, or_
from datetime import datetime, timedelta
import random
from io import BytesIO

from database.engine import AsyncSessionLocal
from database.models import User, Quote, BeerStat, Wakeup
from utils import load_users_from_excel
from pathlib import Path

router = Router()


def html_escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@router.message(F.text.regexp(r"^!помощь\b", flags=0))
@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📖 Доступные команды:\n\n"
        "• !инфа [фамилия/юзернейм] — инфо об организаторе\n"
        "• !цитата (в ответ) — сохранить цитату\n"
        "• !мудрость — случайная цитата (картинка)\n"
        "• !рулетка — шанс 1/6 получить мут на 10 мин\n"
        "• !разбудить DD.MM.YYYY HH:MM — напоминание в чате\n"
        "• !орг дня — случайный организатор дня\n"
        "• !нахуй (в ответ) — адресный ответ\n"
        "• !обосновать (в ответ) — адресный ответ\n"
        "• !когда — сколько осталось до 27.11.2025\n"
        "• !вероятность [событие] — шанс в процентах\n"
        "• !налить пиво (в ответ) — +1 пива пользователю\n"
        "• !статистика пива — рейтинг по пиву\n"
        "• !адрес [фамилия] — адрес организатора\n"
        "• !перепарсить — перезагрузить данные из Excel (только для админов)\n"
        "• !кто [текст] — случайный человек и упоминание\n"
    )
    await message.answer(text, parse_mode=None)


@router.message(F.text.regexp(r"^!инфа\s+(.+)", flags=0))
async def cmd_info(message: Message):
    query = (message.text or "").split(maxsplit=1)[1].strip()
    
    # Убираем @ если есть
    search_query = query.lstrip('@')
    
    async with AsyncSessionLocal() as session:
        # Ищем и по фамилии, и по telegram_username
        result = await session.execute(
            select(User).where(
                or_(
                    User.full_name.ilike(f"%{search_query}%"),
                    User.telegram_username.ilike(f"%{search_query}%")
                )
            )
        )
        users = result.scalars().all()
    if not users:
        await message.answer(f"❌ Не найдено по запросу: <b>{html_escape(query)}</b>", parse_mode="HTML")
        return
    if len(users) == 1:
        u = users[0]
        parts = [
            f"👤 <b>{html_escape(u.full_name)}</b>",
            f"🏢 <b>Подразделение:</b> {html_escape(u.department)}",
        ]
        if u.telegram_username:
            parts.append(f"📱 <b>Telegram:</b> @{html_escape(u.telegram_username)}")
        if u.phone_number:
            parts.append(f"📞 <b>Телефон:</b> {html_escape(u.phone_number)}")
        if u.birth_date:
            parts.append(f"🎂 <b>Дата рождения:</b> {html_escape(u.birth_date)}")
        if u.faculty:
            parts.append(f"🎓 <b>Факультет:</b> {html_escape(u.faculty)}")
        if u.course:
            parts.append(f"📚 <b>Курс:</b> {u.course}")
        if u.study_group:
            parts.append(f"👥 <b>Группа:</b> {html_escape(u.study_group)}")
        if u.has_car:
            parts.append(f"🚗 <b>Авто/права:</b> {html_escape(u.has_car)}")
        if u.nearest_metro:
            parts.append(f"🚇 <b>Метро:</b> {html_escape(u.nearest_metro)}")
        if u.address:
            parts.append(f"🏠 <b>Адрес:</b> {html_escape(u.address)}")
        await message.answer("\n".join(parts), parse_mode="HTML")
    else:
        resp = [f"🔍 Найдено: <b>{len(users)}</b>\n"]
        for i, u in enumerate(users, 1):
            resp.append(f"{i}. <b>{html_escape(u.full_name)}</b> — {html_escape(u.department)}")
        await message.answer("\n".join(resp), parse_mode="HTML")


@router.message(F.reply_to_message & F.text.regexp(r"^!цитата\b", flags=0))
async def cmd_quote(message: Message):
    original = message.reply_to_message
    text = original.text or original.caption or ""
    if not text.strip():
        await message.answer("❌ В ответе нет текстовой цитаты.")
        return
    async with AsyncSessionLocal() as session:
        quote = Quote(
            chat_id=message.chat.id,
            author_user_id=original.from_user.id,
            author_name=original.from_user.full_name,
            quoter_user_id=message.from_user.id,
            text=text.strip()
        )
        session.add(quote)
        await session.commit()
    await message.answer(f"📝 Цитата сохранена от <b>{html_escape(original.from_user.full_name)}</b>.", parse_mode="HTML")
    # Генерация картинки будет добавлена отдельно (см. TODO quote_image_gen)


@router.message(F.text.regexp(r"^!мудрость\b", flags=0))
async def cmd_wisdom(message: Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Quote).where(Quote.chat_id == message.chat.id))
        quotes = result.scalars().all()
    if not quotes:
        await message.answer("🤷 Нет сохранённых цитат.")
        return
    q = random.choice(quotes)

    # Попробуем получить аватар автора
    photo_bytes = None
    try:
        photos = await message.bot.get_user_profile_photos(q.author_user_id, limit=1)
        if photos.total_count > 0:
            file = await message.bot.get_file(photos.photos[0][0].file_id)
            photo_bytes = await message.bot.download_file(file.file_path)
    except Exception:
        photo_bytes = None

    # Сгенерируем картинку
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (1080, 1080), color=(20, 20, 25))
        draw = ImageDraw.Draw(img)

        # Аватар (если есть)
        if photo_bytes:
            try:
                avatar = Image.open(BytesIO(photo_bytes.read() if hasattr(photo_bytes, "read") else photo_bytes))
                avatar = avatar.convert("RGB").resize((200, 200))
                img.paste(avatar, (50, 50))
            except Exception:
                pass

        # Текст
        margin_left = 280 if photo_bytes else 50
        try:
            font_title = ImageFont.truetype("arial.ttf", 48)
            font_text = ImageFont.truetype("arial.ttf", 44)
        except Exception:
            font_title = ImageFont.load_default()
            font_text = ImageFont.load_default()

        author = q.author_name or "Неизвестный"
        draw.text((margin_left, 60), author, font=font_title, fill=(255, 255, 255))

        # Разбивка цитаты на строки
        text = f"«{q.text}»"
        max_width = 980 - margin_left
        words = text.split()
        lines = []
        current = ""
        for w in words:
            test = (current + " " + w).strip()
            w_width, _ = draw.textbbox((0, 0), test, font=font_text)[2:4]
            if w_width > max_width and current:
                lines.append(current)
                current = w
            else:
                current = test
        if current:
            lines.append(current)

        y = 140
        for line in lines[:15]:
            draw.text((margin_left, y), line, font=font_text, fill=(220, 220, 220))
            y += 50

        bio = BytesIO()
        bio.name = "wisdom.png"
        img.save(bio, "PNG")
        bio.seek(0)
        await message.answer_photo(bio, caption=f"🧠 {html_escape(author)}", parse_mode="HTML")
        return
    except Exception:
        # Фоллбек — просто текст
        pass

    await message.answer(f"🧠 <b>{html_escape(q.author_name or 'Неизвестный')}</b>:\n«{html_escape(q.text)}»", parse_mode="HTML")


@router.message(F.text.regexp(r"^!рулетка\b", flags=0))
async def cmd_roulette(message: Message):
    chamber = random.randint(1, 6)
    if chamber == 1:
        until = datetime.utcnow() + timedelta(minutes=10)
        try:
            await message.bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until
            )
            await message.answer(f"🔫 Бах! {message.from_user.mention_html()} замьючен на 10 минут.", parse_mode="HTML")
        except Exception:
            await message.answer("❌ Не удалось выдать мут (нет прав у бота?).")
    else:
        await message.answer("🎉 Повезло! Патрон в другой каморе.")


@router.message(F.text.regexp(r"^!разбудить\s+(.+)$", flags=0))
async def cmd_wake(message: Message):
    raw = (message.text or "").split(maxsplit=1)[1].strip()
    # Ожидаемый формат: DD.MM.YYYY HH:MM
    try:
        wake_dt = datetime.strptime(raw, "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer("❌ Формат времени: 17.11.2025 11:00")
        return
    async with AsyncSessionLocal() as session:
        session.add(Wakeup(chat_id=message.chat.id, user_id=message.from_user.id, wake_at=wake_dt))
        await session.commit()
    await message.answer(f"⏰ Ок! Разбужу {message.from_user.mention_html()} в {wake_dt.strftime('%d.%m.%Y %H:%M')}.", parse_mode="HTML")


@router.message(F.text.regexp(r"^!орг\sдня\b|^!орг\sдня$", flags=0))
async def cmd_org_of_day(message: Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
    if not users:
        await message.answer("❌ В базе нет организаторов.")
        return
    u = random.choice(users)
    await message.answer(f"🏆 Организатор дня: <b>{html_escape(u.full_name)}</b> ({html_escape(u.department)}) 🎉", parse_mode="HTML")


@router.message(F.reply_to_message & F.text.regexp(r"^!нахуй\b", flags=0))
async def cmd_go_away(message: Message):
    target = message.reply_to_message.from_user
    await message.answer(f"{target.mention_html()} иди нахуй", parse_mode="HTML")


@router.message(F.text.regexp(r"^!когда\b", flags=0))
async def cmd_when(message: Message):
    target = datetime.strptime("27.11.2025 00:00", "%d.%m.%Y %H:%M")
    now = datetime.utcnow()
    delta = target - now
    if delta.total_seconds() <= 0:
        await message.answer("⏱ Уже наступило.")
        return
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    await message.answer(f"⏳ Осталось: {days} дн. {hours} ч. {minutes} мин.")


@router.message(F.text.regexp(r"^!вероятность(?:\s+.+)?$", flags=0))
async def cmd_probability(message: Message):
    p = random.randint(0, 100)
    await message.answer(f"📊 Вероятность: {p}%")


@router.message(F.text.regexp(r"^!налить\s+пиво\b", flags=0))
async def cmd_beer_pour(message: Message):
    # Ожидаем ответ на сообщение пользователя или упоминание
    target_id = None
    target_name = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.full_name
    elif message.entities:
        # простая попытка: если есть упоминание пользователя через @username — Telegram не всегда даёт id
        # В таком случае требуем ответом пользоваться
        pass
    if not target_id:
        await message.answer("🍺 Используй как ответ на сообщение того, кому наливаешь пиво.")
        return
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BeerStat).where(BeerStat.chat_id == message.chat.id, BeerStat.user_id == target_id)
        )
        stat = result.scalar_one_or_none()
        if stat:
            stat.count += 1
            stat.username = target_name
        else:
            stat = BeerStat(chat_id=message.chat.id, user_id=target_id, username=target_name, count=1)
            session.add(stat)
        await session.commit()
    await message.answer(f"🍻 Налито пива для {message.reply_to_message.from_user.mention_html()}! (+1)", parse_mode="HTML")


@router.message(F.text.regexp(r"^!статистика\s+пива\b|^!статистика\b", flags=0))
async def cmd_beer_stats(message: Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(BeerStat).where(BeerStat.chat_id == message.chat.id))
        stats = result.scalars().all()
    if not stats:
        await message.answer("🍺 Пока никому не наливали.")
        return
    stats.sort(key=lambda s: s.count, reverse=True)
    lines = ["🍺 Топ пивных друзей:\n"]
    for i, s in enumerate(stats, 1):
        display = s.username or f"id:{s.user_id}"
        lines.append(f"{i}. {html_escape(display)} — {s.count}")
    await message.answer("\n".join(lines))


@router.message(F.text.regexp(r"^!адрес\s+(.+)", flags=0))
async def cmd_address(message: Message):
    surname = (message.text or "").split(maxsplit=1)[1].strip()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.full_name.ilike(f"%{surname}%")))
        users = result.scalars().all()
    if not users:
        await message.answer("❌ Не найдено.")
        return
    user = users[0]
    if not user.address:
        await message.answer("🏠 Адрес не указан.")
        return
    await message.answer(f"🏠 Адрес {html_escape(user.full_name)}:\n{html_escape(user.address)}")


@router.message(F.reply_to_message & F.text.regexp(r"^!обосновать\b", flags=0))
async def cmd_obosnovat(message: Message):
    target = message.reply_to_message.from_user
    await message.answer(f"{target.mention_html()} а тебя это ебать не должно", parse_mode="HTML")


@router.message(F.text.regexp(r"^!кто\s+(.+)", flags=0))
async def cmd_who(message: Message):
    """Выбирает случайного человека и отправляет сообщение с упоминанием"""
    text = (message.text or "").split(maxsplit=1)[1].strip()
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
    
    if not users:
        await message.answer("❌ В базе нет организаторов.")
        return
    
    user = random.choice(users)
    user_name = html_escape(user.full_name)
    
    # Формируем сообщение в формате: {текст} - {человек}\n\n@{тег}
    # Если есть telegram_username, используем его
    if user.telegram_username:
        mention = f"@{user.telegram_username}"
    else:
        # Если нет username, создаем тег из имени (заменяем пробелы на подчеркивания)
        mention = f"@{user_name.replace(' ', '_')}"
    
    # Формат: {текст} - {человек}, затем две пустые строки, затем @{тег}
    response = f"{text} - {user_name}\n\n{mention}"
    
    await message.answer(response, parse_mode="HTML")


@router.message(F.text.regexp(r"^!перепарсить\b", flags=0))
async def cmd_reparse(message: Message):
    """Перезагружает данные из Excel файла"""
    # Проверяем права администратора
    if message.chat.type == 'private':
        await message.answer("❌ Эта команда доступна только в групповых чатах!")
        return
    
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ['creator', 'administrator']:
        await message.answer("❌ Только администраторы могут перезагружать данные!")
        return
    
    # Ищем файл user_data.xlsx
    excel_paths = [
        "user_data.xlsx",
        "/app/user_data.xlsx",
        "./user_data.xlsx"
    ]
    
    excel_file = None
    for path in excel_paths:
        if Path(path).exists():
            excel_file = path
            break
    
    if not excel_file:
        await message.answer("❌ Файл user_data.xlsx не найден!")
        return
    
    await message.answer("🔄 Начинаю перезагрузку данных из Excel...")
    
    try:
        # Загружаем данные
        await load_users_from_excel(excel_file)
        await message.answer("✅ Данные успешно перезагружены из Excel файла!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при загрузке данных: {html_escape(str(e))}", parse_mode="HTML")


