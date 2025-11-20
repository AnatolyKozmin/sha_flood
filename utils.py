import asyncio
from pathlib import Path
from datetime import datetime
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
        # Начинаем с первой строки
        is_first_row = True
        for row_idx, row in enumerate(ws.iter_rows(min_row=1, values_only=True), start=1):
            # Пропускаем пустые строки
            if not row or not any(row):
                continue
            
            # Безопасное получение значения по индексу
            def get_value(idx, default=None, as_string=True):
                if idx < len(row) and row[idx] is not None:
                    val = row[idx]
                    if as_string:
                        return str(val).strip() if str(val).strip() else default
                    return val
                return default
            
            # Проверяем, является ли первая строка заголовками
            if is_first_row:
                first_row_values = [str(val).lower().strip() if val else "" for val in row[:5]]
                # Если первая строка содержит типичные заголовки, пропускаем её
                header_keywords = ['фио', 'подразделение', 'юзернейм', 'дата', 'фамилия', 'имя', 'отчество']
                if any(keyword in ' '.join(first_row_values) for keyword in header_keywords):
                    print(f"📋 Строка {row_idx}: пропущена (заголовки)")
                    is_first_row = False
                    skipped += 1
                    continue
                is_first_row = False
            
            # Извлекаем данные
            full_name = get_value(0)
            department = get_value(1)
            
            # Проверяем обязательные поля
            if not full_name or not department:
                print(f"⚠️  Строка {row_idx}: пропущена (отсутствуют ФИО или подразделение)")
                skipped += 1
                continue
            
            # Извлекаем необязательные поля
            telegram_username = get_value(2)
            if telegram_username and telegram_username.startswith('@'):
                telegram_username = telegram_username[1:]  # Убираем @
            
            # Обработка даты рождения (получаем сырое значение без преобразования в строку)
            birth_date = None
            birth_date_val = get_value(3, as_string=False)
            if birth_date_val is not None:
                # Если это datetime объект (openpyxl может вернуть datetime)
                if isinstance(birth_date_val, datetime):
                    birth_date = birth_date_val.strftime('%d.%m.%Y')
                elif isinstance(birth_date_val, str):
                    # Если это строка, проверяем формат
                    birth_date_val = birth_date_val.strip()
                    if not birth_date_val:
                        birth_date = None
                    elif len(birth_date_val) <= 10 and '.' in birth_date_val:
                        # Уже в формате DD.MM.YYYY
                        birth_date = birth_date_val[:10]
                    else:
                        # Пробуем распарсить разные форматы
                        try:
                            # Формат '2004-05-26 00:00:00' или '2004-05-26'
                            date_part = birth_date_val.split()[0] if ' ' in birth_date_val else birth_date_val
                            dt = datetime.strptime(date_part, '%Y-%m-%d')
                            birth_date = dt.strftime('%d.%m.%Y')
                        except ValueError:
                            # Если не получилось, обрезаем до 10 символов
                            birth_date = birth_date_val[:10] if len(birth_date_val) > 10 else birth_date_val
            faculty = get_value(4)
            
            # Курс обучения
            course = None
            course_val = get_value(5)
            if course_val:
                try:
                    course = int(course_val)
                except (ValueError, TypeError):
                    pass
            
            study_group = get_value(6)
            phone_number = get_value(7)
            has_car = get_value(8)
            nearest_metro = get_value(9)
            address = get_value(10)
            
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

