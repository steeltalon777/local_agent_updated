from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Category, Item, Operation, Site, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профиль'


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'display_name', 'email', 'is_active', 'is_staff', 'is_superuser')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'profile__full_name')
    filter_horizontal = ('groups', 'user_permissions')

    def display_name(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile and profile.full_name:
            return profile.full_name
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip()

    display_name.short_description = 'ФИО'


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active', 'created_at')
    search_fields = ('name', 'parent__name')
    list_filter = ('is_active',)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'default_unit', 'is_active')
    search_fields = ('name', 'sku')
    list_filter = ('category', 'is_active')


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'operation_type',
        'display_item',
        'from_site',
        'to_site',
        'receiver_name',
        'vehicle',
        'created_by',
        'quantity',
        'unit',
        'pdf_file',
    )
    list_filter = ('operation_type', 'created_at', 'created_by', 'from_site', 'to_site')
    search_fields = ('item__name', 'item_name', 'serial', 'comment', 'receiver_name', 'vehicle')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Основная информация', {'fields': ('operation_type', 'created_at', 'created_by')}),
        (
            'Детали операции',
            {'fields': ('item', 'item_name', 'serial', 'quantity', 'unit', 'receiver_name', 'vehicle', 'comment', 'pdf_file')},
        ),
        ('Склады', {'fields': ('from_site', 'to_site')}),
        ('Локации (устаревшие)', {'fields': ('from_location', 'to_location'), 'classes': ('collapse',)}),
    )

    def display_item(self, obj):
        return obj.display_item_name

    display_item.short_description = 'ТМЦ'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
