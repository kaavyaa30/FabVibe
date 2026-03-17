from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_update_order_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivery_otp',
            field=models.CharField(blank=True, max_length=6),
        ),
        migrations.AddField(
            model_name='order',
            name='otp_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='order',
            name='otp_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
