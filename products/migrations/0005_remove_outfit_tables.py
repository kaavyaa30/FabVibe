from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_new_features'),
    ]

    operations = [
        migrations.DeleteModel(name='OutfitItem'),
        migrations.DeleteModel(name='Outfit'),
    ]
