# Generated by Django 5.2 on 2025-04-22 12:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('customers', '0001_initial'),
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stems', models.PositiveIntegerField()),
                ('price_per_stem', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12)),
                ('currency', models.CharField(max_length=3)),
                ('invoice_code', models.CharField(max_length=20, unique=True)),
                ('date', models.DateField()),
                ('branch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='customers.branch')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='customers.customer')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='products.product')),
            ],
        ),
    ]
