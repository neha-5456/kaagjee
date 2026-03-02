# Generated migration for adding half_payment field to CartItem

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='half_payment',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
