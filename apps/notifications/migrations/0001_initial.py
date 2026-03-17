"""
Fresh initial migration — FCMDevice, UserNotification, AdminNotification.
(Replace old 0001_initial.py with this one.)
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ── FCMDevice ─────────────────────────────────────────────────
        migrations.CreateModel(
            name='FCMDevice',
            fields=[
                ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('token',      models.TextField(unique=True)),
                ('platform',   models.CharField(
                    max_length=10,
                    choices=[('android', 'Android'), ('ios', 'iOS'), ('web', 'Web')],
                    default='web',
                )),
                ('is_active',  models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='fcm_devices',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'verbose_name': 'FCM Device', 'verbose_name_plural': 'FCM Devices', 'ordering': ['-created_at']},
        ),

        # ── UserNotification ──────────────────────────────────────────
        migrations.CreateModel(
            name='UserNotification',
            fields=[
                ('id',                models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('notification_type', models.CharField(max_length=30, choices=[
                    ('order_placed', 'Order Placed'), ('order_processing', 'Order Processing'),
                    ('order_completed', 'Order Completed'), ('order_cancelled', 'Order Cancelled'),
                    ('payment_success', 'Payment Successful'), ('payment_failed', 'Payment Failed'),
                    ('admin_note', 'Note from Admin'), ('general', 'General'),
                ])),
                ('title',        models.CharField(max_length=200)),
                ('message',      models.TextField()),
                ('order_id',     models.CharField(max_length=50, blank=True)),
                ('push_sent',    models.BooleanField(default=False)),
                ('push_sent_at', models.DateTimeField(null=True, blank=True)),
                ('is_read',      models.BooleanField(default=False)),
                ('read_at',      models.DateTimeField(null=True, blank=True)),
                ('created_at',   models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notifications',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'verbose_name': 'User Notification', 'verbose_name_plural': 'User Notifications', 'ordering': ['-created_at']},
        ),

        # ── AdminNotification ─────────────────────────────────────────
        migrations.CreateModel(
            name='AdminNotification',
            fields=[
                ('id',                models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('notification_type', models.CharField(max_length=30, choices=[
                    ('new_order', 'New Order'), ('payment_success', 'Payment Success'),
                    ('payment_failed', 'Payment Failed'), ('order_cancelled', 'Order Cancelled'),
                    ('new_user', 'New User Registration'), ('form_submission', 'New Form Submission'),
                ])),
                ('title',        models.CharField(max_length=200)),
                ('message',      models.TextField()),
                ('order_id',     models.CharField(max_length=50, blank=True)),
                ('user_id',      models.IntegerField(null=True, blank=True)),
                ('push_sent',    models.BooleanField(default=False)),
                ('push_sent_at', models.DateTimeField(null=True, blank=True)),
                ('is_read',      models.BooleanField(default=False)),
                ('read_at',      models.DateTimeField(null=True, blank=True)),
                ('created_at',   models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name': 'Admin Notification', 'verbose_name_plural': 'Admin Notifications', 'ordering': ['-created_at']},
        ),
    ]
