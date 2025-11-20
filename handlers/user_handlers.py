from aiogram import Router, F
from aiogram.types import Message, ChatPermissions
from aiogram.filters import Command
from aiogram.utils.markdown import hbold
from sqlalchemy import select, update, or_, and_
from datetime import datetime, timedelta
import random
from io import BytesIO

from database.engine import AsyncSessionLocal
from database.models import User, Quote, BeerStat, Wakeup, MathDuel
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
        "• !пиво (в ответ) — +1 пива пользователю\n"
        "• !статистика пива — рейтинг по пиву\n"
        "• !адрес [фамилия] — адрес организатора\n"
        "• !перепарсить — перезагрузить данные из Excel (только для админов)\n"
        "• !кто [текст] — случайный человек и упоминание\n"
        "• !дуель (в ответ) — рандомный мут на 10 мин\n"
        "• !матдуэль (в ответ) — математическая дуэль\n"
        "• !анмут — размутить всех в муте\n"
        "• !вокабулар — словарь сленга\n"
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
    
    # Формируем сообщение с тегом
    user_name = html_escape(u.full_name)
    if u.telegram_username:
        mention = f"@{u.telegram_username}"
        response = f"🏆 Организатор дня: <b>{user_name}</b> ({html_escape(u.department)}) 🎉\n\n{mention}"
    else:
        # Если нет username, просто имя
        response = f"🏆 Организатор дня: <b>{user_name}</b> ({html_escape(u.department)}) 🎉"
    
    await message.answer(response, parse_mode="HTML")


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


@router.message(F.text.regexp(r"^!пиво\b", flags=0))
async def cmd_beer_pour(message: Message):
    # Проверяем, есть ли у пользователя "ТП" в поле department
    user_id = message.from_user.id
    username = (message.from_user.username or "").lower().strip()
    user_full_name = message.from_user.full_name or ""
    
    async with AsyncSessionLocal() as session:
        # Ищем пользователя по telegram_id, telegram_username или по имени
        conditions = [User.telegram_id == user_id]
        
        if username:
            conditions.append(User.telegram_username.ilike(f"%{username}%"))
        
        if user_full_name:
            conditions.append(User.full_name.ilike(f"%{user_full_name}%"))
        
        result = await session.execute(
            select(User).where(or_(*conditions))
        )
        user = result.scalar_one_or_none()
        
        # Если не нашли по точному совпадению, пробуем найти по части имени
        if not user and user_full_name:
            # Берем первую часть имени (фамилию)
            name_parts = user_full_name.split()
            if name_parts:
                first_name_part = name_parts[0]
                result = await session.execute(
                    select(User).where(User.full_name.ilike(f"%{first_name_part}%"))
                )
                users = result.scalars().all()
                # Если нашли одного - используем его
                if len(users) == 1:
                    user = users[0]
        
        # Проверяем, есть ли "ТП" в department
        has_tp = False
        if user and user.department:
            has_tp = "ТП" in user.department.upper()
        
        # Если пользователь не найден в базе или не является ТП - запрещаем
        if not has_tp:
            await message.answer("Пиво только для тп, остальным компотик 😘😜😁😆🖤")
            return
    
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
    
    # Формируем сообщение в формате: {текст} - {человек} (без тега)
    response = f"{text} - {user_name}"
    
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


