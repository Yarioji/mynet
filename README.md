# MyNet Backend

Личный мессенджер с чатами, звонками и трансляцией экрана.

## Установка

```bash
pip install -r requirements.txt
```

## Запуск

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API документация

После запуска открой в браузере:
- http://localhost:8000/docs  ← интерактивная документация (Swagger)
- http://localhost:8000/redoc ← альтернативная документация

## Эндпоинты

### Авторизация
| Метод | URL | Описание |
|-------|-----|----------|
| POST | /api/auth/register | Регистрация |
| POST | /api/auth/login | Вход (получить токен) |
| POST | /api/auth/logout | Выход |

### Пользователи
| Метод | URL | Описание |
|-------|-----|----------|
| GET | /api/users/me | Мой профиль |
| GET | /api/users/search?q=имя | Поиск пользователей |
| GET | /api/users/{id} | Профиль пользователя |

### Чаты
| Метод | URL | Описание |
|-------|-----|----------|
| POST | /api/chats/ | Создать чат |
| GET | /api/chats/ | Мои чаты |
| GET | /api/chats/{id} | Информация о чате |

### Сообщения
| Метод | URL | Описание |
|-------|-----|----------|
| GET | /api/messages/{chat_id} | История сообщений |
| POST | /api/messages/{chat_id} | Отправить сообщение |
| POST | /api/messages/{chat_id}/read | Пометить как прочитанные |

### WebSocket (real-time)
```
ws://localhost:8000/ws/chat/{chat_id}?token=ВАШ_ТОКЕН
```

Типы событий:
- `{"type": "message", "content": "текст"}` — отправить сообщение
- `{"type": "typing"}` — индикатор печати

## Структура файлов

```
socialnet/
├── main.py          # Точка входа
├── database.py      # Подключение к БД
├── models.py        # Таблицы БД
├── schemas.py       # Pydantic схемы
├── auth_utils.py    # JWT авторизация
├── requirements.txt
└── routers/
    ├── auth.py      # Регистрация/вход
    ├── users.py     # Пользователи
    ├── chats.py     # Чаты
    ├── messages.py  # Сообщения
    └── websocket.py # Real-time WS
```

## ⚠️ Перед деплоем

Замени в `auth_utils.py`:
```python
SECRET_KEY = "ЗАМЕНИ_ЭТО_НА_СЛУЧАЙНУЮ_СТРОКУ_В_ПРОДАКШЕНЕ"
```

Сгенерировать безопасный ключ:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
