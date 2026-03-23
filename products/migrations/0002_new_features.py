from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_inventorylog'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # UserProfile — size preferences & measurements
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('height_cm', models.PositiveSmallIntegerField(null=True, blank=True)),
                ('weight_kg', models.PositiveSmallIntegerField(null=True, blank=True)),
                ('chest_cm', models.PositiveSmallIntegerField(null=True, blank=True)),
                ('waist_cm', models.PositiveSmallIntegerField(null=True, blank=True)),
                ('hips_cm', models.PositiveSmallIntegerField(null=True, blank=True)),
                ('preferred_size', models.CharField(max_length=5, blank=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'user_profiles'},
        ),
        # RecentlyViewed
        migrations.CreateModel(
            name='RecentlyViewed',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('viewed_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='recently_viewed', to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='viewed_by', to='products.product')),
            ],
            options={'db_table': 'recently_viewed', 'ordering': ['-viewed_at'],
                     'unique_together': {('user', 'product')}},
        ),
        # StockAlert
        migrations.CreateModel(
            name='StockAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('size', models.CharField(max_length=10, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('notified', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='stock_alerts', to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='stock_alerts', to='products.product')),
            ],
            options={'db_table': 'stock_alerts',
                     'unique_together': {('user', 'product', 'size')}},
        ),
        # Outfit
        migrations.CreateModel(
            name='Outfit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='outfits', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'outfits', 'ordering': ['-created_at']},
        ),
        # OutfitItem
        migrations.CreateModel(
            name='OutfitItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('slot', models.CharField(max_length=20)),  # top/bottom/shoes/bag/accessory
                ('outfit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='items', to='products.outfit')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    to='products.product')),
            ],
            options={'db_table': 'outfit_items'},
        ),
    ]
