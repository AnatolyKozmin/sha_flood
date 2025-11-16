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
echo "Проверяем наличие файла organizers.xlsx..."
ls -la /app/ | grep -i excel || echo "Список файлов в /app:"
ls -la /app/ | head -20

if [ -f "/app/organizers.xlsx" ]; then
  echo "✅ Обнаружен файл organizers.xlsx, загружаем данные..."
  python utils.py load /app/organizers.xlsx
else
  echo "⚠️  Файл /app/organizers.xlsx не найден"
  echo "Проверяем альтернативные пути..."
  if [ -f "organizers.xlsx" ]; then
    echo "✅ Найден файл organizers.xlsx в текущей директории"
    python utils.py load organizers.xlsx
  else
    echo "❌ Файл organizers.xlsx не найден ни в /app/, ни в текущей директории"
  fi
fi

echo "Запуск бота..."
exec python main.py