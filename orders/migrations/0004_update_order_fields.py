# Generated migration for updating Order and OrderItem fields

from django.db import migrations, models


def migrate_order_data(apps, schema_editor):
    """Migrate data from old fields to new fields"""
    Order = apps.get_model('orders', 'Order')
    for order in Order.objects.all():
        # Combine shipping address fields into single text field
        address_parts = [
            order.shipping_full_name,
            order.shipping_phone,
            order.shipping_address_line1,
        ]
        if order.shipping_address_line2:
            address_parts.append(order.shipping_address_line2)
        address_parts.extend([
            f"{order.shipping_city}, {order.shipping_state} {order.shipping_postal_code}",
            order.shipping_country
        ])
        order.shipping_address = '\n'.join(address_parts)
        order.total_amount = order.total
        order.save()


def reverse_migrate_order_data(apps, schema_editor):
    """Reverse migration - not fully reversible"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_initial'),
    ]

    operations = [
        # Rename order_number to order_id
        migrations.RenameField(
            model_name='order',
            old_name='order_number',
            new_name='order_id',
        ),
        # Add new fields with defaults
        migrations.AddField(
            model_name='order',
            name='shipping_address',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='order',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='orderitem',
            name='price_at_purchase',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        # Migrate data
        migrations.RunPython(migrate_order_data, reverse_migrate_order_data),
        # Remove old fields
        migrations.RemoveField(
            model_name='order',
            name='shipping_full_name',
        ),
        migrations.RemoveField(
            model_name='order',
            name='shipping_phone',
        ),
        migrations.RemoveField(
            model_name='order',
            name='shipping_address_line1',
        ),
        migrations.RemoveField(
            model_name='order',
            name='shipping_address_line2',
        ),
        migrations.RemoveField(
            model_name='order',
            name='shipping_city',
        ),
        migrations.RemoveField(
            model_name='order',
            name='shipping_state',
        ),
        migrations.RemoveField(
            model_name='order',
            name='shipping_postal_code',
        ),
        migrations.RemoveField(
            model_name='order',
            name='shipping_country',
        ),
        migrations.RemoveField(
            model_name='order',
            name='total',
        ),
        migrations.RemoveField(
            model_name='orderitem',
            name='product_name',
        ),
        migrations.RemoveField(
            model_name='orderitem',
            name='price',
        ),
        migrations.RemoveField(
            model_name='orderitem',
            name='subtotal',
        ),
    ]
