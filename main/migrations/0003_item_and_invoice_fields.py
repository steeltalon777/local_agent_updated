# Generated manually for Django 6.0.2

from django.db import migrations, models
import django.db.models.deletion


def forwards_migrate_items(apps, schema_editor):
    Operation = apps.get_model('main', 'Operation')
    Item = apps.get_model('main', 'Item')

    unknown, _ = Item.objects.get_or_create(name='Неизвестно', defaults={'default_unit': 'шт', 'sku': None})

    for op in Operation.objects.all().iterator():
        name = (getattr(op, 'item_name', None) or '').strip()
        unit = (getattr(op, 'unit', None) or 'шт').strip() or 'шт'
        if name:
            item, _ = Item.objects.get_or_create(name=name, defaults={'default_unit': unit, 'sku': None})
        else:
            item = unknown
        op.item_id = item.id
        # legacy поле оставляем заполненным (на всякий)
        if not getattr(op, 'item_name', None):
            op.item_name = item.name
        op.save(update_fields=['item', 'item_name'])


def backwards_migrate_items(apps, schema_editor):
    Operation = apps.get_model('main', 'Operation')
    for op in Operation.objects.all().iterator():
        # откат: заполним item_name из Item
        if getattr(op, 'item_id', None) and hasattr(op, 'item'):
            op.item_name = op.item.name
        op.item_id = None
        op.save(update_fields=['item', 'item_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_remove_operation_site_operation_from_site_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True, verbose_name='Наименование ТМЦ')),
                ('default_unit', models.CharField(default='шт', max_length=50, verbose_name='Ед. изм (по умолчанию)')),
                ('sku', models.CharField(blank=True, max_length=100, null=True, verbose_name='Артикул/SKU')),
            ],
            options={
                'verbose_name': 'ТМЦ',
                'verbose_name_plural': 'ТМЦ',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='operation',
            name='item',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, to='main.item', verbose_name='ТМЦ'),
        ),
        migrations.AlterField(
            model_name='operation',
            name='item_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Наименование (legacy)'),
        ),
        migrations.AddField(
            model_name='operation',
            name='receiver_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Получатель'),
        ),
        migrations.AddField(
            model_name='operation',
            name='vehicle',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Транспорт'),
        ),
        migrations.AddField(
            model_name='operation',
            name='pdf_file',
            field=models.FileField(blank=True, null=True, upload_to='invoices/', verbose_name='PDF накладной'),
        ),
        migrations.RunPython(forwards_migrate_items, backwards_migrate_items),
        migrations.AlterField(
            model_name='operation',
            name='item',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='main.item', verbose_name='ТМЦ'),
        ),
    ]
