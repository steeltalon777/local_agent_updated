from django.db import migrations, models
import django.utils.timezone
import django.db.models.deletion


def create_default_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='warehouse_operator')
    Group.objects.get_or_create(name='chief_storekeeper')


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_item_and_invoice_fields'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True, verbose_name='Категория')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активна')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлена')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children', to='main.category', verbose_name='Родительская категория')),
            ],
            options={'verbose_name': 'Категория', 'verbose_name_plural': 'Категории', 'ordering': ['name']},
        ),
        migrations.AddField(
            model_name='item',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='items', to='main.category', verbose_name='Категория'),
        ),
        migrations.AddField(
            model_name='item',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Активен'),
        ),
        migrations.AddField(
            model_name='site',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Создан'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='site',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Активен'),
        ),
        migrations.AddField(
            model_name='site',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Обновлён'),
        ),
        migrations.AlterModelOptions(
            name='site',
            options={'ordering': ['name'], 'verbose_name': 'Объект', 'verbose_name_plural': 'Объекты'},
        ),
        migrations.RunPython(create_default_groups, migrations.RunPython.noop),
    ]
