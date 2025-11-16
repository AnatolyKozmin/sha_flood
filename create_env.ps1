# Скрипт для быстрого создания .env файла (PowerShell)

Write-Host "🔧 Создание файла .env для Docker" -ForegroundColor Cyan
Write-Host ""

# Проверяем, существует ли уже .env
if (Test-Path ".env") {
    $response = Read-Host "⚠️  Файл .env уже существует. Перезаписать? (y/n)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "❌ Отменено" -ForegroundColor Red
        exit 1
    }
}

# Запрашиваем токен бота
$BOT_TOKEN = Read-Host "Введите токен бота от @BotFather"

# Создаем .env файл
$envContent = @"
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
"@

$envContent | Out-File -FilePath ".env" -Encoding UTF8 -NoNewline

Write-Host ""
Write-Host "✅ Файл .env успешно создан!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Следующие шаги:" -ForegroundColor Yellow
Write-Host "1. Разместите файл organizers.xlsx в корне проекта"
Write-Host "2. Запустите: docker-compose up -d --build"
Write-Host "3. Проверьте логи: docker-compose logs -f bot"


