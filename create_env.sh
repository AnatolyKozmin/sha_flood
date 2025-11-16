#!/bin/bash

# Скрипт для быстрого создания .env файла

echo "🔧 Создание файла .env для Docker"
echo ""

# Проверяем, существует ли уже .env
if [ -f ".env" ]; then
    read -p "⚠️  Файл .env уже существует. Перезаписать? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Отменено"
        exit 1
    fi
fi

# Запрашиваем токен бота
read -p "Введите токен бота от @BotFather: " BOT_TOKEN

# Создаем .env файл
cat > .env << EOF
# Токен бота
BOT_TOKEN=$BOT_TOKEN

# Настройки PostgreSQL (для Docker)
POSTGRES_DB=vshu_db
POSTGRES_USER=vshu
POSTGRES_PASSWORD=1234
POSTGRES_HOST=db
POSTGRES_PORT=5432

# ID администраторов (список через запятую)
ADMIN_IDS=[]
EOF

echo ""
echo "✅ Файл .env успешно создан!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Разместите файл organizers.xlsx в корне проекта"
echo "2. Запустите: docker-compose up -d --build"
echo "3. Проверьте логи: docker-compose logs -f bot"


