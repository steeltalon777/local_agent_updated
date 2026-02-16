# main/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User  # Импортируем стандартного User
from .models import UserProfile, Site, Operation, Item

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "inventory_number", "default_unit", "sku")
    search_fields = ("name", "inventory_number", "sku")

# Инлайн для профиля в админке User
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профиль'


# Расширяем админку User
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'get_full_name', 'email', 'is_staff')

    def get_full_name(self, obj):
        if hasattr(obj, 'profile') and obj.profile.full_name:
            return obj.profile.full_name
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip()

    get_full_name.short_description = 'ФИО'


# Админка для Site
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


# Админка для Operation
# Админка для Operation
class OperationAdmin(admin.ModelAdmin):
    list_display = (
        'created_at', 'operation_type', 'display_item', 'from_site', 'to_site',
        'receiver_name', 'vehicle', 'created_by', 'quantity', 'unit', 'pdf_file'
    )
    list_filter = ('operation_type', 'created_at', 'created_by', 'from_site', 'to_site')  # Убрали 'site', добавили 'from_site', 'to_site'
    search_fields = ('item__name', 'item_name', 'serial', 'comment', 'receiver_name', 'vehicle')
    readonly_fields = ('created_at',)

    def display_item(self, obj):
        return obj.display_item_name
    display_item.short_description = 'ТМЦ'
    # Добавим поля для удобного отображения
    fieldsets = (
        ('Основная информация', {
            'fields': ('operation_type', 'created_at', 'created_by')
        }),
        ('Детали операции', {
            'fields': ('item', 'item_name', 'serial', 'quantity', 'unit', 'receiver_name', 'vehicle', 'comment', 'pdf_file')
        }),
        ('Склады', {
            'fields': ('from_site', 'to_site')
        }),
        ('Локации (устаревшие)', {
            'fields': ('from_location', 'to_location'),
            'classes': ('collapse',)  # Сворачиваемый блок
        }),
    )

# Регистрируем модели
admin.site.unregister(User)  # Отменяем стандартную регистрацию
admin.site.register(User, CustomUserAdmin)  # Регистрируем с нашей кастомной админкой
admin.site.register(Site, SiteAdmin)
admin.site.register(Item)
admin.site.register(Operation, OperationAdmin)