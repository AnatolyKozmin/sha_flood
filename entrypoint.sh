#!/bin/sh
set -e

# Ждём, пока база будет доступна
echo "Ожидание запуска PostgreSQL..."
until pg_isready -h db -p 5432 -U vshu; do
  sleep 2
done

echo "Применяем миграции..."
alembic upgrade head

# Загружаем данные из Excel, если файл существует
if [ -f "organizers.xlsx" ]; then
  echo "Обнаружен файл organizers.xlsx, загружаем данные..."
  python utils.py load organizers.xlsx
else
  echo "⚠️  Файл organizers.xlsx не найден, пропускаем загрузку данных"
fi

echo "Запуск бота..."
exec python main.py