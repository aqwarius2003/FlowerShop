# Generated by Django 5.1.1 on 2024-09-17 08:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tg_bot', '0002_alter_userbot_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userbot',
            name='address',
            field=models.CharField(max_length=200, null=True, verbose_name='Адрес'),
        ),
    ]