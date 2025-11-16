#!/bin/sh
set -e

# Ждём, пока база будет доступна
echo "Ожидание запуска PostgreSQL..."
until pg_isready -h db -p 5432 -U ${POSTGRES_USER:-vshu}; do
  sleep 2
done

echo "Применяем миграции..."
alembic upgrade head

# Загружаем данные из Excel, если файл существует
if [ -f "/app/organizers.xlsx" ]; then
  echo "Обнаружен файл organizers.xlsx, загружаем данные..."
  python utils.py load /app/organizers.xlsx
else
  echo "⚠️  Файл organizers.xlsx не найден, пропускаем загрузку данных"
fi

echo "Запуск бота..."
exec python main.py