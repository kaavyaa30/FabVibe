# Generated migration for updating Cart user field and adding session_key

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cart', '0003_initial'),
    ]

    operations = [
        # Remove the OneToOne constraint and make it a ForeignKey
        migrations.RemoveField(
            model_name='cart',
            name='user',
        ),
        migrations.AddField(
            model_name='cart',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='carts',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        # Add session_key field for guest carts
        migrations.AddField(
            model_name='cart',
            name='session_key',
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=40,
                null=True
            ),
        ),
    ]
