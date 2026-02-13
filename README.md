# Local Agent — Система складских операций

## Назначение

Система учета операций:
- Приход
- Перемещение
- Списание (выдача)

С возможностью генерации PDF-накладных.

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
