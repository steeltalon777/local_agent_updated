from __future__ import annotations

from django.conf import settings

from main.models import Site, AppSettings


def get_local_site() -> Site:
    """Возвращает «локальный» склад, к которому привязан данный инстанс приложения.

    Имя склада задаётся через settings.LOCAL_SITE_NAME (или env LOCAL_SITE_NAME).
    Если склад не существует, создаём его автоматически.

    Если LOCAL_SITE_NAME не задан, то пытаемся выбрать единственный склад в БД.
    В противном случае создаём/берём склад с именем "Локальный склад".
    """

    # Приоритет: админка -> settings/env -> авто-выбор
    try:
        db_name = (AppSettings.get_solo().local_site_name or '').strip()
    except Exception:
        # На совсем свежей базе (до миграций) таблицы может не быть.
        db_name = ''

    name = db_name or (getattr(settings, 'LOCAL_SITE_NAME', '') or '').strip()

    if name:
        site, _ = Site.objects.get_or_create(name=name)
        return site

    # Если имя не задано, но склад один, берём его.
    existing = Site.objects.all().order_by('id')
    if existing.count() == 1:
        return existing.first()

    # Иначе создаём дефолтный (чтобы проект не падал на пустой инсталляции)
    site, _ = Site.objects.get_or_create(name='Локальный склад')
    return site
