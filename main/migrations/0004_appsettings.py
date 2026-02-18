from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_item_and_invoice_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('local_site_name', models.CharField(blank=True, default='', help_text='Если заполнено, переопределяет settings.LOCAL_SITE_NAME и используется как имя локального склада.', max_length=255, verbose_name='LOCAL_SITE_NAME (имя локального склада)')),
                ('office_email', models.EmailField(blank=True, default='', help_text='Куда отправлять PDF-накладные. Если пусто, отправка не выполняется.', max_length=254, verbose_name='Email для накладных (получатель)')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Настройки приложения',
                'verbose_name_plural': 'Настройки приложения',
            },
        ),
    ]
