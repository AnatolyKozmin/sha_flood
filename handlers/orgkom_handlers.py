from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Chat
from database.engine import AsyncSessionLocal

router = Router()


async def is_orgkom_chat(chat_id: int) -> bool:
    """Проверяет, является ли чат чатом организаторов"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Chat).where(
                Chat.chat_id == chat_id,
                Chat.chat_type == 'organizers'
            )
        )
        chat = result.scalar_one_or_none()
        return chat is not None


@router.message(Command("фамилия"))
@router.message(F.text.regexp(r'^!фамилия(?:\s+(.+))?', flags=0))
async def search_by_surname(message: Message):
    """
    Обработчик команды !фамилия для поиска организаторов по фамилии
    Использование: !фамилия Иванов
    """
    # Проверяем, что это чат организаторов
    if message.chat.type == 'private':
        await message.answer("❌ Эта команда доступна только в групповых чатах организаторов!")
        return
    
    if not await is_orgkom_chat(message.chat.id):
        return  # Игнорируем команду в чатах не-организаторов
    
    # Извлекаем фамилию из команды
    text = message.text or ""
    
    # Убираем команду и получаем фамилию
    if text.startswith('/фамилия'):
        surname = text.replace('/фамилия', '').strip()
    elif text.startswith('!фамилия'):
        surname = text.replace('!фамилия', '').strip()
    else:
        surname = ""
    
    if not surname:
        await message.answer(
            "❓ Укажите фамилию для поиска!\n\n"
            "Использование: <code>!фамилия Иванов</code>",
            parse_mode="HTML"
        )
        return
    
    # Поиск в базе данных
    async with AsyncSessionLocal() as session:
        # Ищем по началу ФИО (регистронезависимо)
        result = await session.execute(
            select(User).where(
                User.full_name.ilike(f'%{surname}%')
            )
        )
        users = result.scalars().all()
    
    if not users:
        await message.answer(
            f"❌ Организаторов с фамилией <b>{surname}</b> не найдено.",
            parse_mode="HTML"
        )
        return
    
    # Формируем ответ
    if len(users) == 1:
        user = users[0]
        response = format_user_info(user)
        await message.answer(response, parse_mode="HTML")
    else:
        # Если найдено несколько человек
        response = f"🔍 Найдено организаторов: <b>{len(users)}</b>\n\n"
        for i, user in enumerate(users, 1):
            response += f"{i}. <b>{user.full_name}</b> — {user.department}\n"
        
        response += "\n💡 Уточните запрос, если нужна детальная информация о конкретном человеке."
        await message.answer(response, parse_mode="HTML")


def format_user_info(user: User) -> str:
    """Форматирует информацию о пользователе для вывода"""
    info = f"👤 <b>{user.full_name}</b>\n\n"
    info += f"🏢 <b>Подразделение:</b> {user.department}\n"
    
    if user.telegram_username:
        info += f"📱 <b>Telegram:</b> @{user.telegram_username}\n"
    
    if user.phone_number:
        info += f"📞 <b>Телефон:</b> {user.phone_number}\n"
    
    if user.birth_date:
        info += f"🎂 <b>Дата рождения:</b> {user.birth_date}\n"
    
    if user.faculty:
        info += f"🎓 <b>Факультет:</b> {user.faculty}\n"
    
    if user.course:
        info += f"📚 <b>Курс:</b> {user.course}\n"
    
    if user.study_group:
        info += f"👥 <b>Группа:</b> {user.study_group}\n"
    
    if user.has_car:
        info += f"🚗 <b>Авто/права:</b> {user.has_car}\n"
    
    if user.nearest_metro:
        info += f"🚇 <b>Метро:</b> {user.nearest_metro}\n"
    
    if user.address:
        info += f"🏠 <b>Адрес:</b> {user.address}\n"
    
    return info

