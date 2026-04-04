# 🚀 Деплой на VPS

Инструкция по развертыванию StudentHelperAgent на VPS сервере с nginx и SSL.

## 📋 Требования

- VPS сервер (Ubuntu 20.04/22.04 или Debian)
- Доменное имя с настроенными DNS записями
- Docker и Docker Compose на сервере
- Минимум 2GB RAM, 20GB диска

## 🔧 Подготовка сервера

### 1. Подключитесь к VPS

```bash
ssh root@your-server-ip
```

### 2. Установите Docker

```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установка Docker Compose
apt install docker-compose -y

# Проверка
docker --version
docker-compose --version
```

### 3. Настройте DNS

Добавьте A-записи для вашего домена:

```
A    @              your-server-ip
A    www            your-server-ip
```

Проверьте DNS (может занять до 24 часов):

```bash
dig your-domain.com
```

## 📦 Деплой приложения

### 1. Клонируйте репозиторий

```bash
cd /opt
git clone https://github.com/Piankov-Michail/StudentHelperAgent.git
cd StudentHelperAgent
```

### 2. Настройте переменные окружения

```bash
# Скопируйте шаблон
cp .env.production .env

# Отредактируйте .env
nano .env
```

Измените следующие значения:

```env
# Database - используйте надёжные пароли!
POSTGRES_USER=student_helper
POSTGRES_PASSWORD=ваш_сложный_пароль_для_БД
POSTGRES_DB=student_helper
DATABASE_URL=postgresql+asyncpg://student_helper:ваш_сложный_пароль_для_БД@postgres:5432/student_helper

# Security - сгенерируйте случайные строки!
JWT_SECRET=случайная_строка_минимум_32_символа
ENCRYPTION_KEY=случайная_строка_ровно_32_символа

# Domain
DOMAIN=your-domain.com
EMAIL=your-email@example.com
```

Для генерации случайных ключей:

```bash
# JWT_SECRET (32+ символов)
openssl rand -base64 32

# ENCRYPTION_KEY (ровно 32 символа)
openssl rand -base64 24
```

### 3. Настройте домен в конфигурации

Отредактируйте `nginx/conf.d/app.conf`:

```bash
nano nginx/conf.d/app.conf
```

Замените `your-domain.com` на ваш реальный домен во всех местах.

### 4. Получите SSL сертификат

```bash
# Сделайте скрипт исполняемым
chmod +x init-ssl.sh

# Отредактируйте домен и email в скрипте
nano init-ssl.sh

# Запустите скрипт
./init-ssl.sh
```

Скрипт:
1. Запустит nginx в HTTP режиме
2. Получит SSL сертификат от Let's Encrypt
3. Переключит nginx на HTTPS
4. Настроит автоматическое обновление сертификата

### 5. Запустите приложение

```bash
# Сделайте скрипт исполняемым
chmod +x deploy.sh

# Запустите деплой
./deploy.sh
```

### 6. Проверьте работу

```bash
# Проверка статуса контейнеров
docker-compose -f docker-compose.prod.yml ps

# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f

# Проверка nginx
docker-compose -f docker-compose.prod.yml logs nginx

# Проверка приложения
docker-compose -f docker-compose.prod.yml logs app
```

Откройте в браузере: `https://your-domain.com`

## 🔄 Обновление приложения

```bash
cd /opt/StudentHelperAgent

# Получите последние изменения
git pull

# Запустите деплой
./deploy.sh
```

## 🛠️ Полезные команды

### Управление контейнерами

```bash
# Остановить все
docker-compose -f docker-compose.prod.yml down

# Запустить все
docker-compose -f docker-compose.prod.yml up -d

# Перезапустить конкретный сервис
docker-compose -f docker-compose.prod.yml restart app
docker-compose -f docker-compose.prod.yml restart nginx

# Пересобрать образы
docker-compose -f docker-compose.prod.yml build --no-cache
```

### Логи

```bash
# Все логи
docker-compose -f docker-compose.prod.yml logs -f

# Логи конкретного сервиса
docker-compose -f docker-compose.prod.yml logs -f app
docker-compose -f docker-compose.prod.yml logs -f nginx
docker-compose -f docker-compose.prod.yml logs -f postgres

# Последние 100 строк
docker-compose -f docker-compose.prod.yml logs --tail=100 app
```

