# Local Agent — Система складских операций

## Назначение

Система учета операций:
- Приход
- Перемещение
- Списание (выдача)

С возможностью генерации PDF-накладных.

**Важно:** Накладные генерируются для всех операций **кроме прихода** (move / выдача / списание).

## Стек

- Python 3.x
- Django
- PostgreSQL (рекомендуется)
- Docker (рекомендуется)

## Быстрый запуск (dev)

```bash
python -m venv .venv
source .venv/bin/activate #.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

```

## Первичная настройка через админку

1. Создай суперпользователя:

```bash
python manage.py createsuperuser
```

2. Зайди в админку: `http://127.0.0.1:8000/admin/`

3. Открой **Настройки приложения** и задай:

- **LOCAL_SITE_NAME**: имя локального склада, который обслуживает этот инстанс.
- **Email для накладных**: куда отправлять PDF (например, почта бухгалтерии).

Если поле Email пустое, отправка накладных не выполняется.

## Настройка почты (SMTP)

Отправка накладных работает через стандартную почту Django. Минимальные переменные окружения:

- `EMAIL_HOST`
- `EMAIL_PORT` (по умолчанию 587)
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS` (по умолчанию 1)
- `DEFAULT_FROM_EMAIL` (если не задан, берётся `EMAIL_HOST_USER`)

Адрес получателя настраивается в админке (см. выше). Для совместимости можно задавать через env:

- `OFFICE_EMAIL` (предпочтительно)
- `ACCOUNTING_EMAIL` (fallback)
