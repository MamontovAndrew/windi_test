# windi_test

Этот проект — бэкенд для чат-приложения с поддержкой:

- JWT-аутентификации
- приватных и групповых чатов
- хранения сообщений с дедупликацией
- WebSocket-подключений
- автоматических тестов и автогенерацией тестовых данных

Разработано с использованием **FastAPI**, **SQLAlchemy (async)**, **PostgreSQL**, **Docker**.

## Как запустить

### 1. Клонируем репозиторий и переходим в него

```bash
git clone https://github.com/your_username/windi_chat.git
cd windi_chat
```
### 2. Создаём .env
Создайте файл .env в корне проекта:
```text
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret123
POSTGRES_DB=windi_chat
DATABASE_URL=postgresql+asyncpg://postgres:secret123@db:5432/windi_chat

JWT_SECRET_KEY=mytopsecretkey
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```
Эти переменные используются для настройки подключения к БД и генерации JWT-токенов.

### 3. Запускаем в Docker
docker compose up --build
FastAPI поднимется на http://localhost:8000
PostgreSQL на localhost:5432

Автотесты
При запуске контейнера автоматически выполняются 4 теста с созданием:
- двух пользователей (Alice, Bob)
- отправкой сообщений
- созданием группового чата
- отметкой сообщений как прочитанных


Пример ручного запуска тестов:
```bash
docker compose exec app pytest
```

## Swagger UI
Swagger-документация доступна по адресу:
http://localhost:8000/docs

Для авторизации:

Выполните POST /auth/register или POST /auth/login

Нажмите кнопку Authorize в Swagger UI и вставьте почту и пароль, указанные при входе/регистрации


Примеры API-запросов:

1. Регистрация
```text
POST /auth/register
Content-Type: application/json

{
  "name": "Alice",
  "email": "alice@example.com",
  "password": "secret"
}
```

2. Авторизация
```text
POST /auth/login
Content-Type: application/x-www-form-urlencoded
username=alice@example.com&password=secret
```
Ответ:
```text
{
  "access_token": "your.jwt.token",
  "token_type": "bearer"
}
```

3. Отправка сообщения
```text
POST /chat/message
Authorization: Bearer <access_token>
Content-Type: application/json
{
  "recipient_id": 2,
  "text": "Привет, как дела?"
}
```
Если приватного чата между пользователями ещё нет — он будет создан автоматически.

4. Создание группы
```text
POST /chat/group
Authorization: Bearer <access_token>
Content-Type: application/json
{
  "name": "Project Team",
  "participant_ids": [2, 3]
}
```

5. Просмотр истории чата
```text
GET /chat/history/1?limit=50&offset=0
Authorization: Bearer <access_token>
```

6. Отметка сообщения как прочитанного
```text
PATCH /chat/message/123/read
Authorization: Bearer <access_token>
```

## Архитектура директории
|Компонент|Назначение|
|---------|----------|
|app/models.py|SQLAlchemy-модели|
|app/routes/|FastAPI-роуты (auth, chat)|
|app/utils.py|Хеширование паролей, работа с JWT|
|tests/|Pytest-тесты, создающие данные|
|Dockerfile|Сборка образа|
|docker-compose.yml|компоуз для PostgreSQL + FastAPI|
|start.sh|Запуск сервера и тестов|

## Важные моменты
- При отправке сообщения через /chat/message, если чата нет, он создаётся.
- При создании группы, создатель автоматически добавляется в неё.
- Вся логика построена асинхронно — везде используется AsyncSession.
- Используется dedup_key, чтобы избежать повторных сообщений.
