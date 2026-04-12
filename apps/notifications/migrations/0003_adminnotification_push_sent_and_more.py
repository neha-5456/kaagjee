from django.db import migrations


class Migration(migrations.Migration):
    """
    All missing tables (fcmdevice, usernotification) and columns (push_sent, push_sent_at)
    were created directly via SQL. This migration just marks the state as applied.
    """

    dependencies = [
        ('notifications', '0002_alter_adminnotification_id_alter_fcmdevice_id_and_more'),
    ]

    operations = []
