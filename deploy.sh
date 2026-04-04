#!/bin/bash

# Скрипт для деплоя приложения

set -e

echo "🚀 Деплой StudentHelperAgent..."

# Проверка .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте .env файл на основе .env.template"
    exit 1
fi

# Остановка старых контейнеров
echo "🛑 Остановка старых контейнеров..."
docker-compose -f docker-compose.prod.yml down

# Сборка образов
echo "🔨 Сборка образов..."
docker-compose -f docker-compose.prod.yml build --no-cache

# Запуск контейнеров
echo "▶️  Запуск контейнеров..."
docker-compose -f docker-compose.prod.yml up -d

# Проверка статуса
echo "✅ Проверка статуса..."
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "✅ Деплой завершён!"
echo "📊 Логи: docker-compose -f docker-compose.prod.yml logs -f"
echo "🔍 Статус: docker-compose -f docker-compose.prod.yml ps"
