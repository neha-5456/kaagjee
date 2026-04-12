from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_cartitem_half_payment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='user_email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
        migrations.AlterField(
            model_name='order',
            name='user_phone',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
    ]
