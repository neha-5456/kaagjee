# Generated migration to remove Hindi fields

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='name_hi',
        ),
        migrations.RemoveField(
            model_name='subcategory',
            name='name_hi',
        ),
    ]