@router.message(F.reply_to_message & F.text.regexp(r"^!дуель\b", flags=0))
async def cmd_duel(message: Message):
    """Дуэль: рандомно мьютит одного из двух участников на 10 минут"""
    if message.chat.type == 'private':
        await message.answer("❌ Эта команда доступна только в групповых чатах!")
        return
    
    challenger = message.from_user
    target = message.reply_to_message.from_user
    
    if challenger.id == target.id:
        await message.answer("❌ Нельзя вызвать на дуэль самого себя!")
        return
    
    # Рандомно выбираем, кого мьютить
    loser = random.choice([challenger, target])
    winner = target if loser.id == challenger.id else challenger
    
    until = datetime.utcnow() + timedelta(minutes=10)
    try:
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=loser.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until
        )
        await message.answer(
            f"⚔️ Дуэль! {loser.mention_html()} проиграл и замьючен на 10 минут. "
            f"{winner.mention_html()} победил! 🎉",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Не удалось выдать мут (нет прав у бота?). Ошибка: {str(e)}")


@router.message(F.reply_to_message & F.text.regexp(r"^!матдуэль\b", flags=0))
async def cmd_math_duel(message: Message):
    """Математическая дуэль: кто первый правильно ответит, тот выиграл"""
    if message.chat.type == 'private':
        await message.answer("❌ Эта команда доступна только в групповых чатах!")
        return
    
    challenger = message.from_user
    target = message.reply_to_message.from_user
    
    if challenger.id == target.id:
        await message.answer("❌ Нельзя вызвать на дуэль самого себя!")
        return
    
    # Генерируем два трехзначных числа
    num1 = random.randint(100, 999)
    num2 = random.randint(100, 999)
    correct_answer = num1 + num2
    
    async with AsyncSessionLocal() as session:
        # Проверяем, нет ли уже активной дуэли между этими пользователями
        result = await session.execute(
            select(MathDuel).where(
                MathDuel.chat_id == message.chat.id,
                MathDuel.expired == False,
                or_(
                    and_(MathDuel.user1_id == challenger.id, MathDuel.user2_id == target.id),
                    and_(MathDuel.user1_id == target.id, MathDuel.user2_id == challenger.id)
                )
            )
        )
        existing_duel = result.scalar_one_or_none()
        
        if existing_duel:
            await message.answer("❌ У вас уже есть активная дуэль! Сначала завершите её.")
            return
        
        # Создаем новую дуэль
        duel = MathDuel(
            chat_id=message.chat.id,
            user1_id=challenger.id,
            user2_id=target.id,
            num1=num1,
            num2=num2,
            correct_answer=correct_answer
        )
        session.add(duel)
        await session.commit()
    
    await message.answer(
        f"🧮 Математическая дуэль!\n\n"
        f"{challenger.mention_html()} vs {target.mention_html()}\n\n"
        f"Сколько будет: <b>{num1} + {num2}</b>?\n\n"
        f"Кто первый напишет правильный ответ - выиграл! Проигравший в мут на 10 минут!",
        parse_mode="HTML"
    )


@router.message(F.text.regexp(r"^!анмут\b", flags=0))
async def cmd_unmute_all(message: Message):
    """Размучивает всех пользователей в чате"""
    if message.chat.type == 'private':
        await message.answer("❌ Эта команда доступна только в групповых чатах!")
        return
    
    # Проверяем права администратора
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ['creator', 'administrator']:
        await message.answer("❌ Только администраторы могут размучивать всех!")
        return
    
    try:
        # Получаем список администраторов для получения полных прав
        full_permissions = ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True
        )
        
        unmuted_count = 0
        # Пробуем размутить известных пользователей из базы данных (из статистики пива и цитат)
        async with AsyncSessionLocal() as session:
            # Получаем всех уникальных user_id из различных таблиц
            from sqlalchemy import distinct
            result = await session.execute(
                select(distinct(BeerStat.user_id)).where(BeerStat.chat_id == message.chat.id)
            )
            user_ids = [row[0] for row in result.all()]
            
            result = await session.execute(
                select(distinct(Quote.author_user_id)).where(Quote.chat_id == message.chat.id)
            )
            quote_user_ids = [row[0] for row in result.all()]
            user_ids.extend(quote_user_ids)
            
            # Убираем дубликаты
            user_ids = list(set(user_ids))
        
        # Пробуем размутить каждого пользователя
        for user_id in user_ids:
            try:
                member = await message.bot.get_chat_member(message.chat.id, user_id)
                if member.status == 'restricted' and not member.can_send_messages:
                    await message.bot.restrict_chat_member(
                        chat_id=message.chat.id,
                        user_id=user_id,
                        permissions=full_permissions
                    )
                    unmuted_count += 1
            except Exception:
                pass
        
        if unmuted_count > 0:
            await message.answer(f"✅ Размучено пользователей: {unmuted_count}")
        else:
            await message.answer("ℹ️ Нет замученных пользователей в этом чате (или они не найдены в базе).")
    except Exception as e:
        await message.answer(f"❌ Ошибка при размуте: {html_escape(str(e))}", parse_mode="HTML")