### База данных

```bash
# Подключиться к PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres psql -U student_helper -d student_helper

# Бэкап БД
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U student_helper student_helper > backup.sql

# Восстановление БД
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U student_helper student_helper < backup.sql
```

### SSL сертификаты

```bash
# Проверка срока действия
docker-compose -f docker-compose.prod.yml exec certbot certbot certificates

# Ручное обновление
docker-compose -f docker-compose.prod.yml exec certbot certbot renew

# Перезапуск nginx после обновления
docker-compose -f docker-compose.prod.yml restart nginx
```

## 🔒 Безопасность

### Firewall

```bash
# Установка UFW
apt install ufw -y

# Разрешить SSH
ufw allow 22/tcp

# Разрешить HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Включить firewall
ufw enable

# Проверить статус
ufw status
```

### Автоматические обновления

```bash
# Установка unattended-upgrades
apt install unattended-upgrades -y

# Настройка
dpkg-reconfigure -plow unattended-upgrades
```

### Мониторинг

```bash
# Использование ресурсов
docker stats

# Место на диске
df -h

# Очистка неиспользуемых образов
docker system prune -a
```

## 🐛 Устранение проблем

### Приложение не запускается

```bash
# Проверьте логи
docker-compose -f docker-compose.prod.yml logs app

# Проверьте переменные окружения
docker-compose -f docker-compose.prod.yml exec app env

# Пересоздайте контейнеры
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --force-recreate
```

### Nginx возвращает 502

```bash
# Проверьте, что app запущен
docker-compose -f docker-compose.prod.yml ps app

# Проверьте логи nginx
docker-compose -f docker-compose.prod.yml logs nginx

# Перезапустите nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

### SSL сертификат не работает

```bash
# Проверьте сертификаты
docker-compose -f docker-compose.prod.yml exec certbot certbot certificates

# Проверьте конфигурацию nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# Убедитесь, что домен указывает на сервер
dig your-domain.com
```

### База данных не подключается

```bash
# Проверьте статус PostgreSQL
docker-compose -f docker-compose.prod.yml ps postgres

# Проверьте логи
docker-compose -f docker-compose.prod.yml logs postgres

# Проверьте подключение
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U student_helper
```

## 📊 Мониторинг и логи

### Настройка ротации логов

Создайте `/etc/logrotate.d/docker-containers`:

```
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=10M
    missingok
    delaycompress
    copytruncate
}
```

### Мониторинг с помощью ctop

```bash
# Установка ctop
wget https://github.com/bcicen/ctop/releases/download/v0.7.7/ctop-0.7.7-linux-amd64 -O /usr/local/bin/ctop
chmod +x /usr/local/bin/ctop

# Запуск
ctop
```

## 🌐 Использование CloudFlare (опционально)

Если хотите использовать CloudFlare:

1. Добавьте домен в CloudFlare
2. Измените NS записи у регистратора на CloudFlare NS
3. В CloudFlare настройте:
   - SSL/TLS: Full (strict)
   - Always Use HTTPS: On
   - Automatic HTTPS Rewrites: On
4. Добавьте A-запись: `@` → `your-server-ip` (Proxy: On)
5. Добавьте A-запись: `www` → `your-server-ip` (Proxy: On)

CloudFlare будет работать как дополнительный прокси с DDoS защитой и кэшированием.

## 📝 Бэкапы

### Автоматический бэкап

Создайте скрипт `/opt/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Бэкап БД
docker-compose -f /opt/StudentHelperAgent/docker-compose.prod.yml exec -T postgres \
    pg_dump -U student_helper student_helper > $BACKUP_DIR/db_$DATE.sql

# Бэкап файлов
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /opt/StudentHelperAgent/uploads

# Удаление старых бэкапов (старше 7 дней)
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

Добавьте в crontab:

```bash
chmod +x /opt/backup.sh
crontab -e

# Добавьте строку (бэкап каждый день в 3:00)
0 3 * * * /opt/backup.sh >> /var/log/backup.log 2>&1
```

## 🎉 Готово!

Ваше приложение теперь доступно по адресу `https://your-domain.com` с автоматическим SSL сертификатом и защищённым соединением.
