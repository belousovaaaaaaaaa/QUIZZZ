# Викторина (Quiz) - Новая версия на Python/FastAPI

## 📋 Описание проекта

Образовательная викторина с разделением frontend и backend, базой данных PostgreSQL и WebSocket для реального времени.

## 🏗️ Архитектура проекта

```
/workspace
├── backend/                    # Backend на Python/FastAPI
│   ├── app/
│   │   ├── api/               # API роуты
│   │   │   ├── questions.py   # API вопросов
│   │   │   └── results.py     # API результатов
│   │   ├── models/            # SQLAlchemy модели
│   │   ├── schemas/           # Pydantic схемы
│   │   ├── services/          # Бизнес-логика
│   │   ├── config.py          # Конфигурация
│   │   ├── database.py        # Подключение к БД
│   │   └── socket_handler.py  # WebSocket обработчик
│   ├── frontend/src/          # Frontend файлы
│   │   ├── host.html          # Экран учителя
│   │   ├── player.html        # Экран игрока
│   │   └── editor.html        # Редактор вопросов
│   ├── main.py                # Точка входа
│   ├── requirements.txt       # Зависимости
│   └── .env                   # Переменные окружения
└── frontend/                   # Дубликат frontend (для разработки)
    └── src/
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
cd /workspace/backend
pip install -r requirements.txt
```

### 2. Настройка базы данных

Создайте базу данных PostgreSQL:

```sql
CREATE DATABASE quiz_db;
```

Или используйте SQLite (по умолчанию в requirements.txt есть aiosqlite):

Измените `.env`:
```
DATABASE_URL=sqlite+aiosqlite:///./quiz.db
```

### 3. Запуск сервера

```bash
cd /workspace/backend
python main.py
```

Сервер запустится на `http://localhost:8000`

## 📡 API Endpoints

### REST API

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/questions` | Получить все вопросы |
| GET | `/api/questions/{id}` | Получить вопрос по ID |
| POST | `/api/questions` | Создать вопрос |
| PUT | `/api/questions/{id}` | Обновить вопрос |
| DELETE | `/api/questions/{id}` | Удалить вопрос |
| GET | `/api/questions/categories` | Получить категории |
| POST | `/api/questions/categories` | Создать категорию |
| DELETE | `/api/questions/categories/{id}` | Удалить категорию |
| GET | `/api/results/{room_id}` | Получить результаты игры |
| GET | `/api/results/{room_id}/export` | Экспорт результатов в CSV |

### WebSocket Events

#### Клиент → Сервер
- `create_room` - Создать комнату
- `join_room` - Присоединиться к комнате
- `confirm_answer` - Отправить ответ
- `next_question` - Следующий вопрос
- `end_game` - Завершить игру

#### Сервер → Клиент
- `room_created` - Комната создана
- `player_joined` - Игрок присоединился
- `show_question_host/player` - Показать вопрос
- `timer_start/update` - Таймер
- `answer_confirmed` - Ответ подтверждён
- `update_leaderboard` - Обновление таблицы лидеров
- `game_over` - Игра окончена

## 🎮 Использование

### Для учителя:
1. Откройте `http://localhost:8000/host.html`
2. Нажмите "Создать новую игру"
3. Выберите вопросы из списка или создайте новые в редакторе
4. Сообщите код комнаты студентам

### Для студента:
1. Откройте `http://localhost:8000/player.html`
2. Введите имя и код комнаты
3. Отвечайте на вопросы в отведённое время

### Редактор вопросов:
1. Откройте `http://localhost:8000/editor.html`
2. Создавайте вопросы разных типов:
   - Один правильный ответ
   - Несколько правильных ответов
   - Текстовый ответ
3. Добавляйте категории и уровни сложности

## 🔧 Конфигурация

Файл `.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/quiz_db
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## 📊 Структура базы данных

### Таблицы:
- `categories` - Категории вопросов
- `questions` - Вопросы викторины
- `quizzes` - Готовые наборы вопросов
- `game_results` - Результаты игр
- `player_results` - Результаты игроков

## 🛠️ Технологии

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, Socket.IO
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Database**: PostgreSQL (или SQLite для разработки)
- **Real-time**: WebSocket через python-socketio

## 📝 Лицензия

MIT License