# Обработчик ответов на математическую дуэль
@router.message(F.text.regexp(r"^\d+$", flags=0))
async def handle_math_duel_answer(message: Message):
    """Обрабатывает ответы на математическую дуэль"""
    if message.chat.type == 'private':
        return
    
    try:
        answer = int(message.text.strip())
    except ValueError:
        return
    
    user_id = message.from_user.id
    
    async with AsyncSessionLocal() as session:
        # Ищем активную дуэль с участием этого пользователя
        result = await session.execute(
            select(MathDuel).where(
                MathDuel.chat_id == message.chat.id,
                MathDuel.expired == False,
                or_(
                    MathDuel.user1_id == user_id,
                    MathDuel.user2_id == user_id
                )
            )
        )
        duel = result.scalar_one_or_none()
        
        if not duel:
            return
        
        # Проверяем правильность ответа
        if answer == duel.correct_answer:
            # Правильный ответ - этот пользователь выиграл
            winner = message.from_user
            loser_id = duel.user2_id if duel.user1_id == winner.id else duel.user1_id
            
            # Получаем информацию о проигравшем
            try:
                loser_member = await message.bot.get_chat_member(message.chat.id, loser_id)
                loser_name = loser_member.user.full_name
            except Exception:
                loser_name = f"id:{loser_id}"
            
            # Мьютим проигравшего
            until = datetime.utcnow() + timedelta(minutes=10)
            try:
                await message.bot.restrict_chat_member(
                    chat_id=message.chat.id,
                    user_id=loser_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until
                )
            except Exception:
                pass
            
            # Помечаем дуэль как завершенную
            duel.winner_id = winner.id
            duel.expired = True
            await session.commit()
            
            await message.answer(
                f"🎉 {winner.mention_html()} выиграл математическую дуэль!\n\n"
                f"Правильный ответ: <b>{duel.correct_answer}</b>\n"
                f"Проигравший {loser_name} замьючен на 10 минут!",
                parse_mode="HTML"
            )
        # Если ответ неправильный, просто игнорируем (не сообщаем об ошибке, чтобы не спамить)


@router.message(F.text.regexp(r"^!вокабулар\b", flags=0))
async def cmd_vocabulary(message: Message):
    """Отправляет словарь сленговых слов"""
    vocab_text = """📚 <b>ВОКАБУЛЯР</b>

<b>Общие слова</b>

1. <b>Кринж/кринге</b> — неловкая, стремная или позорная ситуация.

2. <b>Дратути</b> — шуточное приветствие, искажённое «Здравствуйте».

3. <b>Муд</b> — настроение, состояние.

4. <b>База</b> — полное согласие, одобрение чего-то правильного.

5. <b>Имба</b> — что-то слишком крутое или сильное.

6. <b>Сигма</b> — человек, который живёт по своим правилам.

7. <b>Лол</b> — реакция на смешное или абсурдное.

8. <b>Мимимишный</b> — чрезмерно милый, вызывающий умиление.

9. <b>Токсик</b> — человек с негативным, разрушительным поведением.

10. <b>Хайп</b> — ажиотаж, популярность вокруг чего-то.

11. <b>Се се</b> — сокращённое «все-все», завершение темы.

12. <b>Триггерить</b> — вызывать сильную эмоциональную реакцию.

13. <b>Нямнямки</b> — вкусности, перекус, еда.

14. <b>Вайб</b> — настроение, атмосфера чего-либо.

15. <b>Редфлаг</b> — тревожный знак, сигнал, что в человеке или ситуации что-то не то.

16. <b>Гринфлаг</b> — положительный знак, свидетельство того, что с человеком или ситуацией всё хорошо.

17. <b>Ауф</b> — одобрение, восхищение, синоним «вау».

18. <b>Рофл</b> — шутка, прикол, нечто абсурдное; часто используется как «Это что, рофл?».

19. <b>Залип / залипать</b> — полностью погрузиться во что-то (видео, переписку, музыку).

20. <b>Испанский стыд</b> — чувство неловкости за чужие поступки.

21. <b>Трэш</b> — что-то крайне абсурдное, шокирующее или бессмысленное.

<b>Рабочие слова</b>

1. <b>Апрувнуть</b> — одобрить, согласовать.

2. <b>Фидбэк</b> — обратная связь.

3. <b>Апдейт</b> — обновление информации.

4. <b>Созвон / Колл</b> — онлайн-встреча.

5. <b>Онбординг</b> — адаптация нового сотрудника.

6. <b>Фомо</b> — Fear of Missing Out, страх упустить что-то интересное.

7. <b>Оффтоп</b> — сообщение не по теме.

8. <b>Чекнуть</b> — проверить."""
    
    await message.answer(vocab_text, parse_mode="HTML")


