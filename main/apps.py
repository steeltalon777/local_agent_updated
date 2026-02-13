from django.apps import AppConfig


def _enable_sqlite_pragmas(sender, connection, **kwargs):
    """Включаем безопасные/практичные PRAGMA для SQLite.

    - WAL: лучше для многопоточности и конкурентных чтений.
    - synchronous=NORMAL: компромисс (вместо FULL).
    """
    if connection.vendor != 'sqlite':
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA journal_mode=WAL;')
            cursor.execute('PRAGMA synchronous=NORMAL;')
    except Exception:
        # Если что-то пойдёт не так, не валим весь проект.
        # На объекте хоть что-то должно работать.
        return


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        from django.db.backends.signals import connection_created
        connection_created.connect(_enable_sqlite_pragmas, dispatch_uid='local_agent_sqlite_pragmas')
