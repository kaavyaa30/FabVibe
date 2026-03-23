# Generated manually to handle phone_number non-null transition
from django.db import migrations, models
import django.core.validators


def populate_missing_phone_numbers(apps, schema_editor):
    """Populate phone_number for users who don't have one"""
    User = apps.get_model('users', 'User')
    for user in User.objects.filter(phone_number__isnull=True):
        # Generate a unique placeholder phone based on user ID
        user.phone_number = f'+9999{user.id:010d}'
        user.save(update_fields=['phone_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_rename_is_verified_user_email_verified_user_otp_code_and_more'),
    ]

    operations = [
        # Step 1: Populate missing phone numbers
        migrations.RunPython(populate_missing_phone_numbers, migrations.RunPython.noop),
        
        # Step 2: Remove unique constraint from email
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254, unique=False),
        ),
        
        # Step 3: Make phone_number non-nullable and required
        migrations.AlterField(
            model_name='user',
            name='phone_number',
            field=models.CharField(
                max_length=15,
                unique=True,
                validators=[django.core.validators.RegexValidator(
                    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
                    regex=r'^\+?1?\d{9,15}$'
                )]
            ),
        ),
    ]
