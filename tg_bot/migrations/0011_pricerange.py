# Generated by Django 5.1.1 on 2024-09-17 17:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tg_bot', '0010_order_comment_alter_product_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='PriceRange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('min_price', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Минимальная цена')),
                ('max_price', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Максимальная цена')),
            ],
            options={
                'verbose_name': 'Ценовой диапазон',
                'verbose_name_plural': 'Ценовые диапазоны',
            },
        ),
    ]
