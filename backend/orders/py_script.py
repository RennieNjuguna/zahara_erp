# Migration script (run after creating OrderItem model)
from django.db import migrations

def migrate_order_items(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    OrderItem = apps.get_model('orders', 'OrderItem')
    for order in Order.objects.all():
        OrderItem.objects.create(
            order=order,
            product=order.product,
            boxes=order.boxes,
            stems_per_box=order.stems_per_box,
            stems=order.stems,
            price_per_stem=order.price_per_stem,
            total_amount=order.total_amount
        )

class Migration(migrations.Migration):
    dependencies = [('orders', 'previous_migration_name')]
    operations = [
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.ForeignKey(on_delete=models.CASCADE, related_name='items', to='orders.Order')),
                ('product', models.ForeignKey(on_delete=models.CASCADE, to='products.Product')),
                ('boxes', models.PositiveIntegerField(default=1)),
                ('stems_per_box', models.PositiveIntegerField(default=1)),
                ('stems', models.PositiveIntegerField(editable=False)),
                ('price_per_stem', models.DecimalField(decimal_places=2, editable=False, max_digits=10)),
                ('total_amount', models.DecimalField(decimal_places=2, editable=False, max_digits=12)),
            ],
        ),
        migrations.RunPython(migrate_order_items),
        migrations.RemoveField(model_name='Order', name='product'),
        migrations.RemoveField(model_name='Order', name='boxes'),
        migrations.RemoveField(model_name='Order', name='stems_per_box'),
        migrations.RemoveField(model_name='Order', name='stems'),
        migrations.RemoveField(model_name='Order', name='price_per_stem'),
    ]
