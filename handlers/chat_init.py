from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import ChatMemberUpdatedFilter, MEMBER, ADMINISTRATOR
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Chat
from database.engine import AsyncSessionLocal

router = Router()


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER | ADMINISTRATOR))
async def bot_added_to_chat(event: ChatMemberUpdated):
    """
    Обработчик добавления бота в чат.
    Спрашивает тип чата: участники или организаторы.
    """
    # Проверяем, что бот был добавлен (а не удален)
    if event.new_chat_member.status in ['member', 'administrator']:
        # Проверяем, не зарегистрирован ли уже этот чат
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Chat).where(Chat.chat_id == event.chat.id)
            )
            existing_chat = result.scalar_one_or_none()
        
        if existing_chat:
            return  # Чат уже зарегистрирован
        
        # Создаем клавиатуру с выбором типа чата
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Участники",
                    callback_data=f"chat_type:participants:{event.chat.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎯 Организаторы",
                    callback_data=f"chat_type:organizers:{event.chat.id}"
                )
            ]
        ])
        
        await event.answer(
            "👋 Привет! Че за чат?\n\n"
            "Выберите тип чата, чтобы я знал, какие команды здесь доступны:",
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("chat_type:"))
async def process_chat_type_selection(callback: CallbackQuery):
    """
    Обработчик выбора типа чата.
    Сохраняет тип чата в базе данных.
    """
    # Парсим данные из callback_data
    _, chat_type, chat_id_str = callback.data.split(":")
    chat_id = int(chat_id_str)
    
    # Проверяем права пользователя (только администраторы могут выбирать тип)
    member = await callback.bot.get_chat_member(chat_id, callback.from_user.id)
    if member.status not in ['creator', 'administrator']:
        await callback.answer(
            "❌ Только администраторы чата могут выбирать тип!",
            show_alert=True
        )
        return
    
    # Сохраняем в базе данных
    async with AsyncSessionLocal() as session:
        # Проверяем, есть ли уже запись
        result = await session.execute(
            select(Chat).where(Chat.chat_id == chat_id)
        )
        existing_chat = result.scalar_one_or_none()
        
        if existing_chat:
            # Обновляем тип
            existing_chat.chat_type = chat_type
        else:
            # Создаем новую запись
            chat = await callback.bot.get_chat(chat_id)
            new_chat = Chat(
                chat_id=chat_id,
                chat_type=chat_type,
                chat_title=chat.title
            )
            session.add(new_chat)
        
        await session.commit()
    
    # Формируем сообщение в зависимости от типа
    if chat_type == 'organizers':
        response = (
            "✅ Чат настроен как <b>чат организаторов</b>!\n\n"
            "🎯 Доступные команды:\n"
            "• <code>!фамилия</code> - поиск организатора по фамилии\n\n"
            "Больше команд появится позже!"
        )
    else:
        response = (
            "✅ Чат настроен как <b>чат участников</b>!\n\n"
            "👥 Функционал для участников пока в разработке..."
        )
    
    await callback.message.edit_text(
        response,
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(Command("chat_info"))
async def show_chat_info(message: Message):
    """
    Показывает информацию о текущем чате.
    Доступно только администраторам.
    """
    if message.chat.type == 'private':
        await message.answer("❌ Эта команда доступна только в групповых чатах!")
        return
    
    # Проверяем права пользователя
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ['creator', 'administrator']:
        return
    
    # Получаем информацию о чате
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Chat).where(Chat.chat_id == message.chat.id)
        )
        chat = result.scalar_one_or_none()
    
    if not chat:
        await message.answer(
            "❓ Этот чат еще не настроен.\n"
            "Удалите и добавьте бота заново для настройки."
        )
        return
    
    chat_type_name = "Организаторы" if chat.chat_type == 'organizers' else "Участники"
    
    await message.answer(
        f"ℹ️ <b>Информация о чате</b>\n\n"
        f"🏷 <b>Название:</b> {chat.chat_title}\n"
        f"🎯 <b>Тип:</b> {chat_type_name}\n"
        f"📅 <b>Добавлен:</b> {chat.added_at.strftime('%d.%m.%Y %H:%M')}",
        parse_mode="HTML"
    )

