# 🎓 StudentHelperAgent

AI-powered веб-приложение для автоматической транскрибации видео и аудио лекций с созданием структурированных конспектов.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)

---

## 🌟 Возможности

- 🎬 **Автоматическая транскрибация** видео и аудио лекций с помощью Whisper
- 📝 **Создание конспектов** с выделением ключевых тем и важных моментов
- 💬 **AI-чат помощник** для ответов на вопросы по материалам
- 🗂️ **Управление чатами** с историей сообщений
- 🔄 **Retry/Delete** для сообщений - возможность повторить запрос или удалить сообщения
- 📋 **Экспорт** чатов в текстовый формат
- 🔐 **Безопасное хранение** API токенов
- 🎨 **Современный UI** в стиле Google AI Studio

---

## 🚀 Быстрый старт

### Требования

- Docker и Docker Compose
- Аккаунт на [Hugging Face](https://huggingface.co) (для получения токена)

### Установка

1. **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/Piankov-Michail/StudentHelperAgent.git
   cd StudentHelperAgent
   ```

2. **Создайте файл `.env`:**
   ```bash
   cp .env.template .env
   ```

3. **Отредактируйте `.env` файл:**
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/student_helper
   JWT_SECRET=your-secret-key-here
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   ```

4. **Запустите контейнеры:**
   ```bash
   docker-compose up -d
   ```

5. **Откройте приложение:**
   - Перейдите на [http://localhost:8000](http://localhost:8000)

---

## ⚙️ Настройка

### Получение API токенов

#### 1. Hugging Face Token (обязательно)

1. Зарегистрируйтесь на [Hugging Face](https://huggingface.co)
2. Перейдите в [настройки токенов](https://huggingface.co/settings/tokens)
3. Создайте новый токен с правами **"Read"**
4. Скопируйте токен (формат: `hf_xxxxx...`)

#### 2. Ollama API Key (опционально)

1. Зарегистрируйтесь на [Ollama](https://ollama.com)
2. Перейдите в [настройки API ключей](https://ollama.com/settings/keys)
3. Создайте новый API ключ
4. Скопируйте ключ (формат: `ollama_xxxxx...`)

### Добавление токенов в приложение

1. Откройте приложение в браузере
2. Зарегистрируйтесь или войдите
3. Нажмите на **значок шестерёнки** (⚙️) в боковой панели
4. Вставьте токены:
   - **🤗 Hugging Face Token** - для транскрибации
   - **🦙 Ollama API Key** - для облачных моделей (опционально)
5. Нажмите **"Сохранить"**

📖 **Подробная инструкция:** См. [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

## 📖 Использование

### Транскрибация видео/аудио

1. Выберите режим **"🎬 Транскрибация видео"**
2. Прикрепите файл (📎)
3. Добавьте комментарий (опционально)
4. Нажмите отправить (↑)
5. Получите конспект с ключевыми темами

### Чат-помощник

1. Выберите режим **"💬 Чат-помощник"**
2. Задайте вопрос
3. Получите ответ от AI

### Управление сообщениями

При наведении на сообщение появляются кнопки:
- 📋 **Копировать** - скопировать текст
- 🔄 **Повторить** - повторить запрос (только для пользовательских сообщений)
- 🗑️ **Удалить** - удалить сообщение и все последующие (только для пользовательских сообщений)

---

## 🛠️ Технологии

### Backend
- **FastAPI** - веб-фреймворк
- **PostgreSQL** - база данных
- **SQLAlchemy** - ORM
- **LangChain** - работа с LLM
- **Faster-Whisper** - транскрибация аудио

### Frontend
- **Vanilla JavaScript** - без фреймворков
- **Tailwind CSS** - стилизация
- **Marked.js** - рендеринг Markdown
- **Highlight.js** - подсветка кода

### AI/ML
- **Whisper** (Hugging Face) - распознавание речи
- **Ollama** - локальные LLM модели
- **LangChain-Ollama** - интеграция с Ollama

---

## 📁 Структура проекта

```
StudentHelperAgent/
├── app/                    # Backend приложение
│   ├── main.py            # Точка входа FastAPI
│   ├── models.py          # SQLAlchemy модели
│   ├── schemas.py         # Pydantic схемы
│   ├── routers/           # API endpoints
│   ├── services/          # Бизнес-логика
│   ├── repositories/      # Работа с БД
│   └── storage/           # Хранилище файлов
├── agents/                # AI агенты
│   ├── base.py           # Базовый класс агента
│   ├── transcript.py     # Агент транскрибации
│   └── assistant.py      # Чат-помощник
├── static/               # Frontend
│   ├── index.html       # Главная страница
│   ├── css/             # Стили
│   └── js/              # JavaScript
├── docker-compose.yml   # Docker конфигурация
├── requirements.txt     # Python зависимости
├── SETUP_GUIDE.md      # Подробное руководство
└── README.md           # Этот файл
```

---

## 🔧 Разработка

### Локальный запуск без Docker

1. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Настройте PostgreSQL:**
   ```bash
   createdb student_helper
   ```

3. **Создайте `.env` файл:**
   ```env
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/student_helper
   JWT_SECRET=your-secret-key
   OLLAMA_BASE_URL=http://localhost:11434
   ```

4. **Запустите приложение:**
   ```bash
   uvicorn app.main:app --reload
   ```

### Запуск тестов

```bash
pytest tests/
```

---

## 🐛 Устранение неполадок

### Кнопки Retry/Delete не работают

1. Очистите кэш браузера (Ctrl+Shift+R)
2. Перезапустите контейнер: `docker-compose restart`
3. См. [BUTTON_FIX_SUMMARY.md](BUTTON_FIX_SUMMARY.md)

### Ошибка транскрибации

1. Проверьте Hugging Face токен в настройках
2. Убедитесь, что токен имеет права "Read"
3. Проверьте формат файла (MP4, MP3, WAV и т.д.)

### Ollama не отвечает

1. Убедитесь, что Ollama запущен: `ollama serve`
2. Проверьте, что модель загружена: `ollama pull llama2`
3. Проверьте `OLLAMA_BASE_URL` в `.env`

📖 **Полное руководство:** См. [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

## 📝 Документация

- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Подробное руководство по настройке
- [BUTTON_FIX_SUMMARY.md](BUTTON_FIX_SUMMARY.md) - Исправления кнопок Retry/Delete
- [API Documentation](http://localhost:8000/docs) - Swagger UI (после запуска)

---

## 🤝 Вклад в проект

Мы приветствуем вклад в проект! Если вы хотите помочь:

1. Форкните репозиторий
2. Создайте ветку для вашей функции (`git checkout -b feature/AmazingFeature`)
3. Закоммитьте изменения (`git commit -m 'Add some AmazingFeature'`)
4. Запушьте в ветку (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

---

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](LICENSE) для подробностей.

---

## 🙏 Благодарности

- [Hugging Face](https://huggingface.co) за модель Whisper
- [Ollama](https://ollama.com) за локальные LLM модели
- [FastAPI](https://fastapi.tiangolo.com) за отличный веб-фреймворк
- [LangChain](https://langchain.com) за инструменты работы с LLM

---

## 📧 Контакты

- **GitHub:** [@Piankov-Michail](https://github.com/Piankov-Michail)
- **Репозиторий:** [StudentHelperAgent](https://github.com/Piankov-Michail/StudentHelperAgent)
- **Issues:** [GitHub Issues](https://github.com/Piankov-Michail/StudentHelperAgent/issues)

---

**Сделано с ❤️ для студентов**
