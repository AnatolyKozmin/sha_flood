import asyncio
from pathlib import Path
import openpyxl
from sqlalchemy import select

from database.models import User
from database.engine import AsyncSessionLocal


async def load_users_from_excel(excel_path: str):
    """
    Загружает данных организаторов из Excel файла в базу данных
    
    Ожидаемые колонки (в порядке):
    0. ФИО (полностью, как в паспорте, не капсом)
    1. Подразделение
    2. Телеграмм юзернейм
    3. Дата рождения (формат: 18.06.2004)
    4. Факультет
    5. Курс обучения
    6. Учебная группа (формат: ШАЦ25-1)
    7. Номер телефона (формат: 8 (999) 123-45-67)
    8. Есть ли у тебя водительские права и машина?
    9. Напиши ближайшую(-ие) к тебе станции метро
    10. Адрес проживания
    """
    if not Path(excel_path).exists():
        print(f"❌ Файл {excel_path} не найден!")
        return
    
    print(f"📂 Загружаю данные из {excel_path}...")
    
    # Загружаем Excel файл
    wb = openpyxl.load_workbook(excel_path)
    ws = wb.active
    
    added = 0
    updated = 0
    skipped = 0
    
    async with AsyncSessionLocal() as session:
        # Начинаем со второй строки (первая - заголовки)
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            # Пропускаем пустые строки
            if not row or not any(row):
                continue
            
            # Извлекаем данные
            full_name = str(row[0]).strip() if row[0] else None
            department = str(row[1]).strip() if row[1] else None
            
            # Проверяем обязательные поля
            if not full_name or not department:
                print(f"⚠️  Строка {row_idx}: пропущена (отсутствуют ФИО или подразделение)")
                skipped += 1
                continue
            
            # Извлекаем необязательные поля
            telegram_username = str(row[2]).strip() if row[2] and str(row[2]).strip() else None
            if telegram_username and telegram_username.startswith('@'):
                telegram_username = telegram_username[1:]  # Убираем @
            
            birth_date = str(row[3]).strip() if row[3] and str(row[3]).strip() else None
            faculty = str(row[4]).strip() if row[4] and str(row[4]).strip() else None
            
            # Курс обучения
            course = None
            if row[5]:
                try:
                    course = int(row[5])
                except (ValueError, TypeError):
                    pass
            
            study_group = str(row[6]).strip() if row[6] and str(row[6]).strip() else None
            phone_number = str(row[7]).strip() if row[7] and str(row[7]).strip() else None
            has_car = str(row[8]).strip() if row[8] and str(row[8]).strip() else None
            nearest_metro = str(row[9]).strip() if row[9] and str(row[9]).strip() else None
            address = str(row[10]).strip() if row[10] and str(row[10]).strip() else None
            
            # Проверяем, существует ли уже пользователь с таким ФИО
            result = await session.execute(
                select(User).where(User.full_name == full_name)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                # Обновляем существующего пользователя
                existing_user.department = department
                existing_user.telegram_username = telegram_username
                existing_user.birth_date = birth_date
                existing_user.faculty = faculty
                existing_user.course = course
                existing_user.study_group = study_group
                existing_user.phone_number = phone_number
                existing_user.has_car = has_car
                existing_user.nearest_metro = nearest_metro
                existing_user.address = address
                updated += 1
                print(f"♻️  Обновлен: {full_name}")
            else:
                # Создаем нового пользователя
                user = User(
                    full_name=full_name,
                    department=department,
                    telegram_username=telegram_username,
                    birth_date=birth_date,
                    faculty=faculty,
                    course=course,
                    study_group=study_group,
                    phone_number=phone_number,
                    has_car=has_car,
                    nearest_metro=nearest_metro,
                    address=address
                )
                session.add(user)
                added += 1
                print(f"✅ Добавлен: {full_name}")
        
        # Сохраняем изменения
        await session.commit()
    
    print("\n" + "="*50)
    print(f"✅ Добавлено новых: {added}")
    print(f"♻️  Обновлено: {updated}")
    print(f"⚠️  Пропущено: {skipped}")
    print(f"📊 Итого обработано: {added + updated + skipped}")
    print("="*50)


async def clear_users_table():
    """Очищает таблицу пользователей (ВНИМАНИЕ: удаляет все данные!)"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        for user in users:
            await session.delete(user)
        
        await session.commit()
        print(f"🗑️  Удалено пользователей: {len(users)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python utils.py load <путь_к_excel_файлу>  - загрузить данные из Excel")
        print("  python utils.py clear                      - очистить таблицу пользователей")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "load":
        if len(sys.argv) < 3:
            print("❌ Укажите путь к Excel файлу!")
            sys.exit(1)
        
        excel_file = sys.argv[2]
        asyncio.run(load_users_from_excel(excel_file))
    
    elif command == "clear":
        confirm = input("⚠️  Вы уверены, что хотите удалить всех пользователей? (yes/no): ")
        if confirm.lower() == "yes":
            asyncio.run(clear_users_table())
        else:
            print("❌ Отменено")
    
    else:
        print(f"❌ Неизвестная команда: {command}")
        sys.exit(1)

