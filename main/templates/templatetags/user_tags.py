from django import template
from django.contrib.auth.models import User

register = template.Library()

@register.filter
def get_display_name(user):
    """Возвращает ФИО пользователя или username"""
    if hasattr(user, 'profile') and user.profile.full_name:
        return user.profile.full_name
    elif user.first_name or user.last_name:
        return f"{user.first_name or ''} {user.last_name or ''}".strip()
    else:
        return user.username