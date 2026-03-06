from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

GROUP_WAREHOUSE_OPERATOR = 'warehouse_operator'
GROUP_CHIEF_STOREKEEPER = 'chief_storekeeper'


def is_chief_storekeeper(user) -> bool:
    return bool(
        user.is_authenticated and (
            user.is_superuser or user.groups.filter(name=GROUP_CHIEF_STOREKEEPER).exists()
        )
    )


def can_manage_catalog(user) -> bool:
    return is_chief_storekeeper(user)


def chief_required(view_func):
    @login_required(login_url='/login/')
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not can_manage_catalog(request.user):
            raise PermissionDenied('Недостаточно прав для доступа к справочникам')
        return view_func(request, *args, **kwargs)

    return wrapped
