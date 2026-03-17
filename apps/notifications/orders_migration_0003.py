from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_cartitem_half_payment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderNote',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('note',        models.TextField()),
                ('is_internal', models.BooleanField(default=False, help_text='Not sent to user')),
                ('notify_user', models.BooleanField(default=True,  help_text='Send push to user')),
                ('created_at',  models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notes',
                    to='orders.order',
                )),
                ('added_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='order_notes_added',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'verbose_name': 'Order Note', 'verbose_name_plural': 'Order Notes', 'ordering': ['-created_at']},
        ),
    ]
