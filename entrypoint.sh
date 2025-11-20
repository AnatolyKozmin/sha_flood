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
echo "Проверяем наличие файла user_data.xlsx..."
ls -la /app/ | grep -i excel || echo "Список файлов в /app:"
ls -la /app/ | head -20

if [ -f "/app/user_data.xlsx" ]; then
  echo "✅ Обнаружен файл user_data.xlsx, загружаем данные..."
  python utils.py load /app/user_data.xlsx
else
  echo "⚠️  Файл /app/user_data.xlsx не найден"
  echo "Проверяем альтернативные пути..."
  if [ -f "user_data.xlsx" ]; then
    echo "✅ Найден файл user_data.xlsx в текущей директории"
    python utils.py load user_data.xlsx
  else
    echo "❌ Файл user_data.xlsx не найден ни в /app/, ни в текущей директории"
  fi
fi

echo "Запуск бота..."
exec python main.py