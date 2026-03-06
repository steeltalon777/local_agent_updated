from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField('ФИО', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return self.full_name or self.user.username

    def save(self, *args, **kwargs):
        if not self.full_name and (self.user.first_name or self.user.last_name):
            self.full_name = f"{self.user.first_name or ''} {self.user.last_name or ''}".strip()
        super().save(*args, **kwargs)

    def get_display_name(self):
        if self.full_name:
            return self.full_name
        if self.user.first_name or self.user.last_name:
            return f"{self.user.first_name or ''} {self.user.last_name or ''}".strip()
        return self.user.username


class Site(models.Model):
    name = models.CharField('Наименование объекта', max_length=255, unique=True)
    code = models.CharField('Короткий код', max_length=50, blank=True, null=True)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        verbose_name = 'Объект'
        verbose_name_plural = 'Объекты'
        ordering = ['name']

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField('Категория', max_length=255, unique=True)
    parent = models.ForeignKey(
        'self',
        verbose_name='Родительская категория',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='children',
    )
    is_active = models.BooleanField('Активна', default=True)
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def hierarchy_name(self):
        if not self.parent_id:
            return self.name
        return f'{self.parent.name} / {self.name}'


class Item(models.Model):
    name = models.CharField('Наименование ТМЦ', max_length=255, unique=True)
    default_unit = models.CharField('Ед. изм (по умолчанию)', max_length=50, default='шт')
    sku = models.CharField('Артикул/SKU', max_length=100, blank=True, null=True)
    category = models.ForeignKey(
        Category,
        verbose_name='Категория',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items',
    )
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        verbose_name = 'ТМЦ'
        verbose_name_plural = 'ТМЦ'
        ordering = ['name']

    def __str__(self):
        return self.name


class OperationType(models.TextChoices):
    INCOMING = 'incoming', 'Приход'
    MOVE = 'move', 'Перемещение'
    WRITEOFF = 'writeoff', 'Списание'
    ISSUE = 'issue', 'Выдача (расход)'


class Operation(models.Model):
    created_at = models.DateTimeField('Дата и время создания', auto_now_add=True)
    operation_type = models.CharField('Тип операции', max_length=20, choices=OperationType.choices)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Создал')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, verbose_name='ТМЦ')

    item_name = models.CharField('Наименование (legacy)', max_length=255, blank=True, null=True)
    serial = models.CharField('Серийный номер', max_length=255, blank=True, null=True)
    quantity = models.FloatField('Количество', default=1)
    unit = models.CharField('Единица измерения', max_length=50, default='шт')

    receiver_name = models.CharField('Получатель', max_length=255, blank=True, null=True)
    vehicle = models.CharField('Транспорт', max_length=255, blank=True, null=True)

    from_site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        verbose_name='Откуда (склад)',
        related_name='operations_from',
        null=True,
        blank=True,
    )
    to_site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        verbose_name='Куда (склад)',
        related_name='operations_to',
        null=True,
        blank=True,
    )

    from_location = models.CharField('Откуда (локация)', max_length=255, blank=True, null=True)
    to_location = models.CharField('Куда (локация)', max_length=255, blank=True, null=True)

    comment = models.TextField('Комментарий', blank=True, null=True)
    pdf_file = models.FileField('PDF накладной', upload_to='invoices/', blank=True, null=True)

    class Meta:
        verbose_name = 'Операция'
        verbose_name_plural = 'Операции'
        ordering = ['-created_at']

    def __str__(self):
        name = self.item.name if self.item_id else (self.item_name or '')
        return f'{self.get_operation_type_display()} - {name}'

    @property
    def display_item_name(self) -> str:
        return self.item.name if self.item_id else (self.item_name or '')

    @property
    def display_unit(self) -> str:
        if self.unit:
            return self.unit
        if self.item_id:
            return self.item.default_unit
        return 'шт'